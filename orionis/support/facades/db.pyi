from orionis.container.contracts.facade import IFacade
from orionis.orm.contracts.query_builder import IQueryBuilder

class DB(IQueryBuilder, IFacade):
    ...
