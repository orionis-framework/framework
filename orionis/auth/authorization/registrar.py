from typing import TYPE_CHECKING
from orionis.auth.concerns.functions import authorizable_key
from orionis.auth.exceptions import AuthException
from orionis.database.exceptions import QueryException
from orionis.orm.contracts.query_builder import IQueryBuilder

if TYPE_CHECKING:
    from orionis.auth.contracts.authorizable import IAuthorizable

# Tables shipped by the framework migrations.
_PERMISSIONS_TABLE: str = "permissions"
_ROLES_TABLE: str = "roles"
_MODEL_PERMISSIONS_TABLE: str = "model_has_permissions"
_MODEL_ROLES_TABLE: str = "model_has_roles"
_ROLE_PERMISSIONS_TABLE: str = "role_has_permissions"

_MAX_NAME_LENGTH: int = 255

class PermissionRegistrar:
    """
    Create permissions and roles, and attach them to identities.

    Database unique constraints decide concurrent insertions. Duplicate
    recovery uses a transaction or savepoint and verifies that the desired
    row exists before treating the operation as idempotent.

    Concurrency
    -----------
    The registrar is stateless and safe as a singleton. Duplicate inserts
    lose against the primary or unique key and are resolved by reading the
    row that won.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("__db",)

    def __init__(self, db: IQueryBuilder) -> None:
        """
        Initialise the registrar with the model-less query gateway.

        Parameters
        ----------
        db : IQueryBuilder
            Gateway used to build queries over the authorization tables.

        Returns
        -------
        None
            The registrar keeps only the injected gateway.
        """
        self.__db = db

    async def createPermission(self, name: str) -> object:
        """
        Create a permission, or return the existing one.

        Parameters
        ----------
        name : str
            Permission name, such as ``"users.view"``.

        Returns
        -------
        object
            Identifier of the permission row.
        """
        return await self.__firstOrCreate(_PERMISSIONS_TABLE, name)

    async def createRole(self, name: str) -> object:
        """
        Create a role, or return the existing one.

        Parameters
        ----------
        name : str
            Role name, such as ``"admin"``.

        Returns
        -------
        object
            Identifier of the role row.
        """
        return await self.__firstOrCreate(_ROLES_TABLE, name)

    async def givePermissionTo(
        self,
        authorizable: IAuthorizable,
        *permissions: str,
    ) -> None:
        """
        Attach direct permissions to an identity.

        Parameters
        ----------
        authorizable : IAuthorizable
            Identity receiving the permissions.
        *permissions : str
            Permission names. Missing permissions are created.

        Returns
        -------
        None
            The pivot table is updated as a side effect.
        """
        model_type, model_id = authorizable_key(authorizable)
        for permission in permissions:
            permission_id = await self.createPermission(permission)
            await self.__attach(
                _MODEL_PERMISSIONS_TABLE,
                {
                    "permission_id": permission_id,
                    "model_type": model_type,
                    "model_id": model_id,
                },
            )

    async def revokePermissionFrom(
        self,
        authorizable: IAuthorizable,
        *permissions: str,
    ) -> None:
        """
        Detach direct permissions from an identity.

        Parameters
        ----------
        authorizable : IAuthorizable
            Identity losing the permissions.
        *permissions : str
            Permission names. Unknown names are ignored.

        Returns
        -------
        None
            The pivot table is updated as a side effect.
        """
        model_type, model_id = authorizable_key(authorizable)
        for permission in permissions:
            permission_id = await self.__findId(_PERMISSIONS_TABLE, permission)
            if permission_id is None:
                continue
            await (
                self.__db.table(_MODEL_PERMISSIONS_TABLE)
                .where("permission_id", permission_id)
                .where("model_type", model_type)
                .where("model_id", model_id)
                .delete()
            )

    async def assignRole(
        self,
        authorizable: IAuthorizable,
        *roles: str,
    ) -> None:
        """
        Attach roles to an identity.

        Parameters
        ----------
        authorizable : IAuthorizable
            Identity receiving the roles.
        *roles : str
            Role names. Missing roles are created.

        Returns
        -------
        None
            The pivot table is updated as a side effect.
        """
        model_type, model_id = authorizable_key(authorizable)
        for role in roles:
            role_id = await self.createRole(role)
            await self.__attach(
                _MODEL_ROLES_TABLE,
                {
                    "role_id": role_id,
                    "model_type": model_type,
                    "model_id": model_id,
                },
            )

    async def removeRole(
        self,
        authorizable: IAuthorizable,
        *roles: str,
    ) -> None:
        """
        Detach roles from an identity.

        Parameters
        ----------
        authorizable : IAuthorizable
            Identity losing the roles.
        *roles : str
            Role names. Unknown names are ignored.

        Returns
        -------
        None
            The pivot table is updated as a side effect.
        """
        model_type, model_id = authorizable_key(authorizable)
        for role in roles:
            role_id = await self.__findId(_ROLES_TABLE, role)
            if role_id is None:
                continue
            await (
                self.__db.table(_MODEL_ROLES_TABLE)
                .where("role_id", role_id)
                .where("model_type", model_type)
                .where("model_id", model_id)
                .delete()
            )

    async def grantToRole(self, role: str, *permissions: str) -> None:
        """
        Attach permissions to a role.

        Parameters
        ----------
        role : str
            Role name. It is created when missing.
        *permissions : str
            Permission names. Missing permissions are created.

        Returns
        -------
        None
            The pivot table is updated as a side effect.
        """
        role_id = await self.createRole(role)
        for permission in permissions:
            permission_id = await self.createPermission(permission)
            await self.__attach(
                _ROLE_PERMISSIONS_TABLE,
                {"permission_id": permission_id, "role_id": role_id},
            )

    async def revokeFromRole(self, role: str, *permissions: str) -> None:
        """
        Detach permissions from a role.

        Parameters
        ----------
        role : str
            Role name. Unknown roles are ignored.
        *permissions : str
            Permission names. Unknown names are ignored.

        Returns
        -------
        None
            The pivot table is updated as a side effect.
        """
        role_id = await self.__findId(_ROLES_TABLE, role)
        if role_id is None:
            return

        for permission in permissions:
            permission_id = await self.__findId(_PERMISSIONS_TABLE, permission)
            if permission_id is None:
                continue
            await (
                self.__db.table(_ROLE_PERMISSIONS_TABLE)
                .where("permission_id", permission_id)
                .where("role_id", role_id)
                .delete()
            )

    async def __findId(self, table: str, name: str) -> object | None:
        """
        Return the identifier of a named permission or role.

        Parameters
        ----------
        table : str
            Table to search in.
        name : str
            Name of the row.

        Returns
        -------
        object | None
            Identifier of the row, or ``None`` when it does not exist.
        """
        row = await self.__db.table(table).where("name", name).first()
        return None if row is None else row.get("id")

    async def __firstOrCreate(
        self,
        table: str,
        name: str,
    ) -> object:
        """
        Return the identifier of a row, inserting it when missing.

        The unique key decides concurrent insertions. A nested transaction
        rolls back a losing insert before the winning row is read, without
        aborting the caller's transaction.

        Parameters
        ----------
        table : str
            Table holding the named rows.
        name : str
            Name of the row.

        Returns
        -------
        object
            Identifier of the existing or freshly created row.

        Raises
        ------
        QueryException
            When the insert fails for a reason other than a duplicate.
        AuthException
            When the name is empty, padded or longer than the schema permits.
        """
        if (
            not isinstance(name, str)
            or not name
            or name != name.strip()
            or len(name) > _MAX_NAME_LENGTH
        ):
            error_msg = "Authorization names must be non-empty, unpadded strings."
            raise AuthException(error_msg)
        existing = await self.__findId(table, name)
        if existing is not None:
            return existing

        try:
            async with self.__db.transaction():
                result = await self.__db.table(table).insert({"name": name})
        except QueryException:
            # Another caller inserted the very same row first.
            existing = await self.__findId(table, name)
            if existing is None:
                raise
            return existing

        identifier = result.last_insert_id
        if identifier is None:
            identifier = await self.__findId(table, name)
        if identifier is None:
            error_msg = "The authorization row is no longer available."
            raise AuthException(error_msg)
        return identifier

    async def __attach(self, table: str, values: dict[str, object]) -> None:
        """
        Insert a pivot row, ignoring an already existing one.

        Parameters
        ----------
        table : str
            Pivot table receiving the row.
        values : dict[str, object]
            Columns forming the composite primary key.

        Returns
        -------
        None
            The row is inserted, or silently skipped when present.

        Raises
        ------
        QueryException
            If insertion fails and no identical pivot row exists.
        """
        try:
            async with self.__db.transaction():
                await self.__db.table(table).insert(values)
        except QueryException:
            query = self.__db.table(table)
            for column, value in values.items():
                query.where(column, value)
            if not await query.exists():
                raise
