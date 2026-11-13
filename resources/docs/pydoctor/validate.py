"""Reject incomplete API pages and broken local links before publication."""

from __future__ import annotations
import json
import posixpath
import sys
from functools import cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class _Page(HTMLParser):
    """Collect navigation targets and documentation diagnostics from one page."""

    def __init__(self) -> None:
        """Initialize the HTML parser and per-page validation state.

        Returns
        -------
        None
            Prepare anchor, link and documentation-field collections.
        """
        super().__init__(convert_charrefs=True)
        self.identifiers: set[str] = set()
        self.links: set[str] = set()
        self.problems: set[str] = set()
        self.field_tables = 0

    def handleStarttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Read anchors, local references and visible documentation errors.

        Parameters
        ----------
        tag : str
            HTML element name.
        attrs : list[tuple[str, str or None]]
            Attributes supplied by the standard HTML parser.

        Returns
        -------
        None
            Record identifiers, links and incomplete documentation markers.
        """
        attributes = dict(attrs)
        identifier = attributes.get("id")
        if identifier:
            self.identifiers.add(identifier)
        if tag == "a":
            name = attributes.get("name")
            if name:
                self.identifiers.add(name)
            href = attributes.get("href")
            if href:
                self.links.add(href)
        classes = set((attributes.get("class") or "").split())
        self.problems.update(
            classes
            & {
                "undocumented",
                "rst-system-message",
                "rst-problematic",
            },
        )
        self.field_tables += "fieldTable" in classes

    handle_starttag = handleStarttag


@cache
def _local_target(directory: str, href: str) -> tuple[str, str] | None:
    """Normalize a local URL without repeated filesystem operations.

    Parameters
    ----------
    directory : str
        Relative directory containing the referring page.
    href : str
        HTML reference to classify and decode.

    Returns
    -------
    tuple[str, str] or None
        Relative path and fragment, or None for an external reference.
    """
    url = urlsplit(href)
    if url.scheme or url.netloc:
        return None
    path = unquote(url.path)
    if not path:
        return "", unquote(url.fragment)
    if path.startswith("/"):
        target = posixpath.normpath(path.lstrip("/"))
    else:
        target = posixpath.normpath(posixpath.join(directory, path))
    if path.endswith("/"):
        target = posixpath.join(target, "index.html")
    return target, unquote(url.fragment)


def validate_site(directory: Path) -> dict[str, object]:  # NOSONAR
    """Inspect the complete generated site before replacing published files.

    Parameters
    ----------
    directory : pathlib.Path
        Root of a completed pydoctor HTML build.

    Returns
    -------
    dict[str, object]
        Page and API counts, plus any broken links or incomplete fields.
    """
    files = {
        path.relative_to(directory).as_posix(): path
        for path in directory.rglob("*")
        if path.is_file()
    }
    pages = {}
    errors = []
    for name, path in files.items():
        if path.suffix != ".html":
            continue
        page = _Page()
        page.feed(path.read_text(encoding="utf-8"))
        pages[name] = page
        errors.extend(f"{name}: {problem}" for problem in sorted(page.problems))
    if not pages:
        errors.append("The site contains no HTML pages.")
    for name, page in pages.items():
        for href in sorted(page.links):
            local = _local_target(posixpath.dirname(name), href)
            if local is None:
                continue
            target, fragment = local
            target = target or name
            if target not in files:
                errors.append(f"{name}: missing local file {href}")
            elif (
                fragment
                and target in pages
                and fragment not in pages[target].identifiers
            ):
                errors.append(f"{name}: missing local anchor {href}")
    inventory = pages.get("all-documents.html")
    return {
        "html_pages": len(pages),
        "api_objects": sum(
            identifier == "orionis" or identifier.startswith("orionis.")
            for identifier in inventory.identifiers
        )
        if inventory
        else 0,
        "numpy_field_tables": sum(page.field_tables for page in pages.values()),
        "errors": errors,
    }


def main() -> int:
    """Validate a generated site passed on the command line.

    Returns
    -------
    int
        Zero for a complete site, or one when any validation check fails.
    """
    report = validate_site(Path(sys.argv[1]))
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    return int(bool(report["errors"]))


if __name__ == "__main__":
    sys.exit(main())
