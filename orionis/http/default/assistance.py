from typing import TYPE_CHECKING, Any
from urllib.parse import quote, unquote_to_bytes

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

# Apply a conservative application limit to the complete outgoing URL.
CHATGPT_URL_MAX_LENGTH: int = 2048
_CHATGPT_URL_PREFIX: str = "https://chatgpt.com/?prompt="
_PROMPT_BUDGET: int = CHATGPT_URL_MAX_LENGTH - len(_CHATGPT_URL_PREFIX)
_PROMPT_START: str = (
    "Diagnose this Orionis Framework/Python error and suggest a fix. "
    "Respond in the language of locale "
)
_FRAME_HEADING: str = "\nFrames (most recent first):\n"
_SOURCE_NOTICE: str = "\n[Source snippets omitted to fit the URL limit.]"
_TRUNCATION_NOTICE: str = (
    "\n[Truncated to fit URL: source snippets omitted; "
    "{omitted} older frames omitted.]"
)
_MIN_FRAME_BUDGET: int = 48
_ESCAPE_WIDTH: int = 3

def _encode_bounded(
    value: str, limit: int, *, tail: bool = False,
) -> tuple[str, bool]:
    """
    Encode a bounded UTF-8 prefix or suffix.

    Parameters
    ----------
    value : str
        Text to encode.
    limit : int
        Maximum encoded length.
    tail : bool, optional
        Preserve the suffix instead of the prefix.

    Returns
    -------
    tuple[str, bool]
        Encoded text and whether the value was shortened.
    """
    if not value:
        return "", False
    if limit <= 0:
        return "", True
    candidate = value[-limit:] if tail else value[:limit]
    encoded = quote(candidate, safe="", errors="replace")
    if len(encoded) <= limit:
        return encoded, len(candidate) != len(value)

    # Keep complete percent escapes before removing partial UTF-8 characters.
    boundary = len(encoded) - limit if tail else limit
    escape = encoded.rfind("%", 0, boundary)
    if escape >= 0 and boundary - escape < _ESCAPE_WIDTH:
        boundary = escape + _ESCAPE_WIDTH if tail else escape
    segment = encoded[boundary:] if tail else encoded[:boundary]
    decoded = unquote_to_bytes(segment).decode("utf-8", errors="ignore")
    return quote(decoded, safe=""), True

def _encode_field(value: str, limit: int, *, tail: bool = False) -> str:
    """
    Encode a field and mark any truncation.

    Parameters
    ----------
    value : str
        Text to encode.
    limit : int
        Maximum encoded length before the truncation marker.
    tail : bool, optional
        Preserve the suffix instead of the prefix.

    Returns
    -------
    str
        Encoded text with a truncation marker when necessary.
    """
    encoded, shortened = _encode_bounded(value, limit, tail=tail)
    if not shortened:
        return encoded
    encoded, _ = _encode_bounded(value, limit - len("..."), tail=tail)
    return f"...{encoded}" if tail else f"{encoded}..."

def _header_parts(
    traceback_data: dict[str, Any], locale: str,
    request_method: str, request_path: str,
) -> Iterator[str]:
    """
    Yield the diagnostic request and exception fields.

    Parameters
    ----------
    traceback_data : dict[str, Any]
        Parsed exception data.
    locale : str
        Requested response locale.
    request_method : str
        HTTP method associated with the request.
    request_path : str
        HTTP path associated with the request.

    Returns
    -------
    Iterator[str]
        Individual unencoded header fields.
    """
    yield from (
        _PROMPT_START, locale, ".\n",
        traceback_data["error_type"], ": ", traceback_data["error_message"],
        "\nRequest: ", request_method, " ", request_path, _FRAME_HEADING,
    )

def _prompt_parts(
    traceback_data: dict[str, Any], locale: str,
    request_method: str, request_path: str, *, sources: bool,
) -> Iterator[str]:
    """
    Yield the diagnostic header and captured frames.

    Parameters
    ----------
    traceback_data : dict[str, Any]
        Parsed exception data.
    locale : str
        Requested response locale.
    request_method : str
        HTTP method associated with the request.
    request_path : str
        HTTP path associated with the request.
    sources : bool
        Whether to include failing source lines.

    Returns
    -------
    Iterator[str]
        Unencoded prompt fields in traceback order.
    """
    yield from _header_parts(
        traceback_data, locale, request_method, request_path,
    )
    yield from _frame_parts(traceback_data["stack_trace"], sources=sources)

def _frame_parts(
    frames: Iterable[dict[str, Any]], *, sources: bool,
) -> Iterator[str]:
    """
    Yield frame locations and optional source lines.

    Parameters
    ----------
    frames : Iterable[dict[str, Any]]
        Traceback frames in most-recent-first order.
    sources : bool
        Whether to include failing source lines.

    Returns
    -------
    Iterator[str]
        Unencoded frame fields.
    """
    for frame in frames:
        yield from (
            frame["filename"], ":", str(frame["lineno"]), " ",
            frame["name"], "\n",
        )
        if sources and frame.get("line_code"):
            yield "  "
            yield frame["line_code"]
            yield "\n"

