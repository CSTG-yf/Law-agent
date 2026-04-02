from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from app.service.graph.graph_db import Neo4jGraphStore
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("graph_retriever")


class GraphRetriever:
    def __init__(self, graph_store: Neo4jGraphStore = None):
        self.graph_store = graph_store or Neo4jGraphStore()
        logger.info("知识图谱检索器初始化成功")

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        entity_types: List[str] = None,
        relation_types: List[str] = None
    ) -> List[Document]:
        logger.info(
            f"开始知识图谱检索 - query: {query[:100]}, "
            f"top_k: {top_k}, entity_types: {entity_types}"
        )

        if not self.graph_store.is_connected():
            logger.warning("知识图谱未连接，返回空结果")
            return []

        try:
            entities = await self._search_entities(query, top_k, entity_types)
            logger.info(f"检索到 {len(entities)} 个实体")

            relationships = await self._search_relationships(query, top_k, relation_types)
            logger.info(f"检索到 {len(relationships)} 个关系")

            related_entities = await self._search_related_entities(query, top_k)
            logger.info(f"检索到 {len(related_entities)} 个相关实体")

            documents = self._convert_to_documents(entities, relationships, related_entities)

            logger.info(f"知识图谱检索完成 - 共生成 {len(documents)} 个文档")
            return documents[:top_k]

        except Exception as e:
            logger.error(f"知识图谱检索失败 - error: {str(e)}", exc_info=True)
            return []

    async def _search_entities(
        self,
        query: str,
        limit: int,
        entity_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            if entity_types:
                type_filter = " OR ".join([f"n:{t}" for t in entity_types])
                cypher = f"""
                MATCH (n)
                WHERE ({type_filter})
                AND (n.name CONTAINS $query OR n.description CONTAINS $query OR n.id CONTAINS $query)
                RETURN n
                LIMIT $limit
                """
            else:
                cypher = """
                MATCH (n)
                WHERE n.name CONTAINS $query OR n.description CONTAINS $query OR n.id CONTAINS $query
                RETURN n
                LIMIT $limit
                """

            results = self.graph_store.execute_query(cypher, {
                "query": query,
                "limit": limit
            })

            entities = []
            for result in results:
                if "n" in result:
                    node_data = result["n"]
                    entities.append({
                        "type": "entity",
                        "data": node_data
                    })

            return entities

        except Exception as e:
            logger.error(f"实体搜索失败 - error: {str(e)}")
            return []

    async def _search_relationships(
        self,
        query: str,
        limit: int,
        relation_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            if relation_types:
                type_filter = "|".join(relation_types)
                cypher = f"""
                MATCH (a)-[r:{type_filter}]->(b)
                WHERE a.name CONTAINS $query OR b.name CONTAINS $query
                RETURN a, r, b
                LIMIT $limit
                """
            else:
                cypher = """
                MATCH (a)-[r]->(b)
                WHERE a.name CONTAINS $query OR b.name CONTAINS $query
                RETURN a, r, b
                LIMIT $limit
                """

            results = self.graph_store.execute_query(cypher, {
                "query": query,
                "limit": limit
            })

            relationships = []
            for result in results:
                if "a" in result and "b" in result:
                    relationships.append({
                        "type": "relationship",
                        "source": result["a"],
                        "target": result["b"],
                        "relation": result.get("r", {})
                    })

            return relationships

        except Exception as e:
            logger.error(f"关系搜索失败 - error: {str(e)}")
            return []

    async def _search_related_entities(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        try:
            cypher = """
            MATCH (center)
            WHERE center.name CONTAINS $query OR center.id CONTAINS $query
            MATCH (center)-[r1]-(neighbor)
            RETURN center, r1, neighbor
            LIMIT $limit
            """

            results = self.graph_store.execute_query(cypher, {
                "query": query,
                "limit": limit
            })

            related = []
            for result in results:
                if "center" in result and "neighbor" in result:
                    related.append({
                        "type": "related_entity",
                        "center": result["center"],
                        "neighbor": result["neighbor"],
                        "relation": result.get("r1", {})
                    })

            return related

        except Exception as e:
            logger.error(f"相关实体搜索失败 - error: {str(e)}")
            return []

    def _convert_to_documents(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        related_entities: List[Dict]
    ) -> List[Document]:
        documents = []

        for entity in entities:
            data = entity.get("data", {})
            name = data.get("name", data.get("id", "未知实体"))
            description = data.get("description", "")
            entity_type = data.get("type", "未知类型")

            content = f"【实体】{name}\n类型：{entity_type}\n"
            if description:
                content += f"描述：{description}\n"

            for key, value in data.items():
                if key not in ["name", "description", "type", "id"]:
                    content += f"{key}：{value}\n"

            documents.append(Document(
                page_content=content,
                metadata={
                    "source": "knowledge_graph",
                    "type": "entity",
                    "entity_name": name,
                    "entity_type": entity_type,
                    **data
                }
            ))

        for rel in relationships:
            source = rel.get("source", {})
            target = rel.get("target", {})
            relation = rel.get("relation", {})

            source_name = source.get("name", source.get("id", "未知"))
            target_name = target.get("name", target.get("id", "未知"))
            rel_type = relation.get("type", "相关")

            content = f"【关系】{source_name} -[{rel_type}]-> {target_name}\n"
            content += f"源实体：{source_name}\n"
            content += f"目标实体：{target_name}\n"
            content += f"关系类型：{rel_type}\n"

            if source.get("description"):
                content += f"源实体描述：{source['description']}\n"
            if target.get("description"):
                content += f"目标实体描述：{target['description']}\n"

            documents.append(Document(
                page_content=content,
                metadata={
                    "source": "knowledge_graph",
                    "type": "relationship",
                    "source_entity": source_name,
                    "target_entity": target_name,
                    "relation_type": rel_type
                }
            ))

        for related in related_entities:
            center = related.get("center", {})
            neighbor = related.get("neighbor", {})
            relation = related.get("relation", {})

            center_name = center.get("name", center.get("id", "未知"))
            neighbor_name = neighbor.get("name", neighbor.get("id", "未知"))
            rel_type = relation.get("type", "相关")

            content = f"【相关实体】{center_name} <-> {neighbor_name}\n"
            content += f"中心实体：{center_name}\n"
            content += f"关联实体：{neighbor_name}\n"
            content += f"关系类型：{rel_type}\n"

            if neighbor.get("description"):
                content += f"关联实体描述：{neighbor['description']}\n"

            documents.append(Document(
                page_content=content,
                metadata={
                    "source": "knowledge_graph",
                    "type": "related_entity",
                    "center_entity": center_name,
                    "neighbor_entity": neighbor_name,
                    "relation_type": rel_type
                }
            ))

        return documents
