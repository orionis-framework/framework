# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure an uploaded file has a supported raster image header."""

from orionis.schemas.rules.image_probe import probe_image
from orionis.schemas.rules.measure import read_content
from orionis.schemas.rule import Rule


class Image(Rule):
    """
    Ensure an uploaded file has a supported raster image header.

    The format is detected from the file header, so a mislabelled extension
    or content type does not determine the result. Recognize JPEG, PNG, GIF,
    BMP and WebP headers with positive dimensions. Do not decode pixels or
    validate checksums and compressed image data.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    __message__ = "File must be a valid image."
    """Error text for message: ``File must be a valid image.``."""
    __code__ = "image"
    """Code identifier: ``image``."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate an uploaded file as an image.

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
        content = await read_content(value)
        if content is None:
            return False

        return probe_image(content) is not None
