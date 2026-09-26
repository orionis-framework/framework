from orionis.console import Argument
from orionis.console.base import BaseCommand
from orionis.support.inspirational import Inspire

class InspireCommand(BaseCommand):

    # Command name, by convention in lowercase and starting with app.
    signature: str = "app:inspire"

    # Description of the command.
    description: str = "Prints a random inspirational quote."

    # Define command arguments using the Argument dataclass.
    # This example includes an optional argument for text capitalization.
    arguments: list[Argument] = [
        Argument(
            name_or_flags=["--case", "-c"],
            type_=str,
            help="Capitalization format: 'upper', 'lower', 'title'.",
            choices=["upper", "lower", "title"],
            required=False,
        ),
    ]

    async def handle(self, inspire: Inspire) -> None:
        """
        Execute the command to print a random inspirational quote.

        Parameters
        ----------
        inspire : Inspire [Dependency Injection]
            Service providing inspirational quotes.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Retrieve a random inspirational quote from the service.
        quote, author = inspire.random().values()

        # Get the desired capitalization format from arguments.
        text_case: str | None = self.getArgument("case")

        # Define available capitalization functions.
        case_functions: dict[str, callable] = {
            "upper": str.upper,
            "lower": str.lower,
            "title": str.title,
        }

        # Apply the selected capitalization format if specified.
        if text_case in case_functions:
            quote = case_functions[text_case](quote)

        # Display the quote in the console with bold green formatting.
        self.textSuccessBold(quote)

        # Add a short delay before displaying the author.
        for letter in author:
            await self.sleep(0.04)
            self.write(letter, end="", flush=True)

        # Add a newline after printing the author.
        self.line()
