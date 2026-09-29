def parse_range(value: str | None, file_size: int) -> tuple[int, int] | None:
    """
    Parse a byte range into an interval with an exclusive end offset.

    Parameters
    ----------
    value : str | None
        Value of the HTTP ``Range`` header.
    file_size : int
        Size of the requested file in bytes.

    Returns
    -------
    tuple[int, int] | None
        Valid byte interval, or ``None`` for an invalid or unsatisfiable
        range.
    """
    if not value or not value.startswith("bytes=") or file_size <= 0:
        return None
    start_text, separator, end_text = value[6:].partition("-")
    if not separator:
        return None
    if start_text and (not start_text.isascii() or not start_text.isdecimal()):
        return None
    if end_text and (not end_text.isascii() or not end_text.isdecimal()):
        return None
    try:
        if start_text:
            start = int(start_text)
            end = min(int(end_text) + 1, file_size) if end_text else file_size
        else:
            suffix = int(end_text)
            start, end = max(0, file_size - suffix), file_size
        return (start, end) if start < end else None
    except ValueError:
        return None
