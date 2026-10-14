import json
import subprocess
import sys
from pathlib import Path
from orionis.test import TestCase

_ROOT = Path(__file__).resolve().parents[2]

# ruff: noqa: S603

def _probe(source: str) -> dict[str, object]:
    """Run an import probe with a fresh module cache.

    Parameters
    ----------
    source : str
        Python statements that print a JSON object to standard output.

    Returns
    -------
    dict[str, object]
        Decoded result from the child interpreter.
    """
    result = subprocess.run(
        [sys.executable, "-B", "-c", source], cwd=_ROOT,
        capture_output=True, check=True, text=True, encoding="utf-8", timeout=60,
    )
    return json.loads(result.stdout)

class TestContainerLazyImports(TestCase):
    """Exercise cold imports and runtime annotations used by the container."""

    def testContainerDoesNotLoadHTTPOrSchemaValidation(self) -> None:
        """Verify container construction leaves HTTP and validators unloaded.

        Returns
        -------
        None
            Assert that unrelated implementations remain unloaded.
        """
        result = _probe(
            "import json, sys\n"
            "from orionis.container.container import Container\n"
            "Container()\n"
            "excluded = ('orionis.http.request', 'orionis.schemas.validator',\n"
            "    'orionis.http.payload.parsers', 'sqlalchemy', 'rich')\n"
            "print(json.dumps({'loaded': [name for name in excluded\n"
            "    if name in sys.modules]}))\n",
        )
        self.assertEqual(result["loaded"], [])

    def testPublicContractsResolveThroughFutureAnnotations(self) -> None:
        """Verify contract injection with postponed and unresolved annotations.

        Returns
        -------
        None
            Assert contract identity and application injection.
        """
        result = _probe(
            "from __future__ import annotations\n"
            "import asyncio, json\n"
            "from orionis.container.container import Container\n"
            "from orionis import Application, IApplication\n"
            "from orionis.foundation.contracts.application import (\n"
            "    IApplication as Direct)\n"
            "class Service:\n"
            "    def __init__(self, app: IApplication) -> MissingReturn:\n"
            '        """Store the injected application.\n'
            "\n"
            "        Parameters\n"
            "        ----------\n"
            "        app : IApplication\n"
            "            Application supplied by the container.\n"
            "\n"
            "        Returns\n"
            "        -------\n"
            "        None\n"
            "            Initialize the service.\n"
            '        """\n'
            "        self.app = app\n"
            "class IsolatedContainer(Container):\n"
            "    pass\n"
            "async def check():\n"
            '    """Verify public contract injection.\n'
            "\n"
            "    Returns\n"
            "    -------\n"
            "    None\n"
            "        Print contract identity and injection results as JSON.\n"
            '    """\n'
            "    container = IsolatedContainer()\n"
            "    app = Application()\n"
            "    container.instance(IApplication, app)\n"
            "    service = await container.make(Service)\n"
            "    print(json.dumps({'same': IApplication is Direct,\n"
            "        'injected': service.app is app}))\n"
            "asyncio.run(check())\n",
        )
        self.assertTrue(result["same"])
        self.assertTrue(result["injected"])

    def testUniqueRuleDefersDatabaseUntilItHasAValue(self) -> None:
        """Verify empty unique-rule values bypass database imports.

        Returns
        -------
        None
            Assert rule identity, validation results and unloaded backends.
        """
        result = _probe(
            "import asyncio, json, sys\n"
            "from orionis.schemas.rules import Unique\n"
            "from orionis.schemas.rules.unique import Unique as Direct\n"
            "rule = Unique('users', 'name')\n"
            "sync = rule.enforce('name', None, None)\n"
            "async_result = asyncio.run(rule.enforceAsync('name', None, None))\n"
            "excluded = ('orionis.database.connection', 'orionis.orm.resolver',\n"
            "    'orionis.orm.query.raw_builder', 'orionis.aio.loop', 'sqlalchemy')\n"
            "print(json.dumps({'same': Unique is Direct, 'sync': sync,\n"
            "    'async': async_result, 'loaded': [name for name in excluded\n"
            "        if name in sys.modules]}))\n",
        )
        self.assertTrue(result["same"])
        self.assertTrue(result["sync"])
        self.assertTrue(result["async"])
        self.assertEqual(result["loaded"], [])
