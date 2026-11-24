from unittest import TestSuite
from orionis.container.facades.facade import Facade
from orionis.test.contracts.engine import ITestingEngine
from orionis.test.entities.result import TestResult

class Test(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[ITestingEngine]: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> ITestingEngine: ...

    @classmethod
    def setVerbosity(cls, verbosity: int) -> ITestingEngine: ...

    @classmethod
    def setFailFast(cls, *, fail_fast: bool) -> ITestingEngine: ...

    @classmethod
    def setStartDir(cls, start_dir: str) -> ITestingEngine: ...

    @classmethod
    def setFilePattern(cls, file_pattern: str) -> ITestingEngine: ...

    @classmethod
    def setMethodPattern(cls, method_pattern: str) -> ITestingEngine: ...

    @classmethod
    def withoutPanel(cls) -> ITestingEngine: ...

    @classmethod
    def discover(cls) -> TestSuite: ...

    @classmethod
    async def run(cls) -> list[TestResult]: ...
