from dataclasses import dataclass
from email.errors import NonASCIILocalPartDefect
from email.headerregistry import Address as HeaderAddress, HeaderRegistry
from typing import TYPE_CHECKING, cast
from orionis.mail.exceptions import MailCompositionException
from orionis.mail.functions import header_value

if TYPE_CHECKING:
    from email.headerregistry import AddressHeader
    from orionis.mail.types import Recipients

_HEADERS = HeaderRegistry()

@dataclass(frozen=True, slots=True)
class Address:
    """
    Represent one mailbox with an optional Unicode display name.

    Parameters
    ----------
    address : str
        Single addr-spec, never a comma-separated list or a display-name form.
    name : str | None
        Optional visible name.
    """

    address: str  # NOSONAR
    name: str | None = None

    def __post_init__(self) -> None:
        """
        Parse a mailbox using the standard email header parser.

        Returns
        -------
        None
            Normalize only the domain and preserve local-part case.

        Raises
        ------
        MailCompositionException
            If the mailbox is invalid or contains ambiguous header syntax.
        """
        value = header_value(self.address, "Address")  # NOSONAR
        if self.name is not None:
            header_value(self.name, "Address name")

        try:
            parsed = _HEADERS("To", value)

            # A non-ASCII local part is valid for SMTPUTF8 and is the only
            # defect tolerated while parsing a mailbox.
            invalid = any(
                not isinstance(defect, NonASCIILocalPartDefect)
                for defect in parsed.defects
            )
            address_header = cast("AddressHeader", parsed)
            if (
                invalid
                or len(address_header.addresses) != 1
                or any(
                    group.display_name is not None for group in address_header.groups
                )
            ):
                error_msg = "Expected exactly one valid mailbox address."
                raise MailCompositionException(error_msg)

            mailbox = address_header.addresses[0]
            if not mailbox.username or not mailbox.domain or mailbox.display_name:
                error_msg = "Provide an addr-spec and a separate display name."
                raise MailCompositionException(error_msg)

            domain = mailbox.domain.encode("idna").decode("ascii").lower()
            normalized = HeaderAddress(username=mailbox.username, domain=domain)
        except (ValueError, IndexError) as exc:
            error_msg = "Invalid mailbox address."
            raise MailCompositionException(error_msg) from exc

        object.__setattr__(self, "address", normalized.addr_spec)

    def asHeader(self) -> HeaderAddress:
        """
        Build a standard immutable address header value.

        Returns
        -------
        HeaderAddress
            The mailbox with its optional display name.
        """
        parsed = cast("AddressHeader", _HEADERS("To", self.address))
        mailbox = parsed.addresses[0]
        return HeaderAddress(
            display_name=self.name or "",
            username=mailbox.username,
            domain=mailbox.domain,
        )

def one_address(value: str | Address, name: str | None = None) -> Address:
    """
    Normalize exactly one mailbox and reject ambiguous names.

    Parameters
    ----------
    value : str | Address
        One mailbox.
    name : str | None
        Display name, valid only with a string mailbox.

    Returns
    -------
    Address
        Validated immutable address.

    Raises
    ------
    MailCompositionException
        If the value is not one address or a name is supplied twice.
    """
    if isinstance(value, str):
        return Address(value, name)
    if isinstance(value, Address) and name is None:
        return value
    error_msg = "Use a string with an optional name, or one Address without name."
    raise MailCompositionException(error_msg)

def addresses(value: Recipients, name: str | None = None) -> tuple[Address, ...]:
    """
    Normalize and stably deduplicate a recipient declaration.

    Parameters
    ----------
    value : Recipients
        Single mailbox or a list/tuple of mailboxes.
    name : str | None
        Optional name for a single string mailbox only.

    Returns
    -------
    tuple[Address, ...]
        Mailboxes in first-declaration order.

    Raises
    ------
    MailCompositionException
        If a collection is combined with a display name or has invalid entries.
    """
    if isinstance(value, (str, Address)):
        return (one_address(value, name),)
    if not isinstance(value, (list, tuple)) or name is not None:
        error_msg = "Recipients require a mailbox or a list/tuple without name."
        raise MailCompositionException(error_msg)

    # Deduplicate on the normalized addr-spec while keeping declaration order.
    unique: dict[str, Address] = {}
    for item in value:
        address = one_address(item)
        unique.setdefault(address.address, address)
    return tuple(unique.values())
