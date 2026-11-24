import base64
import io
import os
import uuid
from fastapi import FastAPI, HTTPException
from minio import Minio
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.logic import can_user_access_document, validate_file_type

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./catalog.db")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "vaporshelf-docs")

connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_db_initialized = False


class DocumentModel(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    is_private = Column(Boolean, default=True)
    file_type = Column(String, nullable=False)
    owner_id = Column(String, nullable=False, default="usr-101")


class AccessRequestModel(Base):
    __tablename__ = "access_requests"
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True, nullable=False)
    requester_id = Column(String, index=True, nullable=False)
    status = Column(String, default="pending")  # pending | approved | denied


def get_db():
    global _db_initialized
    if not _db_initialized:
        Base.metadata.create_all(bind=engine)
        _db_initialized = True
    return SessionLocal()


def get_minio_client() -> Minio:
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
    return client


app = FastAPI(title="VaporShelf - Catalog & Identity Service")


class DocumentCreate(BaseModel):
    title: str
    is_private: bool = True
    file_type: str
    owner_id: str = "usr-101"
    content_base64: str | None = None


class AccessRequestCreate(BaseModel):
    requester_id: str


class AccessDecision(BaseModel):
    owner_id: str
    approved: bool


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents", status_code=201)
def create_document(doc: DocumentCreate):
    try:
        clean_type = validate_file_type(doc.file_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    doc_id = str(uuid.uuid4())
    object_name = f"{doc_id}.{clean_type}"
    raw_bytes = (
        base64.b64decode(doc.content_base64)
        if doc.content_base64
        else f"VaporShelf placeholder for {doc.title}".encode()
    )

    minio_client = get_minio_client()
    minio_client.put_object(
        MINIO_BUCKET,
        object_name,
        io.BytesIO(raw_bytes),
        length=len(raw_bytes),
        content_type="application/octet-stream",
    )

    db = get_db()
    try:
        db_doc = DocumentModel(
            id=doc_id,
            title=doc.title,
            is_private=doc.is_private,
            file_type=clean_type,
            owner_id=doc.owner_id,
        )
        db.add(db_doc)
        db.commit()
        return {
            "id": doc_id,
            "title": doc.title,
            "is_private": doc.is_private,
            "file_type": clean_type,
            "owner_id": doc.owner_id,
        }
    finally:
        db.close()


@app.get("/documents/{document_id}")
def get_document(document_id: str, user_id: str = "usr-101"):
    db = get_db()
    try:
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        approved_rows = (
            db.query(AccessRequestModel)
            .filter(
                AccessRequestModel.document_id == document_id,
                AccessRequestModel.status == "approved",
            )
            .all()
        )
        approved_users = [row.requester_id for row in approved_rows]

        if not can_user_access_document(
            doc.is_private, doc.owner_id, user_id, approved_users
        ):
            raise HTTPException(
                status_code=403, detail="Access denied to private document"
            )

        return {
            "id": doc.id,
            "title": doc.title,
            "is_private": doc.is_private,
            "file_type": doc.file_type,
            "owner_id": doc.owner_id,
            "download_url": f"{MINIO_PUBLIC_URL}/{MINIO_BUCKET}/{doc.id}.{doc.file_type}",
        }
    finally:
        db.close()


@app.post("/documents/{document_id}/access-requests", status_code=201)
def request_document_access(document_id: str, payload: AccessRequestCreate):
    db = get_db()
    try:
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        req_id = str(uuid.uuid4())
        access_req = AccessRequestModel(
            id=req_id,
            document_id=document_id,
            requester_id=payload.requester_id,
            status="pending",
        )
        db.add(access_req)
        db.commit()
        return {
            "request_id": req_id,
            "document_id": document_id,
            "requester_id": payload.requester_id,
            "status": "pending",
        }
    finally:
        db.close()


@app.put("/documents/{document_id}/access-requests/{requester_id}")
def resolve_document_access(
    document_id: str, requester_id: str, decision: AccessDecision
):
    db = get_db()
    try:
        doc = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if doc.owner_id != decision.owner_id:
            raise HTTPException(
                status_code=403, detail="Only owner can authorize access"
            )

        access_req = (
            db.query(AccessRequestModel)
            .filter(
                AccessRequestModel.document_id == document_id,
                AccessRequestModel.requester_id == requester_id,
            )
            .first()
        )
        if not access_req:
            raise HTTPException(status_code=404, detail="Access request not found")

        access_req.status = "approved" if decision.approved else "denied"
        db.commit()
        return {
            "document_id": document_id,
            "requester_id": requester_id,
            "status": access_req.status,
        }
    finally:
        db.close()
