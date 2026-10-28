import hashlib
import math
import platform
import urllib.request
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

# Pinned oha version and asset digests for supported platforms.
OHA_VERSION = "1.16.0"

# SHA-256 digests of the official release assets.
OHA_ASSETS = {
    ("Linux", "amd64"): (
        "oha-linux-amd64",
        "620bb9e16fb53eabc9a3fc45f88bdb41fefa3fee5c05e75892011ce320391716",
    ),
    ("Linux", "arm64"): (
        "oha-linux-arm64",
        "99a790eb8c3e0feaca974bd6b32f0f8d4426a0c5b289f39e833e5b2c7529cd39",
    ),
    ("Darwin", "amd64"): (
        "oha-macos-amd64",
        "5ecbfc5233e3f1d30384e142a9a8dd7ebf9d3298ab22476fabac44a8f2117e08",
    ),
    ("Darwin", "arm64"): (
        "oha-macos-arm64",
        "7dea53ecb8342a7a067e1976fd0aef44ac33d9cc6b1e65c53637ffb932da63c4",
    ),
    ("Windows", "amd64"): (
        "oha-windows-amd64.exe",
        "d692d392e958e7e8e1b16810287e74a835a62255b079ba2766a4b3b04499f267",
    ),
}

def install_oha(directory: Path) -> Path:
    """
    Download and verify the pinned oha binary.

    Parameters
    ----------
    directory : Path
        Existing directory in which to store the executable.

    Returns
    -------
    Path
        Path to the downloaded executable with its SHA-256 verified.

    Raises
    ------
    RuntimeError
        If the platform is unsupported or the download fails verification.
    """
    # Map architecture aliases to the official release asset names.
    machine = platform.machine().lower()
    architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(machine, machine)
    try:
        asset, digest = OHA_ASSETS[(platform.system(), architecture)]
    except KeyError as error:
        error_msg = "No pinned oha binary for this platform; install oha and use --oha"
        raise RuntimeError(error_msg) from error
    # Verify the complete download before writing an executable file.
    url = f"https://github.com/hatoo/oha/releases/download/v{OHA_VERSION}/{asset}"
    with urllib.request.urlopen(url, timeout=45) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != digest:
        error_msg = f"SHA-256 mismatch for {asset}"
        raise RuntimeError(error_msg)
    destination = directory / asset
    destination.write_bytes(data)
    destination.chmod(0o755)
    return destination

def _nonnegative_number(value: object) -> float:
    """
    Validate and convert a finite nonnegative measurement.

    Parameters
    ----------
    value : object
        Integer or float read from the oha payload.

    Returns
    -------
    float
        Validated finite value greater than or equal to zero.

    Raises
    ------
    ValueError
        If the value is boolean, nonnumeric, nonfinite, or negative.
    """
    # Reject booleans even though Python treats them as integer subclasses.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        error_msg = "Expected a finite nonnegative number in oha output"
        # A malformed JSON payload consistently raises ValueError.
        raise ValueError(error_msg)  # noqa: TRY004
    number = float(value)
    if not math.isfinite(number) or number < 0:
        error_msg = "Expected a finite nonnegative number in oha output"
        raise ValueError(error_msg)
    return number

def _count(value: object) -> int:
    """
    Validate an integral request or error count.

    Parameters
    ----------
    value : object
        Nonnegative numeric count read from the oha payload.

    Returns
    -------
    int
        Validated count without a fractional component.

    Raises
    ------
    ValueError
        If the value is not a finite nonnegative integer count.
    """
    # Reject fractional counts instead of silently truncating malformed data.
    number = _nonnegative_number(value)
    if not number.is_integer():
        error_msg = "Expected an integer request count in oha output"
        raise ValueError(error_msg)
    return int(number)

def parse_measurement(raw: dict[str, Any]) -> dict[str, int | float]:
    """
    Normalize successful throughput, errors, and latency from oha output.

    Parameters
    ----------
    raw : dict[str, Any]
        Decoded oha JSON with status counts, errors, timing, and percentiles.

    Returns
    -------
    dict[str, int | float]
        HTTP 200 counts, errors, elapsed seconds, requests/s, and latencies in ms.

    Raises
    ------
    ValueError
        If numeric data is invalid, elapsed time is zero, or no HTTP 200 exists.
    KeyError
        If a required payload section or measurement is missing.
    """
    # Exclude HTTP and transport failures from successful-request throughput.
    statuses = raw["statusCodeDistribution"]
    successes = _count(statuses.get("200", 0))
    errors = sum(_count(count) for code, count in statuses.items() if code != "200")
    errors += sum(_count(count) for count in raw["errorDistribution"].values())
    elapsed = _nonnegative_number(raw["summary"]["total"])
    if elapsed == 0 or successes == 0:
        error_msg = "Load test needs a positive elapsed time and at least one HTTP 200"
        raise ValueError(error_msg)
    # Convert every latency from seconds to milliseconds at the parsing boundary.
    return {
        "requests": successes,
        "errors": errors,
        "elapsed_seconds": elapsed,
        "requests_per_second": successes / elapsed,
        "mean_latency_ms": _nonnegative_number(raw["summary"]["average"]) * 1000,
        **{
            f"{percentile}_latency_ms": _nonnegative_number(
                raw["latencyPercentiles"][percentile],
            )
            * 1000
            for percentile in ("p50", "p95", "p99")
        },
    }
