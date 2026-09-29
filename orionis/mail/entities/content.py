from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast
from orionis.mail.exceptions import MailCompositionException
from orionis.mail.functions import freeze_owned

@dataclass(frozen=True, slots=True, kw_only=True)
class Content:
    """
    Declare literal bodies or views with one explicit isolated context.

    Parameters
    ----------
    view : str | None
        HTML template identifier, mutually exclusive with html.
    html : str | None
        Literal HTML, never interpreted as a template.
    text : str | None
        Literal plain text, mutually exclusive with text_view.
    text_view : str | None
        Plain-text template identifier.
    data : Mapping[str, object] | None
        Context shared by both views, with copied read-only containers.
    """

    view: str | None = None
    html: str | None = None
    text: str | None = None
    text_view: str | None = None
    data: Mapping[str, object] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """
        Validate body declarations and snapshot their context.

        Returns
        -------
        None
            Protect owned containers while preserving opaque object identity.

        Raises
        ------
        MailCompositionException
            If bodies conflict, are absent, or have invalid types or context.
        """
        bodies = (self.view, self.html, self.text, self.text_view)
        if all(body is None for body in bodies):
            error_msg = "Declare at least one mail body; an empty string is valid."
            raise MailCompositionException(error_msg)

        if (self.view is not None and self.html is not None) or (
            self.text is not None and self.text_view is not None
        ):
            error_msg = "Declare either a view or a literal for each body type."
            raise MailCompositionException(error_msg)

        if any(body is not None and not isinstance(body, str) for body in bodies):
            error_msg = "Mail bodies and view identifiers must be strings."
            raise MailCompositionException(error_msg)

        # An empty literal is a declared body, but an empty template name
        # could never be resolved by the view engine.
        if self.view == "" or self.text_view == "":
            error_msg = "Mail view identifiers must not be empty."
            raise MailCompositionException(error_msg)

        data = {} if self.data is None else self.data
        if not isinstance(data, Mapping) or any(
            not isinstance(key, str) for key in data
        ):
            error_msg = "Mail view data must be a mapping with string keys."
            raise MailCompositionException(error_msg)

        snapshot = cast("Mapping[str, object]", freeze_owned(data))
        object.__setattr__(self, "data", snapshot)
