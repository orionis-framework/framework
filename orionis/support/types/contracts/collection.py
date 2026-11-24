# ruff: noqa: TC003
# Keep public callback annotations available for runtime contract inspection.
"""Define the contract for collection implementations."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Self, overload


class ICollection[T = Any](ABC):
    """Define the contract for collection implementations."""

    @abstractmethod
    def take(
        self: Self,
        number: int,
    ) -> ICollection[T]:
        """
        Take a specific number of items from the collection.

        Parameters
        ----------
        number : int
            The number of items to take. If negative, takes from the end.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing the specified number of items.
        """

    @abstractmethod
    def first(
        self: Self,
        callback: Callable[[T], object] | None = None,
    ) -> T | None:
        """
        Return the first item in the collection, optionally filtered by a callback.

        Parameters
        ----------
        callback : collections.abc.Callable | None, optional
            A function to filter items before returning the first one,
            by default None.

        Returns
        -------
        object
            The first item in the filtered collection, or None if empty.
        """

    @abstractmethod
    def last(
        self: Self,
        callback: Callable[[T], object] | None = None,
    ) -> T | None:
        """
        Return the last item in the collection, optionally filtered by a callback.

        Parameters
        ----------
        callback : collections.abc.Callable | None, optional
            Function to filter items before returning the last one, by default None.

        Returns
        -------
        object
            The last item in the filtered collection, or None if empty.
        """

    @abstractmethod
    def all(self: Self) -> list[T] | dict[Any, Any]:
        """
        Return all items in the collection.

        Returns
        -------
        list[typing.Any] | dict[typing.Any, typing.Any]
            All items contained in the collection.
        """

    @abstractmethod
    def avg(
        self: Self,
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
        self: Self,
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
        self: Self,
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
    def chunk[C: ICollection](
        self: C,
        size: int,
    ) -> ICollection[C]:
        """
        Divide the collection into smaller collections of a specified size.

        Parameters
        ----------
        size : int
            Number of items in each chunk.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing sub-collections (chunks) of the specified size.
        """

    @abstractmethod
    def collapse(self: Self) -> ICollection[Any]:
        """
        Collapse the collection of arrays into a single, flat collection.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing all items from nested arrays, flattened.
        """

    @abstractmethod
    def contains(
        self: Self,
        key: str | Callable[[T], object],
        value: object | None = None,
    ) -> bool:
        """
        Check if the collection contains a given item.

        Parameters
        ----------
        key : str or collections.abc.Callable
            The key to check for, or a callback function.
        value : typing.Any, optional
            The value to match when key is a string, by default None.

        Returns
        -------
        bool
            True if the item is found, False otherwise.
        """

    @abstractmethod
    def count(self: Self) -> int:
        """
        Return the number of items in the collection.

        Returns
        -------
        int
            The number of items in the collection.
        """

    @abstractmethod
    def diff(
        self: Self,
        items: list[Any] | ICollection,
    ) -> ICollection[T]:
        """
        Return items not present in the given collection.

        Parameters
        ----------
        items : list[typing.Any] | collections.abc.Collection
            The items to compare against.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new collection containing items not found in the provided collection.
        """

    @abstractmethod
    def each(
        self: Self,
        callback: Callable[[T], T],
    ) -> ICollection[T]:
        """
        Iterate over items and apply the callback to each.

        Parameters
        ----------
        callback : collections.abc.Callable
            The callback function to apply to each item.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance.
        """

    @abstractmethod
    def every(
        self: Self,
        callback: Callable[[T], object],
    ) -> bool:
        """
        Determine whether all items satisfy the given callback condition.

        Parameters
        ----------
        callback : collections.abc.Callable
            The callback function to test each item.

        Returns
        -------
        bool
            True if all items pass the test, otherwise False.
        """

    @abstractmethod
    def filter(
        self: Self,
        callback: Callable[[T], object],
    ) -> ICollection[T]:
        """
        Filter items in the collection using a callback.

        Parameters
        ----------
        callback : collections.abc.Callable
            Function to determine if an item should be included.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing items for which the callback returns True.
        """

    @abstractmethod
    def flatten(self: Self) -> ICollection[Any]:
        """
        Flatten the collection into a single dimension.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing all items, flattened to a single dimension.
        """

    @abstractmethod
    def forget(
        self: Self,
        *keys: int | str,
    ) -> Self:
        """
        Remove items from the collection by their keys.

        Parameters
        ----------
        *keys : typing.Any
            The keys of the items to remove from the collection.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance after removal.
        """

    @abstractmethod
    def forPage(
        self: Self,
        page: int,
        number: int,
    ) -> ICollection[T]:
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
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing the paginated items.
        """

    @overload
    def get(self, key: int | str) -> T | None: ...

    @overload
    def get[D](self, key: int | str, default: Callable[[], D]) -> T | D: ...

    @overload
    def get[D](self, key: int | str, default: D) -> T | D: ...

    @abstractmethod
    def get(
        self: Self,
        key: int | str,
        default: object | None = None,
    ) -> object:
        """
        Retrieve an item from the collection by key.

        Parameters
        ----------
        key : typing.Any
            The key or index to retrieve from the collection.
        default : typing.Any, optional
            The value to return if the key is not found. Defaults to None.

        Returns
        -------
        typing.Any
            The item at the specified key, or the default value if not found.
        """

    @abstractmethod
    def implode(
        self: Self,
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
    def isEmpty(self: Self) -> bool:
        """
        Check if the collection is empty.

        Returns
        -------
        bool
            True if the collection is empty, otherwise False.
        """

    @abstractmethod
    def map[U](
        self: Self,
        callback: Callable[[T], U],
    ) -> ICollection[U]:
        """
        Apply a function to each item in the collection.

        Parameters
        ----------
        callback : collections.abc.Callable
            Function to apply to each item.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing the mapped items.
        """

    @overload
    def mapInto[U](
        self,
        cls: type[U],
        method: None = None,
        **kwargs: object,
    ) -> ICollection[U | None]: ...

    @overload
    def mapInto(self, cls: type, method: str, **kwargs: object) -> ICollection[Any]: ...

    @abstractmethod
    def mapInto(
        self: Self,
        cls: type,
        method: str | None = None,
        **kwargs: object,
    ) -> ICollection[Any]:
        """
        Map items into instances of the given class.

        Parameters
        ----------
        cls : type
            The class to map items into.
        method : str | None, optional
            The method to call on the class, by default None.
        **kwargs : typing.Any
            Additional keyword arguments to pass to the constructor or method.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new collection with the mapped instances.
        """

    @abstractmethod
    def merge(
        self: Self,
        items: list[T] | ICollection[T],
    ) -> Self:
        """
        Merge the collection with the given items.

        Parameters
        ----------
        items : list[typing.Any] | collections.abc.Collection
            The items to merge into the collection.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance with merged items.

        Raises
        ------
        TypeError
            If items cannot be merged due to incompatible types.
        """

    @abstractmethod
    def pluck(
        self: Self,
        value: str,
        key: str | None = None,
    ) -> ICollection[Any]:
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
        orionis.support.types.contracts.collection.ICollection
            A new collection containing the plucked values.
        """

    @abstractmethod
    def pop(self: Self) -> T | None:
        """
        Remove and return the last item from the collection.

        Returns
        -------
        typing.Any
            The last item from the collection.
        """

    @abstractmethod
    def prepend(
        self: Self,
        value: T,
    ) -> Self:
        """
        Prepend an item to the beginning of the collection.

        Parameters
        ----------
        value : typing.Any
            The value to prepend to the collection.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance with the new item prepended.
        """

    @abstractmethod
    def pull(
        self: Self,
        key: int | str,
    ) -> T | None:
        """
        Remove and return an item from the collection by key.

        Parameters
        ----------
        key : typing.Any
            The key of the item to remove.

        Returns
        -------
        typing.Any
            The removed item, or None if not found.
        """

    @abstractmethod
    def push(
        self: Self,
        value: T,
    ) -> Self:
        """
        Add an item to the end of the collection.

        Parameters
        ----------
        value : typing.Any
            The value to add to the collection.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance with the new item appended.
        """

    @abstractmethod
    def put(
        self: Self,
        key: int | str,
        value: T,
    ) -> Self:
        """
        Insert or update an item in the collection at the specified key.

        Parameters
        ----------
        key : typing.Any
            The key or index at which to set the value.
        value : typing.Any
            The value to assign at the specified key.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance with the updated item.
        """

    @overload
    def random(self, count: None = None) -> T | None: ...

    @overload
    def random(self, count: int) -> ICollection[T] | None: ...

    @abstractmethod
    def random(
        self: Self,
        count: int | None = None,
    ) -> T | ICollection[T] | None:
        """
        Return one or more random items from the collection.

        Parameters
        ----------
        count : int | None, optional
            The number of items to return. If None, returns a single item.

        Returns
        -------
        typing.Any | collections.abc.Collection | None
            A single random item if count is None, a Collection if count is given,
            or None if the collection is empty.

        Raises
        ------
        ValueError
            If count is greater than the number of items in the collection.
        """

    @abstractmethod
    def reduce(
        self: Self,
        callback: Callable,
        initial: object = 0,
    ) -> object:
        """
        Reduce the collection to a single value using a callback.

        Parameters
        ----------
        callback : collections.abc.Callable
            The function to apply cumulatively to the items.
        initial : typing.Any, optional
            The initial value to start the reduction, by default 0.

        Returns
        -------
        typing.Any
            The reduced value after applying the callback.
        """

    @abstractmethod
    def reject(
        self: Self,
        callback: Callable[[T], object],
    ) -> Self:
        """
        Reject items that pass a given truth test.

        Parameters
        ----------
        callback : collections.abc.Callable
            The callback function to test items.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance with items not passing the test.
        """

    @abstractmethod
    def reverse(self: Self) -> Self:
        """
        Reverse the order of items in the collection.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance with items in reversed order.
        """

    @abstractmethod
    def serialize(self: Self) -> list[Any]:
        """
        Serialize the collection items as a list.

        Returns
        -------
        list of typing.Any
            The serialized items in the collection.
        """

    @abstractmethod
    def shift(self: Self) -> T | None:
        """
        Remove and return the first item from the collection.

        Returns
        -------
        typing.Any
            The first item from the collection, or None if the collection is empty.
        """

    @abstractmethod
    def sort(
        self: Self,
        key: str | None = None,
    ) -> Self:
        """
        Sort the items in the collection.

        Parameters
        ----------
        key : str | None, optional
            The key to sort by. If None, sort items directly.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance with sorted items.
        """

    @abstractmethod
    def sum(
        self: Self,
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
        self: Self,
        **kwargs: object,
    ) -> str:
        """
        Return the collection items as a JSON string.

        Parameters
        ----------
        **kwargs : typing.Any
            Additional arguments to pass to json.dumps.

        Returns
        -------
        str
            JSON representation of the serialized collection items.
        """

    @abstractmethod
    def groupBy(
        self: Self,
        key: str,
    ) -> ICollection[Any]:
        """
        Group items in the collection by a specified key.

        Parameters
        ----------
        key : str
            The key to group items by.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection instance containing a dictionary where each key is a
            unique value from the specified key, and each value is a list of items
            sharing that key.
        """

    @abstractmethod
    def transform(
        self: Self,
        callback: Callable[[T], T],
    ) -> ICollection[T]:
        """
        Transform each item in the collection using a callback.

        Parameters
        ----------
        callback : collections.abc.Callable
            The callback function to transform items.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance with transformed items.
        """

    @abstractmethod
    def unique(
        self: Self,
        key: str | Callable[[T], object] | None = None,
    ) -> ICollection[T]:
        """
        Return unique items from the collection.

        Parameters
        ----------
        key : str | collections.abc.Callable | None, optional
            Field name or identity selector; None compares complete items.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing only unique items.
        """

    @abstractmethod
    def where(
        self: Self,
        key: str,
        *args: object,
    ) -> ICollection[T]:
        """
        Filter items by a given key-value pair or comparison.

        Parameters
        ----------
        key : str
            The key to filter by.
        *args : typing.Any
            The operator and value, or just the value.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection instance containing filtered items.
        """

    @abstractmethod
    def whereIn(
        self: Self,
        key: str,
        values: list[Any] | ICollection,
    ) -> ICollection[T]:
        """
        Filter items where a given key's value is in a list of values.

        Parameters
        ----------
        key : str
            The key to filter by.
        values : list[typing.Any] | collections.abc.Collection
            The list of values to check against.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new collection containing items where the key's value is in values.
        """

    @abstractmethod
    def whereNotIn(
        self: Self,
        key: str,
        values: list[Any] | ICollection,
    ) -> ICollection[T]:
        """
        Filter items where a given key's value is not in a list of values.

        Parameters
        ----------
        key : str
            The key to filter by.
        values : list[typing.Any] | collections.abc.Collection
            The list of values to check against.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing items where the key's value is not in values.
        """

    @abstractmethod
    def zip[U](
        self: Self,
        items: list[U] | ICollection[U],
    ) -> ICollection[list[T | U]]:
        """
        Zip the collection with the given items by index.

        Parameters
        ----------
        items : list[typing.Any] | collections.abc.Collection
            The items to zip with.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            A new Collection containing pairs of items from both collections.

        Raises
        ------
        TypeError
            If the 'items' parameter is not a list or Collection.
        """

    @abstractmethod
    def setAppends(
        self: Self,
        appends: list[str],
    ) -> Self:
        """
        Set the attributes to append to the Collection.

        Parameters
        ----------
        appends : list[str]
            The attributes to append.

        Returns
        -------
        orionis.support.types.contracts.collection.ICollection
            The current collection instance.
        """
