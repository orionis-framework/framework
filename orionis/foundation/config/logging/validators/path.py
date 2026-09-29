class __IsValidPath:

    def __call__(self, value: str, *, suffix: bool = False) -> None:
        """
        Validate that the value is a non-empty string representing a file path.

        Parameters
        ----------
        value : str
            The value to validate as a file path.
        suffix : bool, optional
            Whether to require the path to contain '{suffix}'. Default is
            False.

        Returns
        -------
        None

        Raises
        ------
        ValueError, TypeError
            If the value is not a non-empty string or does not meet path
            requirements.
        """
        # Check if value is a non-empty string
        if not isinstance(value, str):
            error_msg = (
                "File cache configuration error: 'path' must be a string, "
                f"got {type(value).__name__}."
            )
            raise TypeError(error_msg)
        if not value.strip():
            error_msg = (
                "File cache configuration error: 'path' must be a non-empty string."
            )
            raise ValueError(error_msg)

        # If suffix is required, ensure the path contains '{suffix}'
        if suffix and "{suffix}" not in value:
            error_msg = (
                "File cache configuration error: 'path' must contain "
                f"'{{suffix}}', got {value!r}."
            )
            raise ValueError(error_msg)

        # Ensure the path ends with '.log'
        if not value.endswith(".log"):
            error_msg = (
                "File cache configuration error: 'path' must end with '.log', "
                f"got {value!r}."
            )
            raise ValueError(error_msg)

# Exported singleton instance
IsValidPath = __IsValidPath()
