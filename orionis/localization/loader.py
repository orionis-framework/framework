from __future__ import annotations
from typing import TYPE_CHECKING
import msgspec
from orionis.localization.contracts.loader import ITranslationLoader
from orionis.localization.exceptions import (
    TranslationFileNotFoundException,
    TranslationSyntaxException,
)

if TYPE_CHECKING:
    from pathlib import Path
    from orionis.localization.types import TranslationMap

class TranslationLoader(ITranslationLoader):
    """
    Load translation sources from the configured language path.

    The loader reads root JSON files (``{path}/{locale}.json``) whose
    keys are the literal source texts, and grouped JSON files
    (``{path}/{locale}/{group}.json``) flattened with dot notation such
    as ``validation.required``. Decoding is performed with ``msgspec``
    for maximum throughput. The loader holds no cache: that concern
    belongs to the repository.

    Notes
    -----
    Translation files are read as raw bytes and decoded as UTF-8 JSON.
    A source stored in any other encoding raises
    :class:`TranslationSyntaxException`, like any other unusable
    payload.
    """

    __slots__ = ("_path",)

    def __init__(self, path: Path) -> None:
        """
        Initialize the loader with the language directory.

        Parameters
        ----------
        path : Path
            Absolute directory containing the translation sources.

        Returns
        -------
        None
        """
        self._path = path

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
        TranslationMap
            Flat mapping of translation key to translated text. An
            empty mapping is returned when no source exists.

        Raises
        ------
        TranslationSyntaxException
            If a translation file is not UTF-8 encoded, contains
            invalid JSON, or its root element is not an object.
        """
        translations: TranslationMap = {}

        # Merge grouped files flattened as "group.nested.key" entries.
        directory = self._path / locale
        if directory.is_dir():
            for file in sorted(directory.glob("*.json")):
                self.__flatten(self.__readFile(file), file.stem, translations)

        # Merge the root JSON file whose keys are literal source texts.
        root_file = self._path / f"{locale}.json"
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
        tuple[str, ...]
            Sorted locale codes discovered from root JSON files and
            grouped directories inside the language path.
        """
        if not self._path.is_dir():
            return ()

        # Collect locales from both root JSON files and grouped folders.
        locales: set[str] = set()
        for entry in self._path.iterdir():
            if entry.is_file() and entry.suffix == ".json":
                locales.add(entry.stem)
            elif entry.is_dir() and any(entry.glob("*.json")):
                locales.add(entry.name)

        return tuple(sorted(locales))

    def __readFile(self, file: Path) -> dict[str, object]:
        """
        Decode a single translation file with msgspec.

        Parameters
        ----------
        file : Path
            Absolute path of the JSON file to decode.

        Returns
        -------
        dict[str, object]
            Decoded JSON object.

        Raises
        ------
        TranslationFileNotFoundException
            If the file does not exist.
        TranslationSyntaxException
            If the payload is not UTF-8 encoded, is invalid JSON, or
            its root element is not an object.
        """
        # Guard against files removed between discovery and read.
        if not file.is_file():
            error_msg = f"Translation file not found: {file}"
            raise TranslationFileNotFoundException(error_msg)

        # Decode the raw UTF-8 bytes with msgspec for maximum throughput.
        try:
            decoded = msgspec.json.decode(file.read_bytes())
        except (msgspec.DecodeError, UnicodeDecodeError) as exc:
            error_msg = f"Invalid JSON in translation file: {file} ({exc})"
            raise TranslationSyntaxException(error_msg) from exc

        # The root element of every translation file must be an object.
        if not isinstance(decoded, dict):
            error_msg = f"Translation file must contain a JSON object: {file}"
            raise TranslationSyntaxException(error_msg)

        return decoded

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
        target : TranslationMap
            Mutable mapping receiving the flattened entries.

        Returns
        -------
        None
        """
        for key, value in payload.items():
            compound = f"{prefix}.{key}"
            if isinstance(value, dict):
                self.__flatten(value, compound, target)
            else:
                target[compound] = value if isinstance(value, str) else str(value)
