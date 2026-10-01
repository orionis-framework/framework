import keyword
import re
from pathlib import Path
from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.make._base import MakeStubCommand
from orionis.foundation.contracts.application import IApplication  # noqa: TC001

_NAME_RE: re.Pattern[str] = re.compile(r"[A-Za-z]\w*", re.ASCII)
_ACRONYM_RE: re.Pattern[str] = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_RE: re.Pattern[str] = re.compile(r"([a-z0-9])([A-Z])")

def _parse_name(name: str) -> tuple[tuple[str, ...], str]:
    """
    Parse a relative Python name into module components and a class name.

    Parameters
    ----------
    name : str
        Class or snake case file name, optionally prefixed by directories.

    Returns
    -------
    tuple[tuple[str, ...], str]
        Snake case module components and the corresponding class name.

    Raises
    ------
    TypeError
        If the supplied name is not a string.
    ValueError
        If the name contains invalid or unsafe Python module components.
    """
    if not isinstance(name, str):
        error_msg = "Factory and model names must be strings."
        raise TypeError(error_msg)
    parts = name.replace("\\", "/").removesuffix(".py").split("/")
    if any(_NAME_RE.fullmatch(part) is None for part in parts):
        error_msg = f"Invalid Python name '{name}'."
        raise ValueError(error_msg)
    modules = tuple(
        _CAMEL_RE.sub(r"\1_\2", _ACRONYM_RE.sub(r"\1_\2", part)).lower()
        for part in parts
    )
    if any(keyword.iskeyword(part) for part in modules):
        error_msg = f"Invalid Python module name '{name}'."
        raise ValueError(error_msg)
    class_name = "".join(
        word[0].upper() + word[1:] for word in parts[-1].split("_") if word
    )
    if keyword.iskeyword(class_name):
        error_msg = f"Invalid Python class name '{class_name}'."
        raise ValueError(error_msg)
    return modules, class_name


class MakeFactory(MakeStubCommand):
    """Generate an explicitly imported factory for an application model."""

    __slots__ = ()

    timestamps: bool = False
    signature: str = "make:factory"
    description: str = "Creates a model factory in the database directory."
    template_name: str = "factory"
    path_key: str = "database_factories"
    success_label: str = "Model factory"
    postfix: str | None = "Factory"
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The factory class or file name, for example UserFactory.",
        ),
        Argument(
            name_or_flags=["--model", "-m"],
            type_=str,
            required=False,
            help="Model name below app/models, for example User or sales/Order.",
        ),
    ]

    def createFiles(
        self,
        app: IApplication,
        name: str,
    ) -> tuple[tuple[str, str], ...]:
        """
        Create a factory using the configured model and factory directories.

        Parameters
        ----------
        app : IApplication
            Application that resolves the destination and model paths.
        name : str
            Factory class or file name, with optional nested directories.

        Returns
        -------
        tuple[tuple[str, str], ...]
            Success label and the generated application-relative path.

        Raises
        ------
        TypeError
            If the model directory is not configured as a path.
        ValueError
            If the names or model package cannot form valid Python imports.
        """
        factory_parts, factory_class = _parse_name(name)
        if not factory_class.endswith("Factory"):
            factory_class += "Factory"
        model_name = self.getArgument("model")
        if model_name is None:
            model_name = "/".join((
                *factory_parts[:-1],
                factory_class.removesuffix("Factory"),
            ))
        model_parts, model_class = _parse_name(model_name)
        model_directory = app.path("app_models")
        if not isinstance(model_directory, Path):
            error_msg = "Application path 'app_models' is not configured."
            raise TypeError(error_msg)
        package_parts = model_directory.relative_to(app.basePath).parts
        if any(
            not part.isidentifier() or keyword.iskeyword(part)
            for part in package_parts
        ):
            error_msg = "The configured models path is not a Python package."
            raise ValueError(error_msg)
        file_path = self.createFile(
            app,
            "/".join(factory_parts),
            replacements={
                "factory_class": factory_class,
                "model_class": model_class,
                "model_module": ".".join((*package_parts, *model_parts)),
            },
        )
        return ((self.success_label, file_path),)
