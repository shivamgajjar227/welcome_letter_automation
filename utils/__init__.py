def safe_str(value):
    """
    Safely convert any value to string.
    - If None → return empty string
    - Else → return str(value)
    """
    return "" if value is None else str(value)