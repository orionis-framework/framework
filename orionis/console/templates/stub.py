import re
from pathlib import Path

# Validate names containing lowercase letters, digits, and underscores.
_NAME_RE: re.Pattern[str] = re.compile(r"[a-z][a-z0-9_]*")
_EXTENSION_RE: re.Pattern[str] = re.compile(r"[a-z][a-z0-9]*")
_TEMPLATE_DIR: Path = Path(__file__).parent
_CLASS_NAME_PLACEHOLDERS: tuple[str, str] = (
    "{{ class_name }}",
    "{{class_name}}",
)

class Stub:

    __slots__ = (
        "_class_name",
        "_classname",
        "_directory_parts",
        "_filename",
        "_postfix",
        "_prefix",
        "_replacements",
        "_template_name",
    )

    def __init__(
        self,
        template_name: str,
        class_name: str,
        prefix: str | None = None,
        postfix: str | None = None,
        replacements: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize a stub generator.

        Parameters
        ----------
        template_name : str
            Name of the template file without its ``.stub`` suffix.
        class_name : str
            Name used to derive the generated filename and class name.
        prefix : str | None, optional
            Prefix prepended to the derived filename and class name.
        postfix : str | None, optional
            Suffix appended to the derived filename and class name.
        replacements : dict[str, str] | None, optional
            Placeholder values to apply to the loaded template.

        Returns
        -------
        None
            The instance is initialized in place.
        """
        self._template_name: str = template_name
        self._class_name: str = class_name
        self._prefix: str | None = prefix
        self._postfix: str | None = postfix
        self._replacements: dict[str, str] | None = replacements
        self._filename: str | None = None
        self._classname: str | None = None
        self._directory_parts: tuple[str, ...] = ()

    def __parseName(self) -> tuple[str, ...]:
        """Normalize a generated name and reject unsafe path components.

        Returns
        -------
        tuple[str, ...]
            Directory components followed by the file stem.

        Raises
        ------
        ValueError
            If the name is empty, absolute, traverses a parent directory, or
            contains a component that cannot form a Python module name.
        """
        normalized = self._class_name.replace("\\", "/")
        parts = normalized.split("/")
        if (
            not normalized
            or normalized.startswith("/")
            or ":" in parts[0]
            or any(part in {"", ".", ".."} for part in parts)
        ):
            error_msg = f"Invalid filename '{self._class_name}' format."
            raise ValueError(error_msg)

        filename = parts[-1]
        suffix = Path(filename).suffix
        if suffix:
            filename = filename[:-len(suffix)]
        parts[-1] = filename

        if any(_NAME_RE.fullmatch(part.lower()) is None for part in parts):
            error_msg = f"Invalid filename '{self._class_name}' format."
            raise ValueError(error_msg)

        return tuple(parts)

    def __compileFilenameAndClassname(self) -> None:
        """
        Compile the generated filename and class name.

        Returns
        -------
        None
            The derived filename and class name are stored on the instance.

        Raises
        ------
        ValueError
            If the generated filename does not match the accepted format.
        """
        if self._filename is not None:
            return

        parts = self.__parseName()
        self._directory_parts = tuple(part.lower() for part in parts[:-1])
        source_name = parts[-1]

        filename = source_name.lower()
        postfix = self._postfix
        if postfix and not filename.endswith(postfix.lower()):
            filename += "_" + postfix.lower()
        self._filename = filename

        classname = "".join(
            word[0].upper() + word[1:]
            for word in source_name.split("_") if word
        )
        prefix = self._prefix
        if prefix and not classname.casefold().startswith(prefix.casefold()):
            classname = prefix[0].upper() + prefix[1:] + classname
        if postfix and not classname.casefold().endswith(postfix.casefold()):
            classname += postfix[0].upper() + postfix[1:]
        self._classname = classname

    def __loadTemplate(self) -> str:
        """
        Load the requested stub template.

        Returns
        -------
        str
            The unmodified template content.

        Raises
        ------
        FileNotFoundError
            If the requested stub file does not exist.
        ValueError
            If the template name does not identify a packaged stub.
        """
        if _NAME_RE.fullmatch(self._template_name) is None:
            error_msg = f"Invalid template name '{self._template_name}'."
            raise ValueError(error_msg)

        # Locate the packaged template file.
        stub_path: Path = _TEMPLATE_DIR / f"{self._template_name}.stub"

        try:
            return stub_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            error_msg: str = f"Stub file '{stub_path}' does not exist."
            raise FileNotFoundError(error_msg) from exc

    def __replaceTemplateContent(self, content: str) -> str:
        """
        Replace placeholders in the loaded template.

        Parameters
        ----------
        content : str
            Template content to update.

        Returns
        -------
        str
            Template content with the class name and replacements applied.

        Raises
        ------
        TypeError
            If a replacement key or value is not a string.
        """
        # Replace the derived class name in both supported placeholder forms.
        class_name = self._classname
        content = content.replace(_CLASS_NAME_PLACEHOLDERS[0], class_name)
        content = content.replace(_CLASS_NAME_PLACEHOLDERS[1], class_name)

        # If no additional replacements are provided, return the content as-is.
        if self._replacements is None:
            return content

        # Iterate over each replacement key-value pair and apply them to the content.
        for key, value in self._replacements.items():

            # Reject invalid replacement types before modifying the content.
            if not isinstance(key, str) or not isinstance(value, str):
                error_msg: str = (
                    f"Invalid type for key '{key}' or value '{value}'. "
                    "Both must be strings."
                )
                raise TypeError(error_msg)

            # Skip the class name replacement as it is handled separately.
            if key == "class_name":
                continue

            # Perform the actual replacement in the template content.
            default_key: str = "{{ " + key + " }}"
            fallback_key: str = "{{" + key + "}}"
            content = content.replace(default_key, value)
            content = content.replace(fallback_key, value)

        # Return the content after all replacements have been applied.
        return content

    def create(
        self,
        directory: Path,
        relative_to: Path | None = None,
        extension: str = "py",
    ) -> str:
        """
        Create the generated source file.

        Parameters
        ----------
        directory : Path
            Directory where the generated Python file is created.
        relative_to : Path | None, optional
            Path to which the generated file path should be made relative.
            If None, the file path is returned as an absolute path.
        extension : str, optional
            File extension for the generated Python file. Defaults to "py".

        Returns
        -------
        str
            Path to the generated file as a string.

        Raises
        ------
        FileNotFoundError
            If the requested stub template does not exist.
        TypeError
            If a replacement key or value is not a string.
        ValueError
            If the generated filename, template name, or extension is invalid.
        """
        if not isinstance(extension, str):
            error_msg = "The generated file extension must be a string."
            raise TypeError(error_msg)
        extension = extension.lstrip(".").lower()
        if _EXTENSION_RE.fullmatch(extension) is None:
            error_msg = f"Invalid file extension '{extension}'."
            raise ValueError(error_msg)

        self.__compileFilenameAndClassname()

        # Load the template content from the package directory.
        content: str = self.__loadTemplate()

        # Replace template placeholders with the provided values.
        content = self.__replaceTemplateContent(content)

        target_directory = directory.joinpath(*self._directory_parts)
        target_directory.mkdir(parents=True, exist_ok=True)
        file_path: Path = target_directory / f"{self._filename}.{extension}"

        # Create the target exclusively so a concurrent write cannot replace it.
        try:
            with file_path.open("x", encoding="utf-8") as target:
                target.write(content)
        except FileExistsError as exc:
            error_msg = f"File '{file_path}' already exists."
            raise FileExistsError(error_msg) from exc

        # If a root path is provided, make the file path relative to it.
        if relative_to is not None:
            file_path = file_path.relative_to(relative_to)

        # Return the path to the generated file as a string.
        return str(file_path)
