from orionis.console.debug.contracts.dumper import IDumper
from orionis.container.facades.facade import Facade

class Debug(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> str: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IDumper: ...

    @classmethod
    def dd(
        cls,
        *args: object,
        show_types: bool = False,
        show_index: bool = False,
        expand_all: bool = True,
        max_depth: int | None = None,
        module_path: str | None = None,
        line_number: int | None = None,
        redirect_output: bool = False,
        insert_line: bool = False,
    ) -> None: ...

    @classmethod
    def dump(
        cls,
        *args: object,
        show_types: bool = False,
        show_index: bool = False,
        expand_all: bool = True,
        max_depth: int | None = None,
        module_path: str | None = None,
        line_number: int | None = None,
        redirect_output: bool = False,
        insert_line: bool = False,
    ) -> None: ...
