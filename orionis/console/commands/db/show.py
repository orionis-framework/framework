from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.db._inspection import DatabaseInspector
from orionis.console.commands.migrate.base import MigrationCommand
from orionis.database.contracts.connection_manager import IConnectionManager

_KIB: int = 1024

def format_bytes(size: int | None) -> str:
    """
    Format a byte count for display.

    Parameters
    ----------
    size : int | None
        Number of bytes to render, or ``None`` when the value is unavailable.

    Returns
    -------
    str
        A human-readable size string, or ``"N/A"`` when the size is unknown.
    """
    if size is None:
        return "N/A"
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < _KIB:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= _KIB
    return f"{value:.1f} TiB"

class DbShowCommand(MigrationCommand):
    """Render connection details and a table summary."""

    # ruff: noqa: TC001

    timestamps: bool = False
    signature: str = "db:show"
    description: str = "Shows database information and table summaries."
    arguments: ClassVar[list[Argument]] = [
        *MigrationCommand.arguments,
        Argument(
            name_or_flags="--counts",
            action="store_true",
            help="Count table rows (may be slow on large databases).",
            dest="counts",
        ),
        Argument(
            name_or_flags="--views",
            action="store_true",
            help="Include views in the output.",
            dest="views",
        ),
    ]

    async def handle(self, conn_manager: IConnectionManager) -> None: # NOSONAR
        """
        Fetch metadata and render the database summary.

        Parameters
        ----------
        conn_manager : IConnectionManager
            Connection manager used to resolve the active database.

        Returns
        -------
        None
            The command writes the summary to the console.
        """
        inspector = DatabaseInspector(conn_manager, self.targetConnection())
        include_counts = self.getArgument("counts", default=False)
        include_views = self.getArgument("views", default=False)
        tables = await inspector.listTables()
        if include_views:
            views = await inspector.listViews()
            materialized_views = await inspector.listMaterializedViews()
            view_count = len(views)
            materialized_count = len(materialized_views)
        else:
            view_count, materialized_count = await inspector.viewCounts()
        size = await inspector.databaseSize()
        connections = await inspector.connectionCount()
        table_sizes = await inspector.tableSizes(tables)

        self.newLine()
        self.table(
            ["Property", "Value"],
            [
                ["Connection", inspector.name],
                ["Driver", inspector.driver],
                ["Database", str(inspector.config.get("database") or "N/A")],
                ["Size", format_bytes(size)],
                [
                    "Open connections",
                    str(connections) if connections is not None else "N/A",
                ],
                ["Tables", str(len(tables))],
                ["Views", str(view_count)],
                ["Materialized views", str(materialized_count)],
            ],
        )
        self.newLine()

        if tables:
            rows = []
            for name in tables:
                row = [name, format_bytes(table_sizes.get(name))]
                if include_counts:
                    row.append(str(await inspector.rowCount(name)))
                rows.append(row)
            headers = ["Table", "Size"]
            if include_counts:
                headers.append("Rows")
            self.table(headers, rows)
        else:
            self.info("No tables were found.", timestamp=False)

        if include_views:
            self.newLine()
            if views or materialized_views:
                self.table(
                    ["View", "Type"],
                    [
                        *[[name, "View"] for name in views],
                        *[[name, "Materialized"] for name in materialized_views],
                    ],
                )
            else:
                self.info("No views were found.", timestamp=False)
        self.newLine()
