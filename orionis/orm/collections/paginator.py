from __future__ import annotations
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orionis.support.types.collection import Collection

class Paginator:
    """
    Length-aware page of query results.

    Wraps a :class:`Collection` of items together with the pagination
    metadata required to render page controls: total row count, current
    page, page size, and derived navigation flags.
    """

    __slots__ = ("_items", "_page", "_per_page", "_total")

    def __init__(
        self,
        items: Collection,
        total: int,
        page: int,
        per_page: int,
    ) -> None:
        """
        Initialize the paginator with its items and metadata.

        Parameters
        ----------
        items : Collection
            Items for the current page.
        total : int
            Total number of rows across all pages.
        page : int
            Current page number, starting at 1.
        per_page : int
            Number of items per page.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the page or page size are not positive integers.
        """
        # Validate pagination inputs to keep derived values consistent.
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            error_msg = "Page number must be a positive integer."
            raise ValueError(error_msg)
        if not isinstance(per_page, int) or isinstance(per_page, bool) or per_page < 1:
            error_msg = "Items per page must be a positive integer."
            raise ValueError(error_msg)

        self._items = items
        self._total = max(0, int(total))
        self._page = page
        self._per_page = per_page

    # ── Data access ─────────────────────────────────────────────────────────

    @property
    def items(self) -> Collection:
        """
        Return the items for the current page.

        Returns
        -------
        Collection
            Items of the current page.
        """
        return self._items

    @property
    def total(self) -> int:
        """
        Return the total number of rows across all pages.

        Returns
        -------
        int
            Total row count.
        """
        return self._total

    @property
    def page(self) -> int:
        """
        Return the current page number.

        Returns
        -------
        int
            Current page, starting at 1.
        """
        return self._page

    @property
    def perPage(self) -> int:
        """
        Return the configured page size.

        Returns
        -------
        int
            Number of items per page.
        """
        return self._per_page

    @property
    def lastPage(self) -> int:
        """
        Return the number of the last available page.

        Returns
        -------
        int
            Last page number, never lower than 1.
        """
        return max(1, (self._total + self._per_page - 1) // self._per_page)

    @property
    def hasNext(self) -> bool:
        """
        Report whether a page exists after the current one.

        Returns
        -------
        bool
            ``True`` when the current page is not the last.
        """
        return self._page * self._per_page < self._total

    @property
    def hasPrevious(self) -> bool:
        """
        Report whether a page exists before the current one.

        Returns
        -------
        bool
            ``True`` when the current page is not the first.
        """
        return self._page > 1

    # ── Serialization ───────────────────────────────────────────────────────

    def toDict(self) -> dict[str, Any]:
        """
        Serialize the page and its metadata into a dictionary.

        Returns
        -------
        dict
            Dictionary with items and pagination metadata.
        """
        return {
            "items": self._items.serialize(),
            "total": self._total,
            "page": self._page,
            "perPage": self._per_page,
            "lastPage": self.lastPage,
            "hasNext": self.hasNext,
            "hasPrevious": self.hasPrevious,
        }

    def toJson(self, **kwargs: Any) -> str:  # noqa: ANN401
        """
        Serialize the page and its metadata into a JSON string.

        Parameters
        ----------
        **kwargs : Any
            Additional keyword arguments forwarded to ``json.dumps``.

        Returns
        -------
        str
            JSON representation of the page.
        """
        kwargs.setdefault("default", str)
        return json.dumps(self.toDict(), **kwargs)

    def __len__(self) -> int:
        """
        Return the number of items in the current page.

        Returns
        -------
        int
            Item count of the current page.
        """
        return len(self._items)

    def __repr__(self) -> str:
        """
        Return a concise developer representation of the paginator.

        Returns
        -------
        str
            Representation including page, page size, and total.
        """
        return (
            f"<Paginator page={self._page} perPage={self._per_page} "
            f"total={self._total}>"
        )
