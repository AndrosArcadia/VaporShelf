def validate_and_calculate_progress(current_page: int, total_pages: int) -> float:
    if total_pages <= 0:
        raise ValueError("total_pages must be greater than zero")
    if current_page < 0 or current_page > total_pages:
        raise ValueError("current_page must be between 0 and total_pages")
    return round((current_page / total_pages) * 100, 2)


def build_progress_key(user_id: str, document_id: str) -> str:
    return f"progress:{user_id}:{document_id}"
