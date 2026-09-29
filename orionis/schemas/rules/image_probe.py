import struct

# Magic numbers identifying every supported raster format.
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8"
_BMP_SIGNATURE = b"BM"
_GIF_SIGNATURES = (b"GIF87a", b"GIF89a")

# JPEG start-of-frame markers; their payload carries the image dimensions.
_SOF_MARKERS = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF},
)

# Byte introducing every JPEG marker.
_JPEG_FILL = 0xFF

# JPEG markers that carry no payload and are skipped two bytes at a time.
_STANDALONE_MARKERS = frozenset({0x01, 0xFF, *range(0xD0, 0xDA)})

# Minimum header length required by each probe before unpacking.
_PNG_HEADER = 24
_GIF_HEADER = 10
_BMP_HEADER = 26
_WEBP_HEADER = 30
_JPEG_SEGMENT = 9

# Mask isolating the 14-bit dimensions stored in WebP bitstreams.
_WEBP_MASK = 0x3FFF

def _probePng(data: bytes) -> tuple[str, int, int] | None:
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
    width, height = struct.unpack(">II", data[16:24])
    return ("png", width, height)

def _probeGif(data: bytes) -> tuple[str, int, int] | None:
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

def _probeBmp(data: bytes) -> tuple[str, int, int] | None:
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
    width, height = struct.unpack("<ii", data[18:26])
    # Bottom-up bitmaps store a negative height.
    return ("bmp", abs(width), abs(height))

def _probeWebp(data: bytes) -> tuple[str, int, int] | None:
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

    if chunk == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
    elif chunk == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        width = (bits & _WEBP_MASK) + 1
        height = ((bits >> 14) & _WEBP_MASK) + 1
    elif chunk == b"VP8 ":
        raw_width, raw_height = struct.unpack("<HH", data[26:30])
        width = raw_width & _WEBP_MASK
        height = raw_height & _WEBP_MASK
    else:
        return None

    return ("webp", width, height)

def _probeJpeg(data: bytes) -> tuple[str, int, int] | None:
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

    while index + _JPEG_SEGMENT <= total:
        # Segments always start with a fill byte; resynchronize on noise.
        if data[index] != _JPEG_FILL:
            index += 1
            continue

        marker = data[index + 1]

        if marker in _SOF_MARKERS:
            height, width = struct.unpack(">HH", data[index + 5 : index + 9])
            return ("jpeg", width, height)

        if marker in _STANDALONE_MARKERS:
            index += 2
            continue

        index += 2 + struct.unpack(">H", data[index + 2 : index + 4])[0]

    return None

# Probes are ordered by signature cost; each one rejects foreign formats first.
_PROBES = (_probePng, _probeJpeg, _probeGif, _probeBmp, _probeWebp)

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
        not a supported image.
    """
    for probe in _PROBES:
        result = probe(data)
        if result is not None:
            return result
    return None
