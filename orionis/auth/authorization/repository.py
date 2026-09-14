from typing import TYPE_CHECKING
from orionis.auth.concerns.functions import authorizable_key
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.exceptions import AuthException
from orionis.orm.contracts.query_builder import IQueryBuilder

if TYPE_CHECKING:
    from orionis.auth.contracts.authorizable import IAuthorizable
    from orionis.orm.contracts.raw_builder import IRawQueryBuilder

# Tables shipped by the framework migrations. They follow the polymorphic
# layout so any model can own permissions and roles.
_PERMISSIONS_TABLE: str = "permissions"
_ROLES_TABLE: str = "roles"
_MODEL_PERMISSIONS_TABLE: str = "model_has_permissions"
_MODEL_ROLES_TABLE: str = "model_has_roles"
_ROLE_PERMISSIONS_TABLE: str = "role_has_permissions"

# Column names reused across the three queries below.
_MODEL_TYPE: str = "model_type"
_MODEL_ID: str = "model_id"
_ROLE_ID: str = "role_id"
_PERMISSION_ID: str = "permission_id"

class DatabasePermissionRepository(IPermissionRepository):
    """Load permissions and roles from the framework authorization tables.

    Roles, direct permissions and role permissions are resolved in one
    UNION statement, once per request. No intermediate role-ID list can
    become stale between separate reads. Later checks use the snapshot.

    Concurrency
    -----------
    The repository is stateless and safe to register as a singleton. It
    only issues read queries, so concurrent calls never interfere.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("__db",)

    def __init__(self, db: IQueryBuilder) -> None:
        """Initialise the repository with the model-less query gateway.

        Parameters
        ----------
        db : IQueryBuilder
            Gateway used to build queries over the authorization tables.

        Returns
        -------
        None
            The repository keeps only the injected gateway.
        """
        self.__db = db

    async def loadFor(
        self,
        authorizable: IAuthorizable,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Load the permissions and roles owned by an identity.

        Parameters
        ----------
        authorizable : IAuthorizable
            Identity whose authorization must be resolved.

        Returns
        -------
        tuple[frozenset[str], frozenset[str]]
            Effective permission names first, role names second.
        """
        try:
            model_type, model_id = authorizable_key(authorizable)
        except AuthException:
            return frozenset(), frozenset()

        rows = await (
            self.__rolesOf(model_type, model_id)
            .union(self.__directPermissionsOf(model_type, model_id))
            .union(self.__rolePermissionsOf(model_type, model_id))
            .get()
        )
        permissions = frozenset(
            row["name"] for row in rows if row["kind"] == "permission"
        )
        roles = frozenset(row["name"] for row in rows if row["kind"] == "role")
        return permissions, roles

    def __rolesOf(
        self,
        model_type: str,
        model_id: object,
    ) -> IRawQueryBuilder:
        """Build the role arm of the authorization statement.

        Parameters
        ----------
        model_type : str
            Polymorphic type stored in the pivot table.
        model_id : object
            Identifier stored in the pivot table.

        Returns
        -------
        IRawQueryBuilder
            Query exposing role names tagged with their authorization kind.
        """
        return (
            self.__db.table(_ROLES_TABLE)
            .select(f"{_ROLES_TABLE}.name")
            .selectRaw("'role'", alias="kind")
            .join(
                _MODEL_ROLES_TABLE,
                f"{_MODEL_ROLES_TABLE}.{_ROLE_ID}",
                "=",
                f"{_ROLES_TABLE}.id",
            )
            .where(f"{_MODEL_ROLES_TABLE}.{_MODEL_TYPE}", model_type)
            .where(f"{_MODEL_ROLES_TABLE}.{_MODEL_ID}", model_id)
        )

    def __directPermissionsOf(
        self,
        model_type: str,
        model_id: object,
    ) -> IRawQueryBuilder:
        """Build the direct-permission arm of the authorization statement.

        Parameters
        ----------
        model_type : str
            Polymorphic type stored in the pivot table.
        model_id : object
            Identifier stored in the pivot table.

        Returns
        -------
        IRawQueryBuilder
            Query exposing direct permission names and their kind.
        """
        return (
            self.__db.table(_PERMISSIONS_TABLE)
            .select(f"{_PERMISSIONS_TABLE}.name")
            .selectRaw("'permission'", alias="kind")
            .join(
                _MODEL_PERMISSIONS_TABLE,
                f"{_MODEL_PERMISSIONS_TABLE}.{_PERMISSION_ID}",
                "=",
                f"{_PERMISSIONS_TABLE}.id",
            )
            .where(f"{_MODEL_PERMISSIONS_TABLE}.{_MODEL_TYPE}", model_type)
            .where(f"{_MODEL_PERMISSIONS_TABLE}.{_MODEL_ID}", model_id)
        )

    def __rolePermissionsOf(
        self,
        model_type: str,
        model_id: object,
    ) -> IRawQueryBuilder:
        """Build inherited permissions constrained to the current owner's roles.

        Parameters
        ----------
        model_type : str
            Stable polymorphic owner type.
        model_id : object
            Canonical identifier of the owner.

        Returns
        -------
        IRawQueryBuilder
            Query exposing permissions from roles attached in this statement.
        """
        return (
            self.__db.table(_PERMISSIONS_TABLE)
            .select(f"{_PERMISSIONS_TABLE}.name")
            .selectRaw("'permission'", alias="kind")
            .join(
                _ROLE_PERMISSIONS_TABLE,
                f"{_ROLE_PERMISSIONS_TABLE}.{_PERMISSION_ID}",
                "=",
                f"{_PERMISSIONS_TABLE}.id",
            )
            .join(
                _MODEL_ROLES_TABLE,
                f"{_MODEL_ROLES_TABLE}.{_ROLE_ID}",
                "=",
                f"{_ROLE_PERMISSIONS_TABLE}.{_ROLE_ID}",
            )
            .where(f"{_MODEL_ROLES_TABLE}.{_MODEL_TYPE}", model_type)
            .where(f"{_MODEL_ROLES_TABLE}.{_MODEL_ID}", model_id)
        )
