import importlib
from typing import TYPE_CHECKING
from uuid import UUID
from orionis.auth.contracts.authenticatable import IAuthenticatable
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.exceptions import IdentityProviderException
from orionis.foundation.contracts.application import IApplication
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.orm.schema.types.column_type import ColumnType

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.orm.model import Model

# Fallbacks applied when the configuration section is absent.
_DEFAULT_MODEL: str = "app.models.user.User"
_DEFAULT_USERNAME: str = "email"
_DEFAULT_PASSWORD: str = "password"  # noqa: S105
_INTEGER_KEY_TYPES = frozenset({
    ColumnType.BIG_INTEGER, ColumnType.INTEGER, ColumnType.SMALL_INTEGER,
    ColumnType.BIGINT, ColumnType.INT, ColumnType.SMALLINT,
})
_MAX_IDENTIFIER_LENGTH = 255
_MAX_PASSWORD_LENGTH = 4096

class ModelIdentityProvider(IIdentityProvider):
    """Resolve identities from an Orionis model declared in configuration.

    The model class is never imported at module load time. Its dotted
    path travels through ``config/auth.py``, which keeps the framework
    free of any dependency on application code and allows any model to
    play the role of the authenticatable identity.

    Concurrency
    -----------
    The provider is stateless apart from the memoised model class, which
    is a pure function of the configuration. A concurrent first import
    may resolve the same class twice with no observable difference.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = (
        "__hasher",
        "__model",
        "__model_path",
        "__username_field",
    )

    def __init__(self, app: IApplication, hasher: IHashManager) -> None:
        """Initialise the provider from the authentication configuration.

        Parameters
        ----------
        app : IApplication
            Application exposing the ``auth.identity`` configuration.
        hasher : IHashManager
            Hashing service used to verify submitted passwords.

        Returns
        -------
        None
            The model class stays unresolved until the first lookup.
        """
        self.__model_path: str = (
            app.config("auth.identity.model") or _DEFAULT_MODEL
        )
        self.__username_field: str = (
            app.config("auth.identity.username") or _DEFAULT_USERNAME
        )
        self.__hasher = hasher
        self.__model: type[Model] | None = None

    def model(self) -> type[Model]:
        """Return the model class backing the authenticated identity.

        Returns
        -------
        type[Model]
            Model class resolved from the configured dotted path.

        Raises
        ------
        IdentityProviderException
            When the path cannot be imported or the resolved class does
            not implement :class:`IAuthenticatable`.
        """
        resolved = self.__model
        if resolved is not None:
            return resolved

        module_path, _, class_name = self.__model_path.rpartition(".")
        try:
            module = importlib.import_module(module_path)
            resolved = getattr(module, class_name)
        except (ImportError, AttributeError, ValueError) as exc:
            error_msg = (
                f"Unable to import the authenticatable model "
                f"'{self.__model_path}'."
            )
            raise IdentityProviderException(error_msg) from exc

        if not isinstance(resolved, type) or not issubclass(
            resolved, IAuthenticatable,
        ):
            error_msg = (
                f"The authenticatable model '{self.__model_path}' must "
                f"implement IAuthenticatable."
            )
            raise IdentityProviderException(error_msg)

        self.__model = resolved
        return resolved

    async def retrieveById(self, identifier: object) -> IAuthenticatable | None:
        """Retrieve an identity by its primary key.

        Parameters
        ----------
        identifier : object
            Value previously returned by ``getAuthIdentifier()``.

        Returns
        -------
        IAuthenticatable | None
            Matching identity, or ``None`` when it no longer exists.
        """
        if identifier is None:
            return None

        model = self.model()
        primary_key = model.__meta__.primary_key
        identifier = self.__normalizeIdentifier(identifier)
        if identifier is None:
            return None
        return await model.query().where(primary_key, identifier).first()

    def __normalizeIdentifier(self, identifier: object) -> object | None:
        """Restore a stored scalar key to the model column's native type.

        Parameters
        ----------
        identifier : object
            Value obtained from a session or a token owner column.

        Returns
        -------
        object | None
            Native integer, UUID or string, or None for an invalid key.
        """
        if (
            not isinstance(identifier, (int, str, UUID))
            or isinstance(identifier, bool)
            or not str(identifier)
            or len(str(identifier)) > _MAX_IDENTIFIER_LENGTH
        ):
            return None
        metadata = self.model().__meta__
        column = metadata.columns[metadata.primary_key]
        try:
            if column.column_type in _INTEGER_KEY_TYPES:
                return int(identifier)
            if column.column_type is ColumnType.UUID:
                identifier = UUID(str(identifier))
                return identifier if column.as_uuid else str(identifier)
        except (ValueError, TypeError):
            return None
        return str(identifier)

    async def retrieveByCredentials(
        self,
        credentials: Mapping[str, object],
    ) -> IAuthenticatable | None:
        """Retrieve an identity matching the public credential.

        Parameters
        ----------
        credentials : Mapping[str, object]
            Submitted credentials. Only the configured username field is
            read; the secret is deliberately ignored here.

        Returns
        -------
        IAuthenticatable | None
            Matching identity, or ``None`` when no identity matches.
        """
        username = credentials.get(self.__username_field)
        if not isinstance(username, str) or not username:
            return None

        model = self.model()
        return await model.query().where(self.__username_field, username).first()

    async def validateCredentials(
        self,
        identity: IAuthenticatable | None,
        credentials: Mapping[str, object],
    ) -> bool:
        """Verify the submitted password against the stored hash.

        The hashing module burns its cost on a worker thread, so the event
        loop stays free. Unknown identities still perform password hashing
        work. This reduces account enumeration signals without promising
        exact timing equality across hash algorithms or historical cost
        settings. Backend input errors are treated as invalid credentials.

        Parameters
        ----------
        identity : IAuthenticatable | None
            Identity returned by ``retrieveByCredentials()``.
        credentials : Mapping[str, object]
            Submitted credentials.

        Returns
        -------
        bool
            True only when the password matches the stored hash.
        """
        password = credentials.get(_DEFAULT_PASSWORD)
        if (
            not isinstance(password, str)
            or not password
            or len(password) > _MAX_PASSWORD_LENGTH
        ):
            return False

        try:
            stored = identity.getAuthPassword() if identity is not None else ""
            if not stored:
                await self.__hasher.make(password)
                return False
            return await self.__hasher.check(password, stored)
        except ValueError:
            return False
