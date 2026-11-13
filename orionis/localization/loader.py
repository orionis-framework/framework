# ruff: noqa: TC001, TC003
# Resolve public path and mapping annotations during runtime introspection.
"""Load translation sources from the configured language path."""

from __future__ import annotations
from pathlib import Path
import msgspec
from orionis.localization.contracts.loader import ITranslationLoader
from orionis.localization.exceptions import (
    InvalidLocaleException,
    TranslationException,
    TranslationFileNotFoundException,
    TranslationSyntaxException,
)
from orionis.localization.types import TranslationMap
from orionis.localization.validators import validate_locale


class TranslationLoader(ITranslationLoader):
    """
    Load translation sources from the configured language path.

    The loader reads root JSON files (``{path}/{locale}.json``) whose
    keys are the literal source texts, and grouped JSON files
    (``{path}/{locale}/{group}.json``) flattened with dot notation such
    as ``validation.required``. Decoding is performed with ``msgspec``
    using its native JSON decoder. The loader holds no cache: that concern
    belongs to the repository.

    Notes
    -----
    Translation files are read as raw bytes and decoded as UTF-8 JSON.
    A source stored in any other encoding raises
    :class:`orionis.localization.TranslationSyntaxException`, like any other unusable
    payload.
    """

    __slots__ = ("_path",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, path: Path) -> None:
        """
        Initialize the loader with the language directory.

        Parameters
        ----------
        path : pathlib.Path
            Absolute directory containing the translation sources.

        Returns
        -------
        None
            No return value.
        """
        self._path = path.resolve()
        """Absolute directory containing the translation sources."""

    def load(self, locale: str) -> TranslationMap:
        """
        Load every translation available for *locale*.

        Grouped files are merged first and root JSON entries are merged
        last so literal-text keys take precedence on collision.

        Parameters
        ----------
        locale : str
            Locale code whose translation sources must be read.

        Returns
        -------
        orionis.localization.types.TranslationMap
            Flat mapping of translation key to translated text. An
            empty mapping is returned when no source exists.

        Raises
        ------
        orionis.localization.InvalidLocaleException
            If the locale code is malformed or contains path components.
        orionis.localization.TranslationException
            If a source resolves outside the configured language directory.
        orionis.localization.TranslationSyntaxException
            If a translation file is not UTF-8 encoded, contains
            invalid JSON, or its root element is not an object.
        """
        locale = validate_locale(locale)
        translations: TranslationMap = {}

        # Merge grouped files flattened as "group.nested.key" entries.
        directory = self.__resolveSource(self._path / locale)
        if directory.is_dir():
            for file in sorted(directory.glob("*.json")):
                self.__flatten(self.__readFile(file), file.stem, translations)

        # Merge the root JSON file whose keys are literal source texts.
        root_file = self.__resolveSource(self._path / f"{locale}.json")
        if root_file.is_file():
            for key, value in self.__readFile(root_file).items():
                if isinstance(value, dict):
                    self.__flatten(value, key, translations)
                else:
                    translations[key] = value if isinstance(value, str) else str(value)

        return translations

    def availableLocales(self) -> tuple[str, ...]:
        """
        Discover every locale with at least one translation source.

        Returns
        -------
        tuple[str, ``...``]
            Sorted valid locale codes from sources resolving within the
            language directory. External links are omitted.
        """
        if not self._path.is_dir():
            return ()

        # Collect locales from both root JSON files and grouped folders.
        locales: set[str] = set()
        for entry in self._path.iterdir():
            if not entry.resolve().is_relative_to(self._path):
                continue
            is_root_file = entry.is_file() and entry.suffix == ".json"
            locale = entry.stem if is_root_file else entry.name
            try:
                validate_locale(locale)
            except InvalidLocaleException:
                continue
            if is_root_file or (
                entry.is_dir()
                and any(
                    file.resolve().is_relative_to(self._path) and file.is_file()
                    for file in entry.glob("*.json")
                )
            ):
                locales.add(locale)

        return tuple(sorted(locales))

    def __readFile(self, file: Path) -> dict[str, object]:
        """
        Decode a single translation file with msgspec.

        Parameters
        ----------
        file : pathlib.Path
            Absolute path of the JSON file to decode.

        Returns
        -------
        dict[str, object]
            Decoded JSON object.

        Raises
        ------
        orionis.localization.TranslationFileNotFoundException
            If the file does not exist.
        orionis.localization.TranslationSyntaxException
            If the payload is not UTF-8 encoded, is invalid JSON, or
            its root element is not an object.
        """
        file = self.__resolveSource(file)
        # Guard against missing entries and non-file sources.
        if not file.is_file():
            error_msg = f"Translation file not found: {file}"
            raise TranslationFileNotFoundException(error_msg)

        # Decode the raw UTF-8 bytes with msgspec.
        try:
            decoded = msgspec.json.decode(file.read_bytes())
        except FileNotFoundError as exc:
            error_msg = f"Translation file not found: {file}"
            raise TranslationFileNotFoundException(error_msg) from exc
        except (msgspec.DecodeError, UnicodeDecodeError) as exc:
            error_msg = f"Invalid JSON in translation file: {file} ({exc})"
            raise TranslationSyntaxException(error_msg) from exc

        # The root element of every translation file must be an object.
        if not isinstance(decoded, dict):
            error_msg = f"Translation file must contain a JSON object: {file}"
            raise TranslationSyntaxException(error_msg)

        return decoded

    def __resolveSource(self, source: Path) -> Path:
        """Resolve a source inside the configured language directory.

        Parameters
        ----------
        source : pathlib.Path
            Candidate directory or JSON file, including symbolic links.

        Returns
        -------
        pathlib.Path
            Resolved source within the configured directory.

        Raises
        ------
        orionis.localization.TranslationException
            If the source resolves outside the language directory.
        """
        resolved = source.resolve()
        if not resolved.is_relative_to(self._path):
            error_msg = (
                f"Translation source is outside the language directory: {source}"
            )
            raise TranslationException(error_msg)
        return resolved

    def __flatten(
        self,
        payload: dict[str, object],
        prefix: str,
        target: TranslationMap,
    ) -> None:
        """
        Flatten a nested translation object into dot-notated keys.

        Parameters
        ----------
        payload : dict[str, object]
            Nested translation object to flatten.
        prefix : str
            Dot-notated prefix accumulated so far.
        target : orionis.localization.types.TranslationMap
            Mutable mapping receiving the flattened entries.

        Returns
        -------
        None
            No return value.
        """
        for key, value in payload.items():
            compound = f"{prefix}.{key}"
            if isinstance(value, dict):
                self.__flatten(value, compound, target)
            else:
                target[compound] = value if isinstance(value, str) else str(value)
