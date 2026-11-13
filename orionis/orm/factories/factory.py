# ruff: noqa: ANN401, TC001
# Keep arbitrary model attributes and runtime factory-property annotations.
"""Build and persist model instances from reusable attribute definitions."""

from collections.abc import AsyncIterator, Callable, Iterator
from copy import deepcopy
from inspect import iscoroutinefunction
from typing import Any, Self
from orionis.orm.factories._attributes import copy_attributes
from orionis.orm.factories._faker import create_faker
from orionis.orm.factories.exceptions import (
    FactoryConcurrencyException,
    FactoryConfigurationException,
    FactoryDefinitionException,
    FactoryPersistenceException,
)
from orionis.orm.factories.sequence import Sequence
from orionis.orm.model import Model
from orionis.support.types.collection import Collection

from orionis.orm.factories.fake import Fake

type State = dict[str, Any] | Callable[[dict[str, Any]], dict[str, Any]]
"""Type alias for ``dict[str, Any] | Callable[[dict[str, Any]], dict[str, Any]]``."""


class Factory[TModel: Model]:
    """Build and persist model instances from reusable attribute definitions."""

    __slots__ = (
        "_busy",
        "_count",
        "_fake",
        "_model",
        "_sequence",
        "_sequence_index",
        "_states",
    )
    """Declare the instance attribute slots reserved by this class."""

    model: type[TModel] | None = None
    """Model selected for generation or persistence."""

    def __init__(
        self,
        *,
        locale: str | None = None,
        seed: int | None = None,
    ) -> None:
        """
        Validate the factory and initialize its independent data provider.

        Parameters
        ----------
        locale : str or None, optional
            Explicit locale override, or the configured ``app.locale``.
            Unavailable or unsupported locales fall back to ``en_US``.
        seed : int or None, optional
            Seed for the instance's random generator.

        Raises
        ------
        orionis.orm.factories.FactoryConfigurationException
            If the model, locale or seed is invalid.
        orionis.orm.factories.FactoryDefinitionException
            If no synchronous definition method is implemented.

        Returns
        -------
        None
            No return value.
        """
        model = self.model
        if (
            not isinstance(model, type)
            or not issubclass(model, Model)
            or model.__meta__ is None
        ):
            error_msg = "Factory.model must be a concrete Orionis Model class."
            raise FactoryConfigurationException(error_msg)
        definition = type(self).definition
        if (
            definition is Factory.definition
            or not callable(definition)
            or iscoroutinefunction(definition)
            or iscoroutinefunction(definition.__call__)
        ):
            error_msg = "A factory must implement synchronous definition()."
            raise FactoryDefinitionException(error_msg)
        if locale is not None and (not isinstance(locale, str) or not locale.strip()):
            error_msg = "Factory locale must be a nonempty locale string."
            raise FactoryConfigurationException(error_msg)
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            error_msg = "Factory seed must be an integer or None."
            raise FactoryConfigurationException(error_msg)
        self._model = model
        """Model selected for generation or persistence."""
        self._count = 1
        """Count value used by ``Factory``."""
        self._states: list[State] = []
        """Attribute transformations applied when building model instances."""
        self._sequence: Sequence | None = None
        """Sequence state used to vary attributes between generated instances."""
        self._sequence_index = 0
        """Sequence index value used by ``Factory``."""
        self._busy = False
        """Busy flag used by ``Factory``."""
        self._fake: Fake = create_faker(locale, seed)
        """Fake produced by ``create_faker``."""

    @property
    def fake(self) -> Fake:
        """
        Expose the instance's typed camelCase data provider facade.

        Returns
        -------
        orionis.orm.factories.Fake
            Orionis facade, including custom providers and ``unique``.
        """
        return self._fake

    def definition(self) -> dict[str, Any]:
        """
        Define the default attributes of one model.

        Returns
        -------
        dict of str ``to`` typing.Any
            Attributes to assign through the model constructor.

        Raises
        ------
        orionis.orm.factories.FactoryDefinitionException
            Always, unless overridden by a concrete factory.
        """
        error_msg = "A factory must implement definition()."
        raise FactoryDefinitionException(error_msg)

    def count(self, count: int) -> Self:
        """
        Set the number of models generated by subsequent operations.

        Parameters
        ----------
        count : int
            Nonnegative count; one returns a model, all others a Collection.

        Returns
        -------
        typing.Self
            This configured factory.

        Raises
        ------
        orionis.orm.factories.FactoryConfigurationException
            If count is not a nonnegative integer.
        """
        self._ensureIdle()
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            error_msg = "Factory count must be a nonnegative integer."
            raise FactoryConfigurationException(error_msg)
        self._count = count
        return self

    def state(self, state: State) -> Self:
        """
        Append attributes or a synchronous transformation of defaults.

        Parameters
        ----------
        state : dict or collections.abc.Callable
            Dictionary or callback receiving detached current attributes.

        Returns
        -------
        typing.Self
            This configured factory.

        Raises
        ------
        orionis.orm.factories.FactoryConfigurationException
            If state is not a dictionary or synchronous callable.
        """
        self._ensureIdle()
        is_callback = callable(state)
        if (
            (not isinstance(state, dict) and not is_callback)
            or iscoroutinefunction(state)
            or (is_callback and iscoroutinefunction(state.__call__))
        ):
            error_msg = "A state must be a dictionary or synchronous callback."
            raise FactoryConfigurationException(error_msg)
        try:
            self._states.append(
                state if is_callback else copy_attributes(state, "State"),
            )
        except FactoryDefinitionException as exc:
            error_msg = "State attributes must have string keys."
            raise FactoryConfigurationException(error_msg) from exc
        return self

    def sequence(self, sequence: Sequence) -> Self:
        """
        Install a sequence and restart this factory's position at zero.

        Parameters
        ----------
        sequence : orionis.orm.factories.Sequence
            Cycling mappings or callbacks of the absolute item index.

        Returns
        -------
        typing.Self
            This configured factory.

        Raises
        ------
        orionis.orm.factories.FactoryConfigurationException
            If sequence is not a Sequence instance.
        """
        self._ensureIdle()
        if not isinstance(sequence, Sequence):
            error_msg = "Factory.sequence() requires a Sequence instance."
            raise FactoryConfigurationException(error_msg)
        self._sequence = sequence
        self._sequence_index = 0
        return self

    def clearUnique(self) -> Self:
        """
        Clear remembered unique values without reseeding or rewinding.

        Returns
        -------
        typing.Self
            This factory, with its instance-wide unique pool cleared.
        """
        self._ensureIdle()
        self._fake.unique.clear()
        return self

    def make(self, **overrides: Any) -> TModel | Collection:
        """
        Construct models without database access or persistence events.

        Parameters
        ----------
        **overrides : typing.Any
            Attributes taking precedence over defaults, states and sequence.

        Returns
        -------
        ``TModel`` or orionis.support.types.Collection
            One model for count one; otherwise a Collection of models.
        """
        stream = self.iterMake(**overrides)
        try:
            if self._count == 1:
                return next(stream)
            return Collection(list(stream))
        finally:
            stream.close()

    async def create(
        self,
        **overrides: Any,
    ) -> TModel | Collection:
        """
        Construct and save each model through Orionis's event lifecycle.

        Parameters
        ----------
        **overrides : typing.Any
            Final attribute overrides, subject to normal mass assignment.

        Returns
        -------
        ``TModel`` or orionis.support.types.Collection
            Persisted models, with the same cardinality rules as ``make``.

        Notes
        -----
        No implicit transaction is opened. Earlier successful writes survive
        a later failure unless the caller supplies a database transaction.
        """
        stream = self.iterCreate(**overrides)
        try:
            if self._count == 1:
                return await anext(stream)
            return Collection([model async for model in stream])
        finally:
            await stream.aclose()

    def iterMake(self, **overrides: Any) -> Iterator[TModel]:
        """
        Yield unsaved models progressively, holding no result collection.

        Parameters
        ----------
        **overrides : typing.Any
            Final attribute overrides copied when iteration starts.

        Yields
        ------
        ``TModel``
            One unsaved model per iteration.

        Notes
        -----
        Close a partially consumed iterator before reusing this factory.
        """
        self._ensureIdle()
        self._busy = True
        try:
            detached = copy_attributes(overrides, "Overrides")
            for _ in range(self._count):
                yield self._makeOne(detached)
        finally:
            self._busy = False

    async def iterCreate(
        self,
        **overrides: Any,
    ) -> AsyncIterator[TModel]:
        """
        Yield models immediately after each awaited save operation.

        Parameters
        ----------
        **overrides : typing.Any
            Final attributes, copied before the first persistence await.

        Yields
        ------
        ``TModel``
            One successfully persisted model per iteration.

        Raises
        ------
        orionis.orm.factories.FactoryPersistenceException
            If a model event vetoes saving.

        Notes
        -----
        Use ``contextlib.aclosing`` when stopping iteration early.
        """
        stream = self.iterMake(**overrides)
        try:
            for model in stream:
                if not await model.save():
                    error_msg = "A model event vetoed factory persistence."
                    raise FactoryPersistenceException(error_msg)
                yield model
        finally:
            stream.close()

    def _ensureIdle(self) -> None:
        """
        Reject reconfiguration or overlapping use of an active factory.

        Raises
        ------
        orionis.orm.factories.FactoryConcurrencyException
            If another operation owns this instance.

        Returns
        -------
        None
            No return value.
        """
        if self._busy:
            error_msg = "Factory is in use; create an instance for each task."
            raise FactoryConcurrencyException(error_msg)

    def _makeOne(self, overrides: dict[str, Any]) -> TModel:
        """
        Merge one definition and construct a model through mass assignment.

        Parameters
        ----------
        overrides : dict of str ``to`` typing.Any
            Detached explicit attributes for the current operation.

        Returns
        -------
        ``TModel``
            New model with normal casts and mutators applied.
        """
        attributes = copy_attributes(self.definition(), "definition()")
        for state in self._states:
            if callable(state):
                values = copy_attributes(state(deepcopy(attributes)), "State")
            else:
                values = deepcopy(state)
            attributes.update(values)
        if self._sequence is not None:
            index = self._sequence_index
            self._sequence_index += 1
            attributes.update(self._sequence.resolve(index))
        if overrides:
            attributes.update(deepcopy(overrides))
        return self._model(attributes)
