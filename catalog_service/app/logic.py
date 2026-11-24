ALLOWED_FILE_TYPES = {"pdf", "epub"}


def validate_file_type(file_type: str) -> str:
    normalized = file_type.strip().lower()
    if normalized not in ALLOWED_FILE_TYPES:
        raise ValueError(f"Unsupported file type: {file_type}")
    return normalized


def can_user_access_document(
    is_private: bool,
    owner_id: str,
    requester_id: str,
    approved_users: list[str],
) -> bool:
    if not is_private:
        return True
    if requester_id == owner_id:
        return True
    return requester_id in approved_users
