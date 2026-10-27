from typing import  Protocol

from sereleum.data.types import TEntity, TDomain

class Mapper(Protocol[TEntity, TDomain]):
    def to_domain(self, entity: TEntity) -> TDomain: ...
    def to_entity(self, domain: TDomain) -> TEntity: ...