from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

class ICollection(ABC):

    @abstractmethod
    def take(
        self,
        number: int,
    ) -> ICollection:
        """
        Take a specific number of items from the collection.

        Parameters
        ----------
        number : int
            The number of items to take. If negative, takes from the end.

        Returns
        -------
        Collection
            A new Collection containing the specified number of items.
        """

    @abstractmethod
    def first(
        self,
        callback: Callable | None = None,
    ) -> object:
        """
        Return the first item in the collection, optionally filtered by a callback.

        Parameters
        ----------
        callback : Callable | None, optional
            A function to filter items before returning the first one,
            by default None.

        Returns
        -------
        object
            The first item in the filtered collection, or None if empty.
        """

    @abstractmethod
    def last(
        self,
        callback: Callable | None = None,
    ) -> object:
        """
        Return the last item in the collection, optionally filtered by a callback.

        Parameters
        ----------
        callback : Callable | None, optional
            Function to filter items before returning the last one, by default None.

        Returns
        -------
        object
            The last item in the filtered collection, or raises IndexError if empty.
        """

    @abstractmethod
    def all(self) -> list[Any]:
        """
        Return all items in the collection.

        Returns
        -------
        list of Any
            All items contained in the collection.
        """

    @abstractmethod
    def avg(
        self,
        key: str | None = None,
    ) -> float:
        """
        Compute the average of the items.

        Parameters
        ----------
        key : str | None, optional
            The key to use for calculating the average of values.
            If None, use all items.

        Returns
        -------
        float
            The average value of the items. Returns 0 if calculation fails.
        """

    @abstractmethod
    def max(
        self,
        key: str | None = None,
    ) -> object:
        """
        Return the maximum value from the items.

        Parameters
        ----------
        key : str | None, optional
            The key to use for finding the maximum value. If None, use all items.

        Returns
        -------
        object
            The maximum value found, or 0 if not found or on error.
        """

    @abstractmethod
    def min(
        self,
        key: str | None = None,
    ) -> object:
        """
        Return the minimum value from the items.

        Parameters
        ----------
        key : str | None, optional
            The key to use for finding the minimum value. If None, use all items.

        Returns
        -------
        object
            The minimum value found, or 0 if not found or on error.
        """

    @abstractmethod
    def chunk(
        self,
        size: int,
    ) -> ICollection:
        """
        Divide the collection into smaller collections of a specified size.

        Parameters
        ----------
        size : int
            Number of items in each chunk.

        Returns
        -------
        Collection
            A new Collection containing sub-collections (chunks) of the specified size.
        """

    @abstractmethod
    def collapse(self) -> ICollection:
        """
        Collapse the collection of arrays into a single, flat collection.

        Returns
        -------
        Collection
            A new Collection containing all items from nested arrays, flattened.
        """

    @abstractmethod
    def contains(
        self,
        key: str | Callable,
        value: object = None,
    ) -> bool:
        """
        Check if the collection contains a given item.

        Parameters
        ----------
        key : str or Callable
            The key to check for, or a callback function.
        value : Any, optional
            The value to match when key is a string, by default None.

        Returns
        -------
        bool
            True if the item is found, False otherwise.
        """

    @abstractmethod
    def count(self) -> int:
        """
        Return the number of items in the collection.

        Returns
        -------
        int
            The number of items in the collection.
        """

    @abstractmethod
    def diff(
        self,
        items: list[Any] | ICollection,
    ) -> ICollection:
        """
        Return items not present in the given collection.

        Parameters
        ----------
        items : list[Any] | Collection
            The items to compare against.

        Returns
        -------
        Collection
            A new collection containing items not found in the provided collection.
        """

    @abstractmethod
    def each(
        self,
        callback: Callable,
    ) -> ICollection:
        """
        Iterate over items and apply the callback to each.

        Parameters
        ----------
        callback : Callable
            The callback function to apply to each item.

        Returns
        -------
        Collection
            The current collection instance.
        """

    @abstractmethod
    def every(
        self,
        callback: Callable,
    ) -> bool:
        """
        Determine whether all items satisfy the given callback condition.

        Parameters
        ----------
        callback : Callable
            The callback function to test each item.

        Returns
        -------
        bool
            True if all items pass the test, otherwise False.
        """

    @abstractmethod
    def filter(
        self,
        callback: Callable,
    ) -> ICollection:
        """
        Filter items in the collection using a callback.

        Parameters
        ----------
        callback : Callable
            Function to determine if an item should be included.

        Returns
        -------
        Collection
            A new Collection containing items for which the callback returns True.
        """

    @abstractmethod
    def flatten(self) -> ICollection:
        """
        Flatten the collection into a single dimension.

        Returns
        -------
        Collection
            A new Collection containing all items, flattened to a single dimension.
        """

    @abstractmethod
    def forget(
        self,
        *keys: int | str,
    ) -> ICollection:
        """
        Remove items from the collection by their keys.

        Parameters
        ----------
        *keys : Any
            The keys of the items to remove from the collection.

        Returns
        -------
        Collection
            The current collection instance after removal.
        """

    @abstractmethod
    def forPage(
        self,
        page: int,
        number: int,
    ) -> ICollection:
        """
        Slice the collection for pagination.

        Parameters
        ----------
        page : int
            The page number to retrieve.
        number : int
            The number of items per page.

        Returns
        -------
        Collection
            A new Collection containing the paginated items.
        """

    @abstractmethod
    def get(
        self,
        key: int | str,
        default: object = None,
    ) -> object:
        """
        Retrieve an item from the collection by key.

        Parameters
        ----------
        key : Any
            The key or index to retrieve from the collection.
        default : Any, optional
            The value to return if the key is not found. Defaults to None.

        Returns
        -------
        Any
            The item at the specified key, or the default value if not found.
        """

    @abstractmethod
    def implode(
        self,
        glue: str = ",",
        key: str | None = None,
    ) -> str:
        """
        Join all items in the collection into a single string.

        Parameters
        ----------
        glue : str, optional
            String used to join the items. Default is ",".
        key : str | None, optional
            Key to extract from each item before joining. Default is None.

        Returns
        -------
        str
            A string with all items joined by the specified glue.
        """

    @abstractmethod
    def isEmpty(self) -> bool:
        """
        Check if the collection is empty.

        Returns
        -------
        bool
            True if the collection is empty, otherwise False.
        """

    @abstractmethod
    def map(
        self,
        callback: Callable,
    ) -> ICollection:
        """
        Apply a function to each item in the collection.

        Parameters
        ----------
        callback : Callable
            Function to apply to each item.

        Returns
        -------
        Collection
            A new Collection containing the mapped items.
        """

    @abstractmethod
    def mapInto(
        self,
        cls: type,
        method: str | None = None,
        **kwargs: object,
    ) -> ICollection:
        """
        Map items into instances of the given class.

        Parameters
        ----------
        cls : type
            The class to map items into.
        method : str | None, optional
            The method to call on the class, by default None.
        **kwargs : Any
            Additional keyword arguments to pass to the constructor or method.

        Returns
        -------
        Collection
            A new collection with the mapped instances.
        """

    @abstractmethod
    def merge(
        self,
        items: list[Any] | ICollection,
    ) -> ICollection:
        """
        Merge the collection with the given items.

        Parameters
        ----------
        items : list[Any] | Collection
            The items to merge into the collection.

        Returns
        -------
        Collection
            The current collection instance with merged items.

        Raises
        ------
        TypeError
            If items cannot be merged due to incompatible types.
        """

    @abstractmethod
    def pluck(
        self,
        value: str,
        key: str | None = None,
    ) -> ICollection:
        """
        Extract values for a given key from all items.

        Parameters
        ----------
        value : str
            The key to extract from each item.
        key : str | None, optional
            The key to use as the result key, by default None.

        Returns
        -------
        Collection
            A new collection containing the plucked values.
        """

    @abstractmethod
    def pop(self) -> object:
        """
        Remove and return the last item from the collection.

        Returns
        -------
        Any
            The last item from the collection.
        """

    @abstractmethod
    def prepend(
        self,
        value: object,
    ) -> ICollection:
        """
        Prepend an item to the beginning of the collection.

        Parameters
        ----------
        value : Any
            The value to prepend to the collection.

        Returns
        -------
        Collection
            The current collection instance with the new item prepended.
        """

    @abstractmethod
    def pull(
        self,
        key: int | str,
    ) -> object:
        """
        Remove and return an item from the collection by key.

        Parameters
        ----------
        key : Any
            The key of the item to remove.

        Returns
        -------
        Any
            The removed item, or None if not found.
        """

    @abstractmethod
    def push(
        self,
        value: object,
    ) -> ICollection:
        """
        Add an item to the end of the collection.

        Parameters
        ----------
        value : Any
            The value to add to the collection.

        Returns
        -------
        Collection
            The current collection instance with the new item appended.
        """

    @abstractmethod
    def put(
        self,
        key: int | str,
        value: object,
    ) -> ICollection:
        """
        Insert or update an item in the collection at the specified key.

        Parameters
        ----------
        key : Any
            The key or index at which to set the value.
        value : Any
            The value to assign at the specified key.

        Returns
        -------
        Collection
            The current collection instance with the updated item.
        """

    @abstractmethod
    def random(
        self,
        count: int | None = None,
    ) -> object | ICollection | None:
        """
        Return one or more random items from the collection.

        Parameters
        ----------
        count : int | None, optional
            The number of items to return. If None, returns a single item.

        Returns
        -------
        Any | Collection | None
            A single random item if count is None, a Collection if count is given,
            or None if the collection is empty.

        Raises
        ------
        ValueError
            If count is greater than the number of items in the collection.
        """

    @abstractmethod
    def reduce(
        self,
        callback: Callable,
        initial: object = 0,
    ) -> object:
        """
        Reduce the collection to a single value using a callback.

        Parameters
        ----------
        callback : Callable
            The function to apply cumulatively to the items.
        initial : Any, optional
            The initial value to start the reduction, by default 0.

        Returns
        -------
        Any
            The reduced value after applying the callback.
        """

    @abstractmethod
    def reject(
        self,
        callback: Callable,
    ) -> ICollection:
        """
        Reject items that pass a given truth test.

        Parameters
        ----------
        callback : Callable
            The callback function to test items.

        Returns
        -------
        Collection
            The current collection instance with items not passing the test.
        """

    @abstractmethod
    def reverse(self) -> ICollection:
        """
        Reverse the order of items in the collection.

        Returns
        -------
        Collection
            The current collection instance with items in reversed order.
        """

    @abstractmethod
    def serialize(self) -> list[Any]:
        """
        Serialize the collection items as a list.

        Returns
        -------
        list of Any
            The serialized items in the collection.
        """

    @abstractmethod
    def shift(self) -> object:
        """
        Remove and return the first item from the collection.

        Returns
        -------
        Any
            The first item from the collection, or None if the collection is empty.
        """

    @abstractmethod
    def sort(
        self,
        key: str | None = None,
    ) -> ICollection:
        """
        Sort the items in the collection.

        Parameters
        ----------
        key : str | None, optional
            The key to sort by. If None, sort items directly.

        Returns
        -------
        Collection
            The current collection instance with sorted items.
        """

    @abstractmethod
    def sum(
        self,
        key: str | None = None,
    ) -> float:
        """
        Compute the sum of the given values.

        Parameters
        ----------
        key : str | None, optional
            The key to sum by. If None, sum all items.

        Returns
        -------
        float
            The sum of the values. Returns 0 if calculation fails.
        """

    @abstractmethod
    def toJson(
        self,
        **kwargs: object,
    ) -> str:
        """
        Return the collection items as a JSON string.

        Parameters
        ----------
        **kwargs : Any
            Additional arguments to pass to json.dumps.

        Returns
        -------
        str
            JSON representation of the serialized collection items.
        """

    @abstractmethod
    def groupBy(
        self,
        key: str,
    ) -> ICollection:
        """
        Group items in the collection by a specified key.

        Parameters
        ----------
        key : str
            The key to group items by.

        Returns
        -------
        Collection
            A new Collection instance containing a dictionary where each key is a
            unique value from the specified key, and each value is a list of items
            sharing that key.
        """

    @abstractmethod
    def transform(
        self,
        callback: Callable,
    ) -> ICollection:
        """
        Transform each item in the collection using a callback.

        Parameters
        ----------
        callback : Callable
            The callback function to transform items.

        Returns
        -------
        Collection
            The current collection instance with transformed items.
        """

    @abstractmethod
    def unique(
        self,
        key: str | None = None,
    ) -> ICollection:
        """
        Return unique items from the collection.

        Parameters
        ----------
        key : str | None, optional
            The key to use for uniqueness comparison. If None, use items directly.

        Returns
        -------
        Collection
            A new Collection containing only unique items.
        """

    @abstractmethod
    def where(
        self,
        key: str,
        *args: object,
    ) -> ICollection:
        """
        Filter items by a given key-value pair or comparison.

        Parameters
        ----------
        key : str
            The key to filter by.
        *args : Any
            The operator and value, or just the value.

        Returns
        -------
        Collection
            A new Collection instance containing filtered items.
        """

    @abstractmethod
    def whereIn(
        self,
        key: str,
        values: list[Any] | ICollection,
    ) -> ICollection:
        """
        Filter items where a given key's value is in a list of values.

        Parameters
        ----------
        key : str
            The key to filter by.
        values : list[Any] | Collection
            The list of values to check against.

        Returns
        -------
        Collection
            A new collection containing items where the key's value is in values.
        """

    @abstractmethod
    def whereNotIn(
        self,
        key: str,
        values: list[Any] | ICollection,
    ) -> ICollection:
        """
        Filter items where a given key's value is not in a list of values.

        Parameters
        ----------
        key : str
            The key to filter by.
        values : list[Any] | Collection
            The list of values to check against.

        Returns
        -------
        Collection
            A new Collection containing items where the key's value is not in values.
        """

    @abstractmethod
    def zip(
        self,
        items: list[Any] | ICollection,
    ) -> ICollection:
        """
        Zip the collection with the given items by index.

        Parameters
        ----------
        items : list[Any] | Collection
            The items to zip with.

        Returns
        -------
        Collection
            A new Collection containing pairs of items from both collections.

        Raises
        ------
        ValueError
            If the 'items' parameter is not a list or Collection.
        """

    @abstractmethod
    def setAppends(
        self,
        appends: list[str],
    ) -> ICollection:
        """
        Set the attributes to append to the Collection.

        Parameters
        ----------
        appends : list[str]
            The attributes to append.

        Returns
        -------
        Collection
            The current collection instance.
        """
