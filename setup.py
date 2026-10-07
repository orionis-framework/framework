from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildPy(build_py):

    def run(self) -> None:
        """
        Build Python modules and include the framework's project manifest.

        Returns
        -------
        None
            Populate the build directory with modules and the canonical manifest.
        """
        super().run()
        if self.editable_mode:
            return
        self.copy_file(
            str(Path(__file__).resolve().with_name("pyproject.toml")),
            str(Path(self.build_lib) / "orionis" / "pyproject.toml"),
        )

setup(cmdclass={"build_py": BuildPy})
