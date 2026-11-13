"""Read supported raster headers without decoding image pixels."""

import struct

# Magic numbers identifying every supported raster format.
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
"""Magic numbers identifying every supported raster format."""
_JPEG_SIGNATURE = b"\xff\xd8"
"""Jpeg signature value used by ``image_probe``."""
_BMP_SIGNATURE = b"BM"
"""Bmp signature value used by ``image_probe``."""
_GIF_SIGNATURES = (b"GIF87a", b"GIF89a")
"""Gif signatures definitions used by ``image_probe``."""

# JPEG start-of-frame markers; their payload carries the image dimensions.
_SOF_MARKERS = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF},
)
"""JPEG start-of-frame markers; their payload carries the image dimensions."""

# Byte introducing every JPEG marker.
_JPEG_FILL = 0xFF
"""Byte introducing every JPEG marker."""

# JPEG markers that carry no payload and are skipped two bytes at a time.
_STANDALONE_MARKERS = frozenset({0x01, *range(0xD0, 0xD8)})
"""JPEG markers that carry no payload and are skipped two bytes at a time."""

# Minimum header length required by each probe before unpacking.
_PNG_HEADER = 24
"""Minimum header length required by each probe before unpacking."""
_GIF_HEADER = 10
"""Gif header value used by ``image_probe``."""
_BMP_HEADER = 26
"""Bmp header value used by ``image_probe``."""
_BMP_CORE_SIZE = 12
"""DIB header size identifying unsigned sixteen-bit CORE dimensions."""
_BMP_INFO_PREFIX = 16
"""Minimum DIB header size carrying thirty-two-bit dimensions."""
_WEBP_HEADER = 20
"""Minimum RIFF and first-chunk headers needed to identify WebP storage."""
_WEBP_FRAME_HEADER = 30
"""Minimum prefix carrying VP8 or VP8X dimensions."""
_WEBP_LOSSLESS_HEADER = 25
"""Minimum prefix carrying the VP8L signature and packed dimensions."""
_WEBP_FRAME_SIZE = 10
"""Bytes required in the VP8 or VP8X dimension prefix."""
_WEBP_LOSSLESS_SIZE = 5
"""Bytes required in the VP8L signature and dimension prefix."""
_WEBP_LOSSLESS_SIGNATURE = 0x2F
"""Signature byte that must begin a lossless WebP bitstream."""
_JPEG_LENGTH_SIZE = 2
"""Length-field bytes included in every variable-length JPEG segment."""
_JPEG_SOF_BASE = 8
"""SOF segment bytes preceding the three-byte component entries."""

# Mask isolating the 14-bit dimensions stored in WebP bitstreams.
_WEBP_MASK = 0x3FFF
"""Mask isolating the 14-bit dimensions stored in WebP bitstreams."""


def _probe_png(data: bytes) -> tuple[str, int, int] | None:
    """
    Read the dimensions stored in a PNG ``IHDR`` chunk.

    Parameters
    ----------
    data : bytes
        Raw image content.

    Returns
    -------
    tuple[str, int, int] | None
        Format name with width and height, or ``None`` when not a PNG.
    """
    if len(data) < _PNG_HEADER or not data.startswith(_PNG_SIGNATURE):
        return None
    if data[8:16] != b"\x00\x00\x00\rIHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return ("png", width, height)


def _probe_gif(data: bytes) -> tuple[str, int, int] | None:
    """
    Read the dimensions stored in a GIF logical screen descriptor.

    Parameters
    ----------
    data : bytes
        Raw image content.

    Returns
    -------
    tuple[str, int, int] | None
        Format name with width and height, or ``None`` when not a GIF.
    """
    if len(data) < _GIF_HEADER or not data.startswith(_GIF_SIGNATURES):
        return None
    width, height = struct.unpack("<HH", data[6:10])
    return ("gif", width, height)


def _probe_bmp(data: bytes) -> tuple[str, int, int] | None:
    """
    Read the dimensions stored in a BMP information header.

    Parameters
    ----------
    data : bytes
        Raw image content.

    Returns
    -------
    tuple[str, int, int] | None
        Format name with width and height, or ``None`` when not a BMP.
    """
    if len(data) < _BMP_HEADER or not data.startswith(_BMP_SIGNATURE):
        return None
    header_size = struct.unpack("<I", data[14:18])[0]
    if header_size == _BMP_CORE_SIZE:
        width, height = struct.unpack("<HH", data[18:22])
    elif header_size >= _BMP_INFO_PREFIX:
        width, height = struct.unpack("<ii", data[18:26])
    else:
        return None
    # Windows top-down bitmaps store a negative height; width stays positive.
    return ("bmp", width, abs(height))


