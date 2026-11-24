import pytest
from app.logic import can_user_access_document, validate_file_type


def test_validate_file_type_valid():
    assert validate_file_type("PDF") == "pdf"
    assert validate_file_type(" epub ") == "epub"


def test_validate_file_type_invalid():
    with pytest.raises(ValueError):
        validate_file_type("exe")


def test_access_control_logic():
    assert can_user_access_document(False, "usr-1", "usr-2", []) is True
    assert can_user_access_document(True, "usr-1", "usr-1", []) is True
    assert can_user_access_document(True, "usr-1", "usr-2", []) is False
    assert can_user_access_document(True, "usr-1", "usr-2", ["usr-2"]) is True
