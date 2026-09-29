from abc import ABC, abstractmethod

class IInspire(ABC):

    @abstractmethod
    def random(self) -> dict:
        """
        Return a random inspirational quote from the available list.

        Select a random quote from the internal list of inspirational quotes.
        If the list is empty, return a fallback quote to ensure a valid response.

        Returns
        -------
        dict
            Dictionary with 'quote' (str) and 'author' (str) keys. If no quotes
            are available, returns a fallback quote.
        """
