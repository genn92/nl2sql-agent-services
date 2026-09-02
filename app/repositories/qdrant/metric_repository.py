from app.entities.metric_info_entity import MetricInfoEntity
from repositories.qdrant.base_repository import BaseQdrantRepository


class MetricQdrantRepository(BaseQdrantRepository[MetricInfoEntity]):
    collection_name = "metric_info_collection"

    def _create_entity(self, payload: dict):
        return MetricInfoEntity(**payload)
