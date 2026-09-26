from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.app.entities.app import App
from orionis.foundation.config.auth.entities.auth import Auth
from orionis.foundation.config.cache.entities.cache import Cache
from orionis.foundation.config.database.entities.database import Database
from orionis.foundation.config.filesystems.entitites.filesystems import Filesystems
from orionis.foundation.config.hashing.entities.hashing import Hashing
from orionis.foundation.config.http.entitites.http import HTTP
from orionis.foundation.config.logging.entities.logging import Logging
from orionis.foundation.config.mail.entities.mail import Mail
from orionis.foundation.config.queue.entities.queue import Queue
from orionis.foundation.config.scheduler.entities.scheduler import Scheduler
from orionis.foundation.config.session.entities.session import Session
from orionis.foundation.config.testing.entities.testing import Testing
from orionis.foundation.config.view.entities.view import View
from orionis.support.entities.base import BaseEntity

# Dispatch table: maps each field name to its expected concrete type.
_SECTION_MAP: tuple[tuple[str, type], ...] = (
    ("app", App),
    ("auth", Auth),
    ("cache", Cache),
    ("database", Database),
    ("filesystems", Filesystems),
    ("http", HTTP),
    ("logging", Logging),
    ("mail", Mail),
    ("queue", Queue),
    ("session", Session),
    ("hashing", Hashing),
    ("scheduler", Scheduler),
    ("view", View),
    ("testing", Testing),
)

@dataclass(frozen=True, kw_only=True)
class Configuration(BaseEntity):
    """
    Represent the main configuration for Orionis Framework startup.

    Parameters
    ----------
    app : App | dict, optional
        Application configuration settings.
    auth : Auth | dict, optional
        Authentication configuration settings.
    cache : Cache | dict, optional
        Cache configuration settings.
    database : Database | dict, optional
        Database configuration settings.
    filesystems : Filesystems | dict, optional
        Filesystem configuration settings.
    logging : Logging | dict, optional
        Logging configuration settings.
    mail : Mail | dict, optional
        Mail configuration settings.
    hashing : Hashing | dict, optional
        Password hashing configuration settings.
    scheduler : Scheduler | dict, optional
        Scheduled task configuration settings.
    view : View | dict, optional
        Template rendering configuration settings.
    http : HTTP | dict, optional
        HTTP configuration settings.
    queue : Queue | dict, optional
        Queue configuration settings.
    session : Session | dict, optional
        Session configuration settings.
    testing : Testing | dict, optional
        Testing configuration settings.

    Raises
    ------
    TypeError
        If any configuration section is initialized with an invalid type.

    Returns
    -------
    None
        This class does not return a value upon instantiation.
    """

    app: App | dict = field(
        default_factory=App,
        metadata={
            "description": "Application configuration settings.",
            "default": lambda: App().toDict(),
        },
    )

    auth: Auth | dict = field(
        default_factory=Auth,
        metadata={
            "description": "Authentication configuration settings.",
            "default": lambda: Auth().toDict(),
        },
    )

    cache: Cache | dict = field(
        default_factory=Cache,
        metadata={
            "description": "Cache configuration settings.",
            "default": lambda: Cache().toDict(),
        },
    )

    database: Database | dict = field(
        default_factory=Database,
        metadata={
            "description": "Database configuration settings.",
            "default": lambda: Database().toDict(),
        },
    )

    filesystems: Filesystems | dict = field(
        default_factory=Filesystems,
        metadata={
            "description": "Filesystem configuration settings.",
            "default": lambda: Filesystems().toDict(),
        },
    )

    http: HTTP | dict = field(
        default_factory=HTTP,
        metadata={
            "description": "HTTP configuration settings.",
            "default": lambda: HTTP().toDict(),
        },
    )

    logging: Logging | dict = field(
        default_factory=Logging,
        metadata={
            "description": "Logging configuration settings.",
            "default": lambda: Logging().toDict(),
        },
    )

    mail: Mail | dict = field(
        default_factory=Mail,
        metadata={
            "description": "Mail configuration settings.",
            "default": lambda: Mail().toDict(),
        },
    )

    queue: Queue | dict = field(
        default_factory=Queue,
        metadata={
            "description": "Queue configuration settings.",
            "default": lambda: Queue().toDict(),
        },
    )

    session: Session | dict = field(
        default_factory=Session,
        metadata={
            "description": "Session configuration settings.",
            "default": lambda: Session().toDict(),
        },
    )

    testing: Testing | dict = field(
        default_factory=Testing,
        metadata={
            "description": "Testing configuration settings.",
            "default": lambda: Testing().toDict(),
        },
    )

    hashing: Hashing | dict = field(default_factory=Hashing)

    scheduler: Scheduler | dict = field(default_factory=Scheduler)

    view: View | dict = field(default_factory=View)

    def __post_init__(self) -> None:
        """
        Validate and convert configuration attributes to their entity types.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Call parent post-init for base validation
        super().__post_init__()

        # Single dispatch to validate and convert each section attribute
        for _attr, _cls in _SECTION_MAP:
            _val = getattr(self, _attr)
            if isinstance(_val, dict):
                object.__setattr__(self, _attr, _cls(**_val))
            elif not isinstance(_val, _cls):
                error_msg = (
                    f"Invalid type for '{_attr}': expected {_cls.__name__} or dict, "
                    f"got {type(_val).__name__}"
                )
                raise TypeError(error_msg)