def _probe_webp(data: bytes) -> tuple[str, int, int] | None:
    """
    Read the dimensions of the lossy, lossless or extended WebP bitstream.

    Parameters
    ----------
    data : bytes
        Raw image content.

    Returns
    -------
    tuple[str, int, int] | None
        Format name with width and height, or ``None`` when not a WebP.
    """
    if len(data) < _WEBP_HEADER or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None

    chunk = data[12:16]
    chunk_size = struct.unpack("<I", data[16:20])[0]

    if chunk == b"VP8X":
        if len(data) < _WEBP_FRAME_HEADER or chunk_size < _WEBP_FRAME_SIZE:
            return None
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
    elif chunk == b"VP8L":
        if (
            len(data) < _WEBP_LOSSLESS_HEADER
            or chunk_size < _WEBP_LOSSLESS_SIZE
            or data[20] != _WEBP_LOSSLESS_SIGNATURE
        ):
            return None
        bits = int.from_bytes(data[21:25], "little")
        width = (bits & _WEBP_MASK) + 1
        height = ((bits >> 14) & _WEBP_MASK) + 1
    elif chunk == b"VP8 ":
        if (
            len(data) < _WEBP_FRAME_HEADER
            or chunk_size < _WEBP_FRAME_SIZE
            or data[23:26] != b"\x9d\x01\x2a"
        ):
            return None
        raw_width, raw_height = struct.unpack("<HH", data[26:30])
        width = raw_width & _WEBP_MASK
        height = raw_height & _WEBP_MASK
    else:
        return None

    return ("webp", width, height)


def _jpeg_frame(
    data: bytes,
    index: int,
    segment_size: int,
) -> tuple[str, int, int] | None:
    """Read dimensions from a structurally complete JPEG frame segment.

    Parameters
    ----------
    data : bytes
        Header content containing the complete segment.
    index : int
        Offset of the segment marker.
    segment_size : int
        Segment length, including its two-byte length field.

    Returns
    -------
    tuple[str, int, int] | None
        JPEG format and dimensions, or ``None`` for an invalid component layout.
    """
    if segment_size < _JPEG_SOF_BASE:
        return None
    components = data[index + 9]
    if not components or segment_size != _JPEG_SOF_BASE + 3 * components:
        return None
    height, width = struct.unpack(">HH", data[index + 5 : index + 9])
    return ("jpeg", width, height)


def _probe_jpeg(data: bytes) -> tuple[str, int, int] | None:
    """
    Walk the JPEG segments until a start-of-frame marker is found.

    Parameters
    ----------
    data : bytes
        Raw image content.

    Returns
    -------
    tuple[str, int, int] | None
        Format name with width and height, or ``None`` when not a JPEG.
    """
    if not data.startswith(_JPEG_SIGNATURE):
        return None

    index = 2
    total = len(data)

    while index + 4 <= total:
        if data[index] != _JPEG_FILL:
            return None

        marker = data[index + 1]
        if marker == _JPEG_FILL:
            index += 1
            continue
        if marker in (0xD9, 0xDA):
            return None

        if marker in _STANDALONE_MARKERS:
            index += 2
            continue

        segment_size = struct.unpack(">H", data[index + 2 : index + 4])[0]
        if segment_size < _JPEG_LENGTH_SIZE or index + 2 + segment_size > total:
            return None
        if marker in _SOF_MARKERS:
            return _jpeg_frame(data, index, segment_size)
        index += 2 + segment_size

    return None


# Probes are ordered by signature cost; each one rejects foreign formats first.
_PROBES = (_probe_png, _probe_jpeg, _probe_gif, _probe_bmp, _probe_webp)
"""Probes are ordered by signature cost; each one rejects foreign formats first."""


def probe_image(data: bytes) -> tuple[str, int, int] | None:
    """
    Identify a raster image and read its dimensions from the header.

    Parameters
    ----------
    data : bytes
        Raw image content.

    Returns
    -------
    tuple[str, int, int] | None
        Format name with width and height, or ``None`` when the content is
        not a supported header or either dimension is zero or negative. Inspect
        only format metadata; do not decode pixels or verify compressed content.
    """
    for probe in _PROBES:
        result = probe(data)
        if result is not None and result[1] > 0 and result[2] > 0:
            return result
    return None
