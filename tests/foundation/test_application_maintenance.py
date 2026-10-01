from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Lock
from orionis.foundation.application import Application
from orionis.test import TestCase

class _RuntimeApplication:
    """Expose the runtime members used by Application.underMaintenance."""

    __slots__ = (
        "_Application__booted",
        "_Application__maintenance_cache",
        "_Application__maintenance_lock",
        "_Application__maintenance_marker",
        "base_path",
        "maintenance",
    )

    def __init__(
        self,
        base_path: Path,
        *,
        maintenance: bool = False,
    ) -> None:
        """Store the test root and configured maintenance value.

        Parameters
        ----------
        base_path : Path
            Temporary root for framework storage.
        maintenance : bool, optional
            Configured maintenance state when no runtime marker exists.

        Returns
        -------
        None
            Prepare the runtime application double.
        """
        self._Application__booted = True
        self.base_path = base_path
        self.maintenance = maintenance
        self._Application__maintenance_cache = (0, False)
        self._Application__maintenance_lock = Lock()
        self._Application__maintenance_marker = (
            self.path("storage_framework") / "maintenance"
        )

    def path(self, key: str) -> Path:
        """Return the framework storage path used by the runtime marker.

        Parameters
        ----------
        key : str
            Application path key requested by the application method.

        Returns
        -------
        Path
            Framework storage directory below the temporary root.
        """
        if key != "storage_framework":
            raise KeyError(key)
        return self.base_path / "storage" / "framework"

    def config(self, key: str) -> bool:
        """Return the test application's configured maintenance value.

        Parameters
        ----------
        key : str
            Configuration key requested by the application method.

        Returns
        -------
        bool
            Configured application maintenance value.
        """
        if key != "app.maintenance":
            raise KeyError(key)
        return self.maintenance

class _ReadableMarker:
    """Record reads of a maintenance marker and simulate a read error."""

    __slots__ = ("error", "path", "read_count", "read_lock")

    def __init__(self, path: Path) -> None:
        """Store the marker path and initialize its read counter.

        Parameters
        ----------
        path : Path
            Marker file to read.
        """
        self.path = path
        self.error = False
        self.read_count = 0
        self.read_lock = Lock()

    def read_text(self, *, encoding: str) -> str:
        """Read the marker or raise the configured filesystem error.

        Parameters
        ----------
        encoding : str
            Text encoding requested by the application.

        Returns
        -------
        str
            Contents of the maintenance marker.
        """
        with self.read_lock:
            self.read_count += 1
        if self.error:
            raise PermissionError
        return self.path.read_text(encoding=encoding)

class TestApplicationMaintenance(TestCase):
    """Verify runtime maintenance state follows its shared state file."""

    def testUsesConfigurationWhenNoRuntimeStateExists(self) -> None:
        """Fall back to configured maintenance state before a CLI transition.

        Returns
        -------
        None
            Assertions verify the configured fallback state.
        """
        with TemporaryDirectory() as temporary:
            app = _RuntimeApplication(Path(temporary), maintenance=True)

            self.assertTrue(Application.underMaintenance(app))

    def testReadsDownAndUpTransitionsFromTheRuntimeStateFile(self) -> None:
        """Observe state changes written after the application has booted.

        Returns
        -------
        None
            Assertions verify down and up states override boot configuration.
        """
        with TemporaryDirectory() as temporary:
            app = _RuntimeApplication(Path(temporary), maintenance=True)
            marker = app.path("storage_framework") / "maintenance"
            marker.parent.mkdir(parents=True)

            marker.write_text("down", encoding="utf-8")
            self.assertTrue(Application.underMaintenance(app))

            marker.write_text("up", encoding="utf-8")
            self.assertTrue(Application.underMaintenance(app))

            app._Application__maintenance_cache = (0, True)
            self.assertFalse(Application.underMaintenance(app))

    def testReadsSharedMarkerOnlyOncePerRefreshInterval(self) -> None:
        """Reuse a state snapshot for requests within one refresh interval.

        Returns
        -------
        None
            Assertions verify marker reads and refresh timing.
        """
        with TemporaryDirectory() as temporary:
            app = _RuntimeApplication(Path(temporary))
            marker = app.path("storage_framework") / "maintenance"
            marker.parent.mkdir(parents=True)
            marker.write_text("up", encoding="utf-8")
            reader = _ReadableMarker(marker)
            app._Application__maintenance_marker = reader

            for _ in range(1_000):
                self.assertFalse(Application.underMaintenance(app))
            self.assertEqual(reader.read_count, 1)

            app._Application__maintenance_cache = (0, False)
            self.assertFalse(Application.underMaintenance(app))
            self.assertEqual(reader.read_count, 2)

    def testReadErrorsFailClosedUntilNextRefresh(self) -> None:
        """Serve maintenance responses during a transient marker read error.

        Returns
        -------
        None
            Assertions verify fail-closed behavior and recovery timing.
        """
        with TemporaryDirectory() as temporary:
            app = _RuntimeApplication(Path(temporary))
            reader = _ReadableMarker(app.path("storage_framework") / "maintenance")
            reader.error = True
            app._Application__maintenance_marker = reader

            self.assertTrue(Application.underMaintenance(app))
            reader.error = False
            self.assertTrue(Application.underMaintenance(app))
            app._Application__maintenance_cache = (0, True)
            self.assertFalse(Application.underMaintenance(app))

    def testInvalidUtf8MarkerFailsClosed(self) -> None:
        """Keep the application in maintenance mode for an undecodable marker.

        Returns
        -------
        None
            Assertions verify that malformed marker bytes do not escape.
        """
        with TemporaryDirectory() as temporary:
            app = _RuntimeApplication(Path(temporary))
            marker = app.path("storage_framework") / "maintenance"
            marker.parent.mkdir(parents=True)
            marker.write_bytes(b"\xff")

            self.assertTrue(Application.underMaintenance(app))

    def testConcurrentRefreshReadsSharedMarkerOnce(self) -> None:
        """Share one marker read across concurrent calls after expiry.

        Returns
        -------
        None
            Assertions verify all callers receive the same refreshed state.
        """
        with TemporaryDirectory() as temporary:
            app = _RuntimeApplication(Path(temporary))
            marker = app.path("storage_framework") / "maintenance"
            marker.parent.mkdir(parents=True)
            marker.write_text("down", encoding="utf-8")
            barrier = Barrier(8)
            reader = _ReadableMarker(marker)
            app._Application__maintenance_marker = reader

            def read_state(_index: int) -> bool:
                """Wait for peers and read the shared application state.

                Parameters
                ----------
                _index : int
                    Worker index supplied by the executor.

                Returns
                -------
                bool
                    Maintenance state returned to this worker.
                """
                barrier.wait()
                return Application.underMaintenance(app)

            with ThreadPoolExecutor(max_workers=8) as executor:
                self.assertEqual(list(executor.map(read_state, range(8))), [True] * 8)
                self.assertEqual(reader.read_count, 1)
