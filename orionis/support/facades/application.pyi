from orionis.container.contracts.container import IContainer
from orionis.container.contracts.facade import IFacade
from orionis.foundation.contracts.application import IApplication

class Application(IApplication, IContainer, IFacade):
    ...
