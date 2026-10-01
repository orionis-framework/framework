from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.db._inspection import DatabaseInspector
from orionis.console.commands.db.show import format_bytes
from orionis.console.commands.migrate.base import MigrationCommand
from orionis.database.contracts.connection_manager import IConnectionManager

class DbTableCommand(MigrationCommand):
    """Render a table schema summary."""

    # ruff: noqa: TC001

    timestamps: bool = False
    signature: str = "db:table"
    description: str = "Shows columns, indexes and keys for a database table."
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="table",
            type_=str,
            help="Table name to inspect.",
        ),
        *MigrationCommand.arguments,
    ]

    async def handle(self, conn_manager: IConnectionManager) -> int:
        """
        Inspect the requested table and render its schema details.

        Parameters
        ----------
        conn_manager : IConnectionManager
            Connection manager used to resolve the active database.

        Returns
        -------
        int
            Exit status code for the command: ``0`` on success and ``1`` when the
            table name is invalid.
        """
        inspector = DatabaseInspector(conn_manager, self.targetConnection())
        name = self.getArgument("table")
        try:
            details = await inspector.tableDetails(str(name))
        except ValueError as exc:
            self.error(str(exc), timestamp=False)
            return 1

        self.newLine()
        self.table(
            ["Property", "Value"],
            [
                ["Connection", inspector.name],
                ["Table", details["name"]],
                ["Rows", str(details["rows"])],
                ["Size", format_bytes(details["size"])],
            ],
        )
        self.newLine()
        self.table(
            ["Column", "Type", "Nullable", "Default", "Primary"],
            [
                [
                    str(column["name"]),
                    str(column["type"]),
                    "Yes" if column["nullable"] else "No",
                    str(column["default"]) if column["default"] is not None else "-",
                    "Yes" if column["primary"] else "No",
                ]
                for column in details["columns"]
            ],
        )
        self.newLine()
        if details["indexes"]:
            self.table(
                ["Index", "Columns", "Unique", "Primary"],
                [
                    [
                        str(index["name"]),
                        str(index["columns"]),
                        "Yes" if index["unique"] else "No",
                        "Yes" if index["primary"] else "No",
                    ]
                    for index in details["indexes"]
                ],
            )
        else:
            self.info("No indexes were found.", timestamp=False)

        self.newLine()
        if details["foreign_keys"]:
            self.table(
                ["Foreign key", "Column", "References", "On delete"],
                [
                    [
                        str(key["name"]),
                        str(key["column"]),
                        str(key["references"]),
                        str(key["on_delete"]),
                    ]
                    for key in details["foreign_keys"]
                ],
            )
        else:
            self.info("No foreign keys were found.", timestamp=False)
        self.newLine()
        return 0
