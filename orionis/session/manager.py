from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.foundation.config.session.enums.drivers import SessionDriver
from orionis.foundation.config.session.entities.session import Session as SessionConfig
from orionis.foundation.contracts.application import IApplication
from orionis.orm.resolver import ConnectionResolver
from orionis.session.contracts.session import ISession
from orionis.session.entities.record import SessionRecord
from orionis.session.session import Session
from orionis.session.stores.cache import CacheSessionStore
from orionis.session.stores.database import DatabaseSessionStore
from orionis.session.stores.file import FileSessionStore
from orionis.session.stores.memory import MemorySessionStore

if TYPE_CHECKING:
    from pathlib import Path
    from orionis.http.request import Request
    from orionis.http.response import Response
    from orionis.session.contracts.store import ISessionStore

class SessionManager:
    """
    Coordinates the session lifecycle for every HTTP request.

    This class is a **coordinator only**.  It never stores session data,
    never interprets the session payload, and never duplicates logic that
    belongs to ``Session`` or to the backing store.

    Parameters
    ----------
    config : SessionConfig
        Resolved session configuration entity.
    store : ISessionStore
        Pre-built backing-store instance.
    """

    # ruff: noqa: TC001

    __slots__ = (
        "_app",
        "_cookie_domain",
        "_cookie_http_only",
        "_cookie_max_age",
        "_cookie_name",
        "_cookie_partitioned",
        "_cookie_path",
        "_cookie_same_site",
        "_cookie_secure",
        "_lifetime_delta",
        "_store",
    )

    def __init__(
        self,
        app: IApplication,
        cache: ICacheManager,
    ) -> None:
        """
        Initialise the manager, pre-computing all request-invariant values.

        Parameters
        ----------
        app : IApplication
            The application instance.
        cache : ICacheManager
            The application's cache manager, injected so the cache-backed
            store can be built without depending on the ``Cache`` facade's
            pin state.

        Returns
        -------
        None
        """
        self._app = app

        config = SessionConfig(**app.config("session"))

        self._store: ISessionStore = self.__resolveStore(
            base_path=app.basePath,
            config=config,
            cache=cache,
        )
        self._lifetime_delta: timedelta = timedelta(minutes=config.lifetime)
        self._cookie_name: str = config.cookie
        self._cookie_path: str = config.path
        self._cookie_domain: str | None = config.domain
        self._cookie_max_age: int | None = (
            None if config.expire_on_close else config.lifetime * 60
        )
        self._cookie_secure: bool = config.secure
        self._cookie_http_only: bool = config.http_only
        self._cookie_same_site: str = getattr(
            config.same_site, "value", config.same_site,
        )
        self._cookie_partitioned: bool = config.partitioned

    # ── Public API ──────────────────────────────────────────────────────────────

    async def start(self, request: Request) -> Session:
        """
        Restore or create a session for the incoming request.

        Parameters
        ----------
        request : Request
            The incoming HTTP request.

        Returns
        -------
        Session
            An active or blank lazy session, with flash data aged.
        """
        # Read the session ID from the cookie, and restore the session from
        # the backing store.  If the cookie is missing or the record is absent,
        # create a new lazy session.
        session_id: str | None = request.cookies.get(self._cookie_name)
        session = await self.__restore(session_id) if session_id else Session()
        session._ageFlashData()  # noqa: SLF001

        # Register the session in the application container so that it can be
        # injected into any service that needs it.
        self.__register(session)

        # Return the session to the caller so that it can be used directly in
        # the request handler.
        return session

    async def save(self, response: Response, session: Session) -> None:
        """
        Persist the session and set the cookie on *response*.

        No-op when the session was never activated.

        Parameters
        ----------
        response : Response
            Outgoing HTTP response.
        session : Session
            The session returned by ``start()``.

        Returns
        -------
        None
        """
        if not session.started:
            return

        if session.invalidated:
            await self.__invalidateSession(response, session)
            return

        if session.wantsRegenerate:
            await self.__rotateId(session)

        if session.dirty:
            await self.__persist(session)

        self.__setCookie(response, session.id)

    # ── Private helpers ─────────────────────────────────────────────────────────

    def __register(self, session: Session) -> None:
        """
        Register the session in the application container.

        Parameters
        ----------
        session : Session
            The session to register.

        Returns
        -------
        None
        """
        # Bind the request-scoped session under its contract so any service
        # (and the Session facade) can resolve it through the container.
        self._app.instance(ISession, session)

    def __resolveStore(
        self,
        base_path: Path,
        config: SessionConfig,
        cache: ICacheManager,
    ) -> ISessionStore:
        """
        Resolve and return the configured session store implementation.

        Parameters
        ----------
        base_path : Path
            Base project path used to resolve file-store directories.
        config : SessionConfig
            Session configuration containing the selected driver.
        cache : ICacheManager
            The application's cache manager, used by the cache driver.

        Returns
        -------
        ISessionStore
            File-backed store when the file driver is selected; otherwise
            an in-memory store.
        """
        driver = config.driver
        if driver == SessionDriver.FILE:
            return FileSessionStore(directory=base_path / config.files)
        if driver == SessionDriver.CACHE:
            return CacheSessionStore(cache=cache, store=config.cache)
        if driver == SessionDriver.DATABASE:
            return DatabaseSessionStore(
                connection=ConnectionResolver.connection(config.connection),
                table=config.table or "sessions",
            )
        return MemorySessionStore()

    async def __restore(self, session_id: str) -> Session:
        """
        Load a session from the store, or return a blank lazy session.

        The store is trusted to handle expiry: a ``None`` return means
        the record was absent or already expired.

        Parameters
        ----------
        session_id : str
            The identifier read from the session cookie.

        Returns
        -------
        Session
            Restored session, or a blank lazy session on cache miss.
        """
        record: SessionRecord | None = await self._store.read(session_id)
        if record is None:
            return Session()
        return Session(id=record.id, data=record.data, started=True, is_new=False)

    async def __persist(self, session: Session) -> None:
        """
        Write the current session state to the backing store.

        Parameters
        ----------
        session : Session
            The session to persist.  ``session.id`` must not be ``None``.

        Returns
        -------
        None
        """
        await self._store.write(
            SessionRecord(
                id=session.id,  # type: ignore[arg-type]
                data=session.all(),
                expires_at=datetime.now(UTC) + self._lifetime_delta,
            ),
        )
        session._markClean()  # noqa: SLF001

    async def __rotateId(self, session: Session) -> None:
        """
        Replace the session ID, deleting the old record from the store.

        Parameters
        ----------
        session : Session
            The session whose ID is to be rotated.

        Returns
        -------
        None
        """
        old_id = session._rotateId()  # noqa: SLF001
        if old_id is not None:
            await self._store.delete(old_id)

    async def __invalidateSession(
        self,
        response: Response,
        session: Session,
    ) -> None:
        """
        Remove the session record and expire the cookie on *response*.

        Parameters
        ----------
        response : Response
            Response on which the expired cookie is set.
        session : Session
            The session to remove.

        Returns
        -------
        None
        """
        if session.id is not None:
            await self._store.delete(session.id)
        self.__deleteCookie(response)

    def __setCookie(self, response: Response, session_id: str) -> None:
        """
        Attach the session identifier cookie to *response*.

        Parameters
        ----------
        response : Response
            The outgoing response.
        session_id : str
            The session identifier to embed in the cookie value.

        Returns
        -------
        None
        """
        response.setCookie(
            self._cookie_name,
            session_id,
            max_age=self._cookie_max_age,
            path=self._cookie_path,
            domain=self._cookie_domain,
            secure=self._cookie_secure,
            http_only=self._cookie_http_only,
            same_site=self._cookie_same_site,
            partitioned=self._cookie_partitioned,
        )

    def __deleteCookie(self, response: Response) -> None:
        """
        Set an expired cookie to instruct the browser to clear it.

        Parameters
        ----------
        response : Response
            The outgoing response.

        Returns
        -------
        None
        """
        response.deleteCookie(
            self._cookie_name,
            path=self._cookie_path,
            domain=self._cookie_domain,
        )
