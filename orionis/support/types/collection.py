from __future__ import annotations
import contextlib
import json
import operator
import random
import secrets
from functools import reduce
from itertools import groupby
from typing import TYPE_CHECKING, Any
from dotty_dict import dotty
from orionis.support.types.contracts.collection import ICollection

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

# Map comparison names to their implementations.
_OPERATORS: dict[str, Any] = {
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
}

# Sentinel object: distinguishes "attribute absent" from a legitimate None
# value in getattr calls, eliminating the hasattr+getattr double-lookup.
_MISSING: object = object()


class Collection(ICollection):

    # ruff: noqa: ANN401

    def __hash__(self) -> int:
        """
        Compute the hash value of the collection.

        Returns
        -------
        int
            Hash value of the collection based on its items.
        """
        # Convert items to tuple for hashing
        return hash(tuple(self._items))

    def __init__(
        self,
        items: list[Any] | None = None,
    ) -> None:
        """
        Initialize a new Collection instance.

        Parameters
        ----------
        items : list[Any] or None, optional
            Initial items for the collection (default is None).

        Returns
        -------
        None
            This method does not return a value.
        """
        self._items = items or []
        self.__appends__ = []

    def take(
        self,
        number: int,
    ) -> Collection:
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
        # Take items from the end if number is negative, otherwise from the start
        if number < 0:
            return self[number:]
        return self[:number]

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
        if callback is None:
            return self._items[0] if self._items else None

        self.__checkIsCallable(callback)
        for item in self._items:
            if callback(item):
                return item
        return None

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
            The last item in the filtered collection, or None if empty.
        """
        if callback is None:
            return self._items[-1] if self._items else None

        self.__checkIsCallable(callback)
        result = None
        for item in self._items:
            if callback(item):
                result = item
        return result

    def all(self) -> list[Any]:
        """
        Return all items in the collection.

        Returns
        -------
        list of Any
            All items contained in the collection.
        """
        return self._items

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
        # Initialize result
        result = 0

        # Get values using the key or use all items if key is None
        items = self.__getValue(key) or self._items

        # Return zero when there are no values to average.
        if not items:
            return 0

        # Calculate average
        with contextlib.suppress(TypeError):
            result = sum(items) / len(items)
        return result

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
        # Get values using the key or use all items if key is None
        result = 0
        items = self.__getValue(key) or self._items
        try:
            return max(items)
        except (TypeError, ValueError):
            pass
        return result

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
        result = 0
        items = self.__getValue(key) or self._items
        try:
            return min(items)
        except (TypeError, ValueError):
            pass
        return result

    def chunk(
        self,
        size: int,
    ) -> Collection:
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
        # Validate size parameter
        if size <= 0:
            error_msg = "Chunk size must be greater than 0"
            raise ValueError(error_msg)

        # Divide the collection into chunks of the requested size.
        items = [self[i : i + size] for i in range(0, len(self._items), size)]
        return self.__class__(items)

    def collapse(self) -> Collection:
        """
        Collapse the collection of arrays into a single, flat collection.

        Returns
        -------
        Collection
            A new Collection containing all items from nested arrays, flattened.
        """
        items = []
        # Flatten all nested arrays into a single list
        for item in self:
            items += self.__getItems(item)
        return self.__class__(items)

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
        # If a value is provided, check for the key-value pair using a lambda.
        if value is not None:
            return self.contains(lambda x: self.__dataGet(x, key) == value)

        # Stop at the first item matching the callable.
        if callable(key):
            return any(key(x) for x in self._items)

        # Otherwise, check if key is in the collection.
        return key in self

    def count(self) -> int:
        """
        Return the number of items in the collection.

        Returns
        -------
        int
            The number of items in the collection.
        """
        # Return the length of the internal _items list
        return len(self._items)

    def diff(
        self,
        items: list[Any] | Collection,
    ) -> Collection:
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
        # Extract items from Collection if necessary
        items = self.__getItems(items)
        # Use a set for hashable values and a list for unhashable values.
        try:
            items_set = set(items)
            return self.__class__([x for x in self._items if x not in items_set])
        except TypeError:
            return self.__class__([x for x in self._items if x not in items])

    def each(
        self,
        callback: Callable,
    ) -> Collection:
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
        self.__checkIsCallable(callback)
        # Update the stored items using the supplied callback.
        _its = self._items
        for k in range(len(_its)):
            result = callback(_its[k])
            if not result:
                break
            _its[k] = result
        return self

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
        self.__checkIsCallable(callback)
        # Use all() to check if every item satisfies the callback condition
        return all(callback(x) for x in self._items)

    def filter(
        self,
        callback: Callable,
    ) -> Collection:
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
        # Ensure the callback is callable before filtering
        self.__checkIsCallable(callback)
        return self.__class__([item for item in self._items if callback(item)])

    def flatten(self) -> Collection:
        """
        Flatten the collection into a single dimension.

        Returns
        -------
        Collection
            A new Collection containing all items, flattened to a single dimension.
        """
        def _flatten(items: object) -> Iterator[Any]:
            """
            Yield scalar values from nested lists and dictionaries.

            Parameters
            ----------
            items : object
                Value or nested container to flatten.

            Yields
            ------
            Any
                Scalar values in traversal order.
            """
            if isinstance(items, dict):
                for v in items.values():
                    yield from _flatten(v)
            elif isinstance(items, list):
                for i in items:
                    yield from _flatten(i)
            else:
                yield items

        return self.__class__(list(_flatten(self._items)))

    def forget(
        self,
        *keys: int | str,
    ) -> Collection:
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
        # Sort keys in reverse order to avoid index shifting issues during deletion
        keys = sorted(keys, reverse=True)
        for key in keys:
            del self[key]
        return self

    def forPage(
        self,
        page: int,
        number: int,
    ) -> Collection:
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
        # Validate parameters
        page = max(page, 1)

        # Validate number parameter
        if number <= 0:
            error_msg = "Number of items per page must be greater than 0"
            raise ValueError(error_msg)

        # Calculate start and end indices for the requested page
        start = (page - 1) * number
        return self.__class__(self._items[start:start + number])

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
        try:
            return self[key]
        except IndexError:
            pass
        return self.__value(default)

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
        # Return empty string if collection is empty
        if not self:
            return ""

        # Check the type of the first item; direct _items access skips
        # the filter/callback machinery of first() for a plain index read
        first = self._items[0]

        # If items are not strings and a key is provided, pluck the key values
        if not isinstance(first, str) and key:
            return glue.join(str(x) for x in self.pluck(key))

        # Otherwise, join string representations of all items
        return glue.join([str(x) for x in self])

    def isEmpty(self) -> bool:
        """
        Check if the collection is empty.

        Returns
        -------
        bool
            True if the collection is empty, otherwise False.
        """
        # Return True if the collection has no items
        return not self

    def map(
        self,
        callback: Callable,
    ) -> Collection:
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
        # Ensure the callback is callable before mapping
        self.__checkIsCallable(callback)
        return self.__class__([callback(x) for x in self._items])

    def mapInto(
        self,
        cls: type,
        method: str | None = None,
        **kwargs: object,
    ) -> Collection:
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
        # Validate that cls is a type
        if not isinstance(cls, type):
            error_msg = "cls must be a type"
            raise TypeError(error_msg)

        mapper = getattr(cls, method, None) if method else None
        if method and mapper is None:
            return self.__class__([None] * len(self._items))

        results = []
        # Iterate through each item and map into the class or its method
        for item in self:
            try:
                if method:
                    results.append(mapper(item, **kwargs))
                else:
                    results.append(cls(item))
            except (TypeError, AttributeError, ValueError):
                results.append(None)
        return self.__class__(results)

    def merge(
        self,
        items: list[Any] | Collection,
    ) -> Collection:
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
        # Ensure items is a list or Collection before merging
        if not isinstance(items, (list, Collection)):
            error_msg = "Unable to merge incompatible types"
            raise TypeError(error_msg)

        items = self.__getItems(items)
        self._items += items
        return self

    def pluck(
        self,
        value: str,
        key: str | None = None,
    ) -> Collection:
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
        # Initialize attributes as dict or list based on presence of key
        if key:
            attributes: dict[Any, Any] = {}
        else:
            attributes: list[Any] = []

        for item in self:
            # Get the value to pluck
            plucked_value = self.__dataGet(item, value)
            if key:
                # Use the key as the dictionary key
                dict_key = self.__dataGet(item, key)
                attributes[dict_key] = plucked_value
            # Add to list
            elif plucked_value is not None:
                attributes.append(plucked_value)

        # Return a new Collection with the plucked values
        return self.__class__(attributes)

    def pop(self) -> object:
        """
        Remove and return the last item from the collection.

        Returns
        -------
        Any
            The last item from the collection, or None if empty.
        """
        # Return None if collection is empty
        if not self:
            return None

        # Remove and return the last item in the internal _items list
        return self._items.pop()

    def prepend(
        self,
        value: object,
    ) -> Collection:
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
        # Insert the value at the start of the internal _items list
        self._items.insert(0, value)
        return self

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
        # Retrieve the value at the specified key, then remove it from the collection
        value = self.get(key)
        self.forget(key)
        return value

    def push(
        self,
        value: object,
    ) -> Collection:
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
        # Append the value to the internal _items list
        self._items.append(value)
        return self

    def put(
        self,
        key: int | str,
        value: object,
    ) -> Collection:
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
        # Set the value at the specified key in the collection
        self[key] = value
        return self

    def random(
        self,
        count: int | None = None,
    ) -> object | Collection | None:
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
        # Get the total number of items in the collection
        collection_count = self.count()
        if collection_count == 0:
            return None

        # Validate count parameter
        if count is not None:
            if count < 0:
                error_msg = "count argument must be non-negative"
                raise ValueError(error_msg)
            if count > collection_count:
                error_msg = "count argument must be inferior to collection length."
                raise ValueError(error_msg)

        # Return random items based on count
        if count:
            # Select 'count' random items and update the collection
            self._items = random.sample(self._items, k=count) # NOSONAR
            return self

        # Return a single random item
        return secrets.choice(self._items)

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
        # Use functools.reduce to accumulate values in the collection
        return reduce(callback, self, initial)

    def reject(
        self,
        callback: Callable,
    ) -> Collection:
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
        # Ensure the callback is callable before filtering
        self.__checkIsCallable(callback)
        # Filter items that do NOT satisfy the callback (opposite of filter)
        self._items = [item for item in self._items if not callback(item)]
        return self

    def reverse(self) -> Collection:
        """
        Reverse the order of items in the collection.

        Returns
        -------
        Collection
            The current collection instance with items in reversed order.
        """
        # Reverse the current collection in place.
        self._items.reverse()
        return self

    def serialize(self) -> list[Any]:
        """
        Serialize the collection items as a list.

        Returns
        -------
        list of Any
            The serialized items in the collection.
        """
        def _serialize(item: object) -> object:
            """
            Serialize one collection item with its declared appends.

            Parameters
            ----------
            item : object
                Collection item to serialize.

            Returns
            -------
            object
                Serialized representation of the item.
            """
            # Set appends if present for each item
            if self.__appends__:
                set_appends = getattr(item, "set_appends", _MISSING)
                if set_appends is not _MISSING:
                    with contextlib.suppress(AttributeError):
                        set_appends(self.__appends__)
            # Prefer serialize method, then to_dict, else return as is
            serializer = getattr(item, "serialize", _MISSING)
            if serializer is not _MISSING:
                return serializer()
            serializer = getattr(item, "to_dict", _MISSING)
            if serializer is not _MISSING:
                return serializer()
            return item

        return list(map(_serialize, self._items))

    def shift(self) -> object:
        """
        Remove and return the first item from the collection.

        Returns
        -------
        Any
            The first item from the collection, or None if the collection is empty.
        """
        # Remove and return the first item using pull(0)
        return self.pull(0)

    def sort(
        self,
        key: str | None = None,
    ) -> Collection:
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
        # Sort by key if provided, otherwise sort items directly
        if key:
            # Sort by extracting the key from each item
            self._items.sort(key=lambda x: self.__dataGet(x, key))
        else:
            # Sort items directly
            self._items.sort()
        return self

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
        result = 0
        # Get values using the key or use all items if key is None
        items = self.__getValue(key) or self._items
        with contextlib.suppress(TypeError):
            result = sum(items)
        return result

    def toJson(
        self,
        **kwargs: object,
    ) -> str:
        """
        Return the collection items as a JSON string.

        Parameters
        ----------
        **kwargs : object
            Additional keyword arguments for json.dumps.

        Returns
        -------
        str
            JSON string representing the serialized collection items.
        """
        # Serialize the collection and convert to JSON string
        return json.dumps(self.serialize(), **kwargs)

    def groupBy(
        self,
        key: str,
    ) -> Collection:
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
        # Pair each item with its grouping key before sorting.
        keyed = [(self.__dataGet(x, key), x) for x in self._items]
        keyed.sort(key=lambda t: t[0])

        new_dict: dict[Any, list[Any]] = {}
        for k, g in groupby(keyed, key=lambda t: t[0]):
            new_dict[k] = [t[1] for t in g]

        return Collection(new_dict)

    def transform(
        self,
        callback: Callable,
    ) -> Collection:
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
        # Ensure the callback is callable before transforming items
        self.__checkIsCallable(callback)
        self._items = [callback(item) for item in self._items]
        return self

    def unique(
        self,
        key: str | None = None,
    ) -> Collection:
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
        # If no key is provided, use set to get unique items directly
        if not key:
            return self._getUniqueItemsWithoutKey()

        # If the collection is a dict, return as is (no uniqueness logic)
        if isinstance(self.all(), dict):
            return self

        # Otherwise, get unique items based on the specified key
        return self._getUniqueItemsByKey(key)

    def _getUniqueItemsWithoutKey(self) -> Collection:
        """
        Return unique items from the collection without using a key.

        Returns
        -------
        Collection
            A new Collection containing only unique items.
        """
        try:
            # Attempt to use set for hashable items
            items = list(set(self._items))
        except TypeError:
            # Fallback for unhashable items: manual uniqueness check
            items = []
            for item in self._items:
                if item not in items:
                    items.append(item)
        return self.__class__(items)

    def _getUniqueItemsByKey(self, key: str) -> Collection:
        """
        Get unique items from the collection based on a specified key.

        Parameters
        ----------
        key : str
            The key to determine uniqueness for each item.

        Returns
        -------
        Collection
            A new Collection containing only unique items by the given key.
        """
        keys: set[Any] = set()
        items: list[Any] = []
        # Iterate and collect unique items based on the comparison key
        for item in self:
            comparison = self.__dataGet(item, key)
            self._addUniqueItem(comparison, item, keys, items)
        return self.__class__(items)

    def _addUniqueItem(
        self,
        comparison: Any,
        item: Any,
        keys: set[Any],
        items: list[Any],
    ) -> None:
        """
        Add a unique item to the collection based on the comparison value.

        Parameters
        ----------
        comparison : Any
            The value used to determine uniqueness.
        item : Any
            The item to potentially add.
        keys : set[Any]
            The set of seen comparison values.
        items : list[Any]
            The list of unique items.

        Returns
        -------
        None
            This method does not return a value.
        """
        try:
            # Add item if its comparison value is not already in keys
            if comparison not in keys:
                items.append(item)
                keys.add(comparison)
        except TypeError:
            # Compare unhashable values against existing keys.
            if not any(comp == comparison for comp in keys):
                items.append(item)

    def where(
        self,
        key: str,
        *args: object,
    ) -> Collection:
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
        # Validate arguments
        if not args:
            error_msg = "At least one argument (value) must be provided"
            raise ValueError(error_msg)

        op: str = "=="
        value: Any = args[0]
        min_args_for_operator = 2

        # If an operator is provided, use it and the next argument as value
        if len(args) >= min_args_for_operator:
            op = args[0]
            value = args[1]

        attributes: list[Any] = []

        # Iterate and filter items based on the key and comparison using __dataGet
        for item in self._items:
            comparison = self.__dataGet(item, key)
            try:
                if self.__makeComparison(comparison, value, op):
                    attributes.append(item)
            except (TypeError, ValueError):
                # Skip items that can't be compared
                continue

        return self.__class__(attributes)

    def whereIn(
        self,
        key: str,
        values: list[Any] | Collection,
    ) -> Collection:
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
        # Extract values from Collection if necessary
        values = self.__getItems(values)
        try:
            value_set = set(values)
            unhashable_values: list[Any] = []
        except TypeError:
            value_set = set()
            unhashable_values = values
        str_values: set[str] = {str(v) for v in values}
        attributes: list[Any] = []

        # Iterate and collect items where the key's value is in the provided values
        for item in self._items:
            comparison = self.__dataGet(item, key)
            try:
                matches_value = comparison in value_set
            except TypeError:
                matches_value = comparison in values
            if (
                matches_value
                or comparison in unhashable_values
                or str(comparison) in str_values
            ):
                attributes.append(item)

        return self.__class__(attributes)

    def whereNotIn(
        self,
        key: str,
        values: list[Any] | Collection,
    ) -> Collection:
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
        # Extract values from Collection if necessary
        values = self.__getItems(values)
        try:
            value_set = set(values)
            unhashable_values: list[Any] = []
        except TypeError:
            value_set = set()
            unhashable_values = values
        str_values: set[str] = {str(v) for v in values}
        attributes: list[Any] = []

        # Iterate and collect items where the key's value is not in the provided values
        for item in self._items:
            comparison = self.__dataGet(item, key)
            try:
                matches_value = comparison in value_set
            except TypeError:
                matches_value = comparison in values
            if (
                not matches_value
                and comparison not in unhashable_values
                and str(comparison) not in str_values
            ):
                attributes.append(item)

        return self.__class__(attributes)

    def zip(
        self,
        items: list[Any] | Collection,
    ) -> Collection:
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
        # Validate input type first
        if not isinstance(items, (list, Collection)):
            error_msg = "The 'items' parameter must be a list or a Collection"
            raise TypeError(error_msg)

        # Extract items from Collection if necessary
        items = self.__getItems(items)

        # Pair collection items with the supplied values.
        return self.__class__(
            [[x, y] for x, y in zip(self._items, items, strict=False)],
        )

    def setAppends(
        self,
        appends: list[str],
    ) -> Collection:
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
        # Extend the __appends__ list with the provided attributes
        self.__appends__ += appends
        return self

    def addRelation(
        self,
        relation_data: dict[str, Any],
    ) -> Collection:
        """
        Add relation data to the collection.

        Parameters
        ----------
        relation_data : dict[str, Any]
            The relation data to add.

        Returns
        -------
        Collection
            The current collection instance.
        """
        # Add relation data to items if they support it
        for item in self:
            if hasattr(item, "setRelation"):
                for key, value in relation_data.items():
                    item.setRelation(key, value)
        return self

    def __getValue(
        self,
        key: str | Callable | None,
    ) -> list[Any] | None:
        """
        Retrieve values from items using a key or callback.

        Parameters
        ----------
        key : str | Callable | None
            The key to extract or callback to apply.

        Returns
        -------
        list[Any] | None
            List of extracted values, or None if key is not provided.
        """
        if not key:
            return None

        items: list[Any] = []
        # Iterate through each item and extract value by key or callback
        for item in self._items:
            if isinstance(key, str):
                # Read the named attribute when it exists.
                val = getattr(item, key, _MISSING)
                if val is not _MISSING:
                    items.append(val)
                elif isinstance(item, dict) and key in item:
                    items.append(item[key])
            elif callable(key):
                result = key(item)
                if result:
                    items.append(result)
        return items

    def __dataGet(
        self,
        item: object,
        key: str,
        default: object = None,
    ) -> object:
        """
        Retrieve a value from an item using a nested key notation.

        Parameters
        ----------
        item : Any
            The item to extract data from.
        key : str
            The key to look for, supports nested notation.
        default : Any, optional
            The value to return if the key is not found. Defaults to None.

        Returns
        -------
        Any
            The extracted value if found, otherwise the default value.
        """
        try:
            if isinstance(item, (list, tuple)):
                return item[int(key)] if key.isdigit() else default
            if isinstance(item, dict):
                # Read a plain key directly from the item.
                # dotty() is only needed for dot-notation or wildcard (*) keys.
                if "." not in key and "*" not in key:
                    return item.get(key, default)
                dotty_key = key.replace("*", ":")
                return dotty(item).get(dotty_key, default)
            # Read the named attribute when it exists.
            val = getattr(item, key, _MISSING)
            if val is not _MISSING:
                return val
            return self.__value(default)
        except (IndexError, AttributeError, KeyError, TypeError, ValueError):
            return self.__value(default)

    def __value(
        self,
        value: object,
    ) -> object:
        """
        Return the evaluated value if callable, otherwise return the value itself.

        Parameters
        ----------
        value : Any
            The value or callable to evaluate.

        Returns
        -------
        Any
            The result of calling the value if it is callable, otherwise the value
            itself.
        """
        # Evaluate the value if it is callable, otherwise return as is
        if callable(value):
            return value() # NOSONAR
        return value

    def __checkIsCallable(
        self,
        callback: object,
        *,
        raise_exception: bool = True,
    ) -> bool:
        """
        Check if the given callback is callable.

        Parameters
        ----------
        callback : Any
            The callback to check.
        raise_exception : bool, optional
            Whether to raise an exception if not callable. Default is True.

        Returns
        -------
        bool
            True if the callback is callable, otherwise False.

        Raises
        ------
        ValueError
            If callback is not callable and raise_exception is True.
        """
        # Return False or raise an error if callback is not callable
        if not callable(callback):
            if not raise_exception:
                return False
            error_msg = "The 'callback' should be a function"
            raise ValueError(error_msg)
        return True

    def __makeComparison(
        self,
        a: object,
        b: object,
        op: str,
    ) -> bool:
        """
        Compare two values using the specified operator.

        Parameters
        ----------
        a : Any
            The first value to compare.
        b : Any
            The second value to compare.
        op : str
            The comparison operator as a string.

        Returns
        -------
        bool
            True if the comparison is valid, otherwise False.
        """
        # Select the comparison implementation by operator name.
        if op not in _OPERATORS:
            msg = "Unsupported operator: " + str(op)
            raise ValueError(msg)

        try:
            return _OPERATORS[op](a, b)
        except TypeError:
            # Handle incompatible types by converting to string
            try:
                return _OPERATORS[op](str(a), str(b))
            except (TypeError, ValueError):
                return False

    def __iter__(self) -> Iterator[Any]:
        """
        Iterate over the items in the collection.

        Yields
        ------
        Any
            Each item in the collection.
        """
        # Yield each item in the internal _items list
        yield from self._items

    def __eq__(
        self,
        other: object,
    ) -> bool:
        """
        Compare the collection with another object for equality.

        Parameters
        ----------
        other : object
            The object to compare with the current collection.

        Returns
        -------
        bool
            True if the collections are equal, False otherwise.
        """
        # Compare items if other is a Collection, else compare directly
        if isinstance(other, Collection):
            return other.all() == self._items
        return other == self._items

    def __getitem__(
        self,
        item: int | slice,
    ) -> object | Collection:
        """
        Retrieve an item or a slice from the collection.

        Parameters
        ----------
        item : int or slice
            The index or slice to retrieve.

        Returns
        -------
        Any or Collection
            The item at the given index, or a new Collection for a slice.
        """
        # Return a new Collection if a slice is provided, else return the item.
        if isinstance(item, slice):
            return self.__class__(self._items[item])
        return self._items[item]

    def __setitem__(
        self,
        key: int | str,
        value: object,
    ) -> None:
        """
        Set the value at the specified key in the collection.

        Parameters
        ----------
        key : Any
            The index or key at which to set the value.
        value : Any
            The value to assign at the specified key.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Assign the value to the specified key in the internal _items list
        self._items[key] = value

    def __delitem__(
        self,
        key: int | str,
    ) -> None:
        """
        Delete an item from the collection at the specified key.

        Parameters
        ----------
        key : Any
            The index or key of the item to remove.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Remove the item at the specified key from the internal _items list
        del self._items[key]

    def __ne__(
        self,
        other: object,
    ) -> bool:
        """
        Determine if the collection is not equal to another object.

        Parameters
        ----------
        other : object
            The object to compare with the current collection.

        Returns
        -------
        bool
            True if the collections are not equal, otherwise False.
        """
        # Extract items from the other object if it is a Collection
        other = self.__getItems(other)
        # Return True if the items are not equal, otherwise False
        return other != self._items

    def __len__(self) -> int:
        """
        Return the number of items in the collection.

        Returns
        -------
        int
            The total number of items in the collection.
        """
        # Return the length of the internal _items list
        return len(self._items)

    def __le__(
        self,
        other: object,
    ) -> bool:
        """
        Compare if the current collection is less than or equal to another object.

        Parameters
        ----------
        other : object
            The object to compare with the current collection.

        Returns
        -------
        bool
            True if the current collection is less than or equal to the other object,
            False otherwise.
        """
        # Extract items from the other object if it is a Collection
        other = self.__getItems(other)
        # Return True if the items are less than or equal, False otherwise
        return self._items <= other

    def __lt__(
        self,
        other: object,
    ) -> bool:
        """
        Compare if the current collection is less than another object.

        Parameters
        ----------
        other : object
            Object to compare with the current collection.

        Returns
        -------
        bool
            True if the current collection is less than the other object,
            otherwise False.
        """
        # Extract items from the other object if it is a Collection
        other = self.__getItems(other)
        # Return True if the items are less than, otherwise False
        return self._items < other

    def __ge__(
        self,
        other: object,
    ) -> bool:
        """
        Compare if the current collection is greater than or equal to another object.

        Parameters
        ----------
        other : object
            Object to compare with the current collection.

        Returns
        -------
        bool
            True if the current collection is greater than or equal to the other
            object, otherwise False.
        """
        # Extract items from the other object if it is a Collection
        other = self.__getItems(other)
        # Return True if the items are greater than or equal, otherwise False
        return self._items >= other

    def __gt__(
        self,
        other: object,
    ) -> bool:
        """
        Compare if the current collection is greater than another object.

        Parameters
        ----------
        other : object
            The object to compare with the current collection.

        Returns
        -------
        bool
            True if the current collection is greater than the other object,
            otherwise False.
        """
        # Extract items from the other object if it is a Collection
        other = self.__getItems(other)
        # Return True if the items are greater than, otherwise False
        return self._items > other

    @classmethod
    def __getItems(
        cls,
        items: list[Any] | Collection | object,
    ) -> list[Any] | object:
        """
        Extract the underlying items from a Collection or return the input as-is.

        Parameters
        ----------
        items : list[Any] | Collection | object
            The input to extract items from. If a Collection, its items are
            returned; otherwise, the input is returned unchanged.

        Returns
        -------
        list[Any] | object
            The extracted items if `items` is a Collection, otherwise the
            original input.
        """
        # If the input is a Collection, extract its items using the all() method
        if isinstance(items, Collection):
            items = items.all()
        return items
