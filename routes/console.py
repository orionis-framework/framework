from orionis.support.facades import Reactor
from orionis.support.inspirational.inspire import Inspire

Reactor.command("example:command", [Inspire, "printQuote"])
