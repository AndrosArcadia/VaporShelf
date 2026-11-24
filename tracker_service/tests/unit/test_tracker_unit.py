import pytest
from app.logic import build_progress_key, validate_and_calculate_progress


def test_calculate_progress_percentage():
    assert validate_and_calculate_progress(42, 300) == 14.0
    assert validate_and_calculate_progress(300, 300) == 100.0


def test_invalid_page_numbers():
    with pytest.raises(ValueError):
        validate_and_calculate_progress(305, 300)
    with pytest.raises(ValueError):
        validate_and_calculate_progress(10, 0)


def test_build_progress_key():
    assert build_progress_key("usr-102", "doc-1") == "progress:usr-102:doc-1"
