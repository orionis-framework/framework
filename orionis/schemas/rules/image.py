from orionis.schemas.rules.image_probe import probe_image
from orionis.schemas.rules.measure import read_content
from orionis.schemas.rule import Rule

class Image(Rule):
    """
    Ensure an uploaded file is a raster image.

    The format is detected from the file header, so a mislabelled extension
    or content type never fools the check. JPEG, PNG, GIF, BMP and WebP are
    recognized.
    """

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = "File must be a valid image."
    __code__ = "image"

    def enforce(
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
        content = read_content(value)
        if content is None:
            return False

        return probe_image(content) is not None
