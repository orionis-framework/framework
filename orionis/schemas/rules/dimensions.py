from orionis.schemas.rules.image_probe import probe_image
from orionis.schemas.rules.measure import read_content
from orionis.schemas.rule import Rule

def _parse_ratio(raw: object, name: str) -> float | None:
    """
    Normalize a ratio constraint into a floating point value.

    Parameters
    ----------
    raw : object
        Ratio expressed as a number or as a ``"width/height"`` string.
    name : str
        Constraint name reported when the value cannot be parsed.

    Returns
    -------
    float | None
        Parsed ratio, or ``None`` when no constraint was supplied.

    Raises
    ------
    ValueError
        If the value is neither a number nor a parsable fraction.
    """
    if raw is None:
        return None

    if isinstance(raw, int | float) and not isinstance(raw, bool):
        return float(raw)

    if isinstance(raw, str):
        try:
            numerator, separator, denominator = raw.partition("/")
            return (
                float(numerator) / float(denominator)
                if separator
                else float(numerator)
            )
        except (ValueError, ZeroDivisionError) as exc:
            error_msg = f"Invalid '{name}' value: {raw!r}."
            raise ValueError(error_msg) from exc

    error_msg = f"Invalid '{name}' value: {raw!r}."
    raise ValueError(error_msg)

class Dimensions(Rule):
    """
    Ensure an uploaded image satisfies the given dimension constraints.

    Widths and heights are read from the image header, so no third-party
    imaging library is required. Ratios accept either a number or a
    ``"width/height"`` string such as ``"3/2"``.
    """

    # ruff: noqa: ARG002

    __slots__ = (
        "_height",
        "_max_height",
        "_max_ratio",
        "_max_width",
        "_min_height",
        "_min_ratio",
        "_min_width",
        "_ratio",
        "_width",
    )

    __message__ = "Image must satisfy the required dimensions."
    __code__ = "dimensions"

    def __init__(  # noqa: PLR0913
        self,
        *,
        min_width: int | None = None,
        max_width: int | None = None,
        min_height: int | None = None,
        max_height: int | None = None,
        width: int | None = None,
        height: int | None = None,
        ratio: float | str | None = None,
        min_ratio: float | str | None = None,
        max_ratio: float | str | None = None,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the accepted dimension constraints.

        Parameters
        ----------
        min_width : int | None, optional
            Lowest accepted width in pixels.
        max_width : int | None, optional
            Highest accepted width in pixels.
        min_height : int | None, optional
            Lowest accepted height in pixels.
        max_height : int | None, optional
            Highest accepted height in pixels.
        width : int | None, optional
            Exact required width in pixels.
        height : int | None, optional
            Exact required height in pixels.
        ratio : float | str | None, optional
            Exact required aspect ratio.
        min_ratio : float | str | None, optional
            Lowest accepted aspect ratio.
        max_ratio : float | str | None, optional
            Highest accepted aspect ratio.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If any ratio constraint cannot be parsed.
        """
        super().__init__(message=message)
        self._min_width: int | None = min_width
        self._max_width: int | None = max_width
        self._min_height: int | None = min_height
        self._max_height: int | None = max_height
        self._width: int | None = width
        self._height: int | None = height
        self._ratio: float | None = _parse_ratio(ratio, "ratio")
        self._min_ratio: float | None = _parse_ratio(min_ratio, "min_ratio")
        self._max_ratio: float | None = _parse_ratio(max_ratio, "max_ratio")

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate an uploaded image against the dimension constraints.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value to validate.
        instance : object
            Owning object instance. This argument is accepted for
            interface compatibility.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        content = read_content(value)
        if content is None:
            return False

        probed = probe_image(content)
        if probed is None:
            return False

        _, width, height = probed
        if width == 0 or height == 0:
            return False

        return self.__checkBounds(width, height) and self.__checkRatio(width, height)

    def __checkBounds(self, width: int, height: int) -> bool:
        """
        Check the pixel dimensions against the configured bounds.

        Parameters
        ----------
        width : int
            Image width in pixels.
        height : int
            Image height in pixels.

        Returns
        -------
        bool
            Return ``True`` when every configured bound is satisfied.
        """
        return not (
            (self._width is not None and width != self._width)
            or (self._height is not None and height != self._height)
            or (self._min_width is not None and width < self._min_width)
            or (self._max_width is not None and width > self._max_width)
            or (self._min_height is not None and height < self._min_height)
            or (self._max_height is not None and height > self._max_height)
        )

    def __checkRatio(self, width: int, height: int) -> bool:
        """
        Check the aspect ratio against the configured constraints.

        Parameters
        ----------
        width : int
            Image width in pixels.
        height : int
            Image height in pixels.

        Returns
        -------
        bool
            Return ``True`` when every configured ratio is satisfied.
        """
        actual = width / height

        # One pixel of slack, so rounding in the source image never fails.
        tolerance = 1 / max(width, height)

        return not (
            (self._ratio is not None and abs(actual - self._ratio) > tolerance)
            or (self._min_ratio is not None and actual < self._min_ratio)
            or (self._max_ratio is not None and actual > self._max_ratio)
        )
