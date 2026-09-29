class Timestamps:

    def __init__(self, *, timezone: bool = True) -> None:
        """
        Initialize a timestamp column definition.

        Parameters
        ----------
        timezone : bool, optional
            Whether the timestamp should include timezone information.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.timezone = timezone
