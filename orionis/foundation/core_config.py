from dataclasses import asdict
from types import MappingProxyType
from orionis.foundation.config.app.entities.app import App
from orionis.foundation.config.scheduler.entities.scheduler import Scheduler
from orionis.foundation.config.auth.entities.auth import Auth
from orionis.foundation.config.cache.entities.cache import Cache
from orionis.foundation.config.database.entities.database import Database
from orionis.foundation.config.filesystems.entitites.filesystems import Filesystems
from orionis.foundation.config.hashing.entities.hashing import Hashing
from orionis.foundation.config.http.entitites.http import HTTP
from orionis.foundation.config.logging.entities.logging import Logging
from orionis.foundation.config.mail.entities.mail import Mail
from orionis.foundation.config.queue.entities.queue import Queue
from orionis.foundation.config.session.entities.session import Session
from orionis.foundation.config.testing.entities.testing import Testing
from orionis.foundation.config.view.entities.view import View

def get_core_config_mapping() -> MappingProxyType:
    """
    Return a read-only mapping of core configuration entities.

    Returns
    -------
    MappingProxyType
        An immutable mapping containing the default configuration for each
        core entity.
    """
    # Build the mapping of configuration entities using asdict for serialization.
    return MappingProxyType({
        "app": asdict(App()),
        "auth": asdict(Auth()),
        "cache": asdict(Cache()),
        "database": asdict(Database()),
        "filesystems": asdict(Filesystems()),
        "hashing": asdict(Hashing()),
        "http": asdict(HTTP()),
        "logging": asdict(Logging()),
        "mail": asdict(Mail()),
        "queue": asdict(Queue()),
        "scheduler": asdict(Scheduler()),
        "session": asdict(Session()),
        "testing": asdict(Testing()),
        "view": asdict(View()),
    })

CORE_CONFIG: MappingProxyType = get_core_config_mapping()
