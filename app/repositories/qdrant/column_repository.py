from app.entities.column_info_entity import ColumnInfoEntity
from app.repositories.qdrant.base_repository import BaseQdrantRepository


class ColumnQdrantRepository(BaseQdrantRepository[ColumnInfoEntity]):
    collection_name = "column_info_collection"

    def _create_entity(self, payload: dict):
        return ColumnInfoEntity(**payload)