def _try_prompt(
    parts: Iterable[str], *, notice: str = "", prefix: str = "",
    limit: int = _PROMPT_BUDGET,
) -> str | None:
    """
    Encode a prompt only when all fields fit within the limit.

    Parameters
    ----------
    parts : Iterable[str]
        Prompt fields to encode.
    notice : str, optional
        Limit notice appended to the prompt.
    prefix : str, optional
        Already encoded prompt prefix.
    limit : int, optional
        Maximum encoded prompt length.

    Returns
    -------
    str | None
        Complete encoded prompt, or ``None`` when a field does not fit.
    """
    encoded_notice = quote(notice, safe="")
    remaining = limit - len(encoded_notice) - len(prefix)
    encoded_parts: list[str] = [prefix]
    for part in parts:
        encoded, shortened = _encode_bounded(part, remaining)
        if shortened:
            return None
        encoded_parts.append(encoded)
        remaining -= len(encoded)
    encoded_parts.append(encoded_notice)
    return "".join(encoded_parts)

def _compact_header(
    traceback_data: dict[str, Any], locale: str,
    request_method: str, request_path: str,
) -> str:
    """
    Build a bounded header for the diagnostic prompt.

    Parameters
    ----------
    traceback_data : dict[str, Any]
        Parsed exception data.
    locale : str
        Requested response locale.
    request_method : str
        HTTP method associated with the request.
    request_path : str
        HTTP path associated with the request.

    Returns
    -------
    str
        Encoded diagnostic header.
    """
    return "".join((
        quote(_PROMPT_START, safe=""), _encode_field(locale, 64),
        ".%0A", _encode_field(traceback_data["error_type"], 96), "%3A%20",
        _encode_field(traceback_data["error_message"], 256), "%0ARequest%3A%20",
        _encode_field(request_method, 24), "%20",
        _encode_field(request_path, 128), quote(_FRAME_HEADING, safe=""),
    ))

def _compact_frame(frame: dict[str, Any], budget: int) -> str:
    """
    Build a compact representation of one traceback frame.

    Parameters
    ----------
    frame : dict[str, Any]
        Parsed traceback frame.
    budget : int
        Maximum encoded length assigned to the frame.

    Returns
    -------
    str
        Encoded compact frame location.
    """
    lineno = _encode_field(str(frame["lineno"]), 12)
    name_budget = max(12, min(64, budget // 4))
    filename_budget = budget - name_budget - len(lineno) - len("%3A%20%0A")
    return "".join((
        _encode_field(frame["filename"], filename_budget, tail=True),
        "%3A", lineno, "%20", _encode_field(frame["name"], name_budget), "%0A",
    ))

def _compact_prompt(
    traceback_data: dict[str, Any], locale: str,
    request_method: str, request_path: str,
) -> str:
    """
    Build a compact prompt when the full traceback does not fit.

    Parameters
    ----------
    traceback_data : dict[str, Any]
        Parsed exception data.
    locale : str
        Requested response locale.
    request_method : str
        HTTP method associated with the request.
    request_path : str
        HTTP path associated with the request.

    Returns
    -------
    str
        Encoded prompt within the configured URL budget.
    """
    header = _compact_header(traceback_data, locale, request_method, request_path)
    frames = traceback_data["stack_trace"]
    complete_locations = _try_prompt(
        _frame_parts(frames, sources=False), prefix=header,
        notice=_TRUNCATION_NOTICE.format(omitted=0),
    )
    if complete_locations is not None:
        return complete_locations
    reserved_notice = quote(
        _TRUNCATION_NOTICE.format(omitted=len(frames)), safe="",
    )
    remaining = _PROMPT_BUDGET - len(header) - len(reserved_notice)
    frame_count = min(len(frames), remaining // _MIN_FRAME_BUDGET)
    parts = [header]
    if frame_count:
        frame_budget = remaining // frame_count
        for index in range(frame_count):
            frame = _compact_frame(frames[index], frame_budget)
            parts.append(frame)
            remaining -= len(frame)
    while frame_count < len(frames) and remaining:
        frame_budget = min(remaining, max(
            _MIN_FRAME_BUDGET, remaining // (len(frames) - frame_count),
        ))
        frame = _try_prompt(
            _frame_parts((frames[frame_count],), sources=False),
            limit=frame_budget,
        )
        if frame is None:
            if frame_budget < _MIN_FRAME_BUDGET:
                break
            frame = _compact_frame(frames[frame_count], frame_budget)
        parts.append(frame)
        remaining -= len(frame)
        frame_count += 1
    parts.append(quote(
        _TRUNCATION_NOTICE.format(omitted=len(frames) - frame_count), safe="",
    ))
    return "".join(parts)

def build_chatgpt_url(
    traceback_data: dict[str, Any], locale: str,
    request_method: str, request_path: str,
) -> tuple[str, bool]:
    """
    Build a compact, encoded diagnostic link within a local URL budget.

    Include every captured frame and its failing source line when they fit.
    Otherwise omit source snippets before shortening fields or dropping the
    oldest frames. The limit is an application compatibility policy, not a
    published ChatGPT maximum. No request data is cached or transmitted here.

    Parameters
    ----------
    traceback_data : dict[str, Any]
        ExceptionParser output, including frames in most-recent-first order.
    locale : str
        Locale requested for the diagnostic response.
    request_method : str
        HTTP method associated with the failed request.
    request_path : str
        HTTP path associated with the failed request.

    Returns
    -------
    tuple[str, bool]
        ASCII URL and whether source, fields, or frames were omitted.
    """
    encoded = _try_prompt(_prompt_parts(
        traceback_data, locale, request_method, request_path, sources=True,
    ))
    if encoded is not None:
        return _CHATGPT_URL_PREFIX + encoded, False
    encoded = _try_prompt(
        _prompt_parts(
            traceback_data, locale, request_method, request_path, sources=False,
        ),
        notice=_SOURCE_NOTICE,
    )
    if encoded is None:
        encoded = _compact_prompt(
            traceback_data, locale, request_method, request_path,
        )
    return _CHATGPT_URL_PREFIX + encoded, True
