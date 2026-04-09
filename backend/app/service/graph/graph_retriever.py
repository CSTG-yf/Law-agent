from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.service.graph.graph_db import Neo4jGraphStore
from app.service.graph.legal_graph_schema import LegalGraphSchema, CaseGraphSchema
from app.core.config import settings
from app.core.logger import get_logger
import json

logger = get_logger("graph_retriever")


KEYWORD_EXTRACTION_PROMPT = """你是一个法律知识图谱检索助手。你的任务是从用户查询中提取关键词和可能的实体类型，用于在知识图谱中检索相关信息。

知识图谱中包含以下节点类型：
- LawArticle（法条）：法律条文，如"劳动合同法第39条"
- LegalConcept（法律概念）：法律相关概念，如"劳动者"、"用人单位"
- LegalTerm（法律术语）：专业法律术语
- LegalCase（案例）：法律案例
- Party（当事人）：案件当事人
- Court（法院）：审理法院
- LegalDocument（法律文书）：法律文件
- LegalProcedure（法律程序）：法律流程
- LegalSubject（法律主体）：法律关系主体
- LegalObject（法律客体）：法律关系客体

知识图谱中包含以下关系类型：
- DEFINES（定义）、CONTAINS（包含）、REFERS_TO（引用）
- APPLIES_LAW（适用法律）、INVOLVES（涉及）
- PLAINTIFF（原告）、DEFENDANT（被告）
- RELATED_TO（相关）、SIMILAR_TO（相似）

用户查询：{query}

请分析查询，提取以下信息（以JSON格式返回）：
{{
    "keywords": ["关键词1", "关键词2", ...],  // 从查询中提取的关键词，用于匹配实体名称
    "entity_types": ["可能的实体类型1", ...],  // 查询可能涉及的实体类型
    "relation_types": ["可能的关系类型1", ...],  // 查询可能涉及的关系类型
    "search_intent": "检索意图描述"  // 简要描述用户的检索意图
}}

注意：
1. keywords 应该是简短的词汇，便于在知识图谱中进行模糊匹配
2. entity_types 和 relation_types 必须是上面列出的类型之一
3. 如果无法确定类型，返回空数组
4. 只返回JSON，不要有其他内容"""


class GraphRetriever:
    def __init__(self, graph_store: Neo4jGraphStore = None, llm = None):
        self.graph_store = graph_store or Neo4jGraphStore()
        
        self.llm = ChatOpenAI(
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            model=settings.MODEL_NAME,
            temperature=0
        )
        
        self.keyword_prompt = ChatPromptTemplate.from_template(KEYWORD_EXTRACTION_PROMPT)
        
        logger.info("知识图谱检索器初始化成功")

    async def _extract_keywords(self, query: str) -> Dict[str, Any]:
        """使用 LLM 从查询中提取关键词和实体类型"""
        try:
            chain = self.keyword_prompt | self.llm
            response = await chain.ainvoke({"query": query})
            
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            
            logger.info(
                f"关键词提取完成 - keywords: {result.get('keywords', [])}, "
                f"entity_types: {result.get('entity_types', [])}, "
                f"intent: {result.get('search_intent', '')}"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"关键词提取JSON解析失败 - error: {str(e)}, response: {content}")
            return {"keywords": [], "entity_types": [], "relation_types": []}
        except Exception as e:
            logger.error(f"关键词提取失败 - error: {str(e)}")
            return {"keywords": [], "entity_types": [], "relation_types": []}

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
            extracted = await self._extract_keywords(query)
            keywords = extracted.get("keywords", [])
            extracted_entity_types = extracted.get("entity_types", [])
            extracted_relation_types = extracted.get("relation_types", [])
            
            if entity_types is None and extracted_entity_types:
                entity_types = extracted_entity_types
            
            if relation_types is None and extracted_relation_types:
                relation_types = extracted_relation_types
            
            all_entities = []
            all_relationships = []
            all_related = []
            seen_entity_ids = set()
            seen_rel_keys = set()
            
            search_terms = keywords if keywords else [query]
            
            for term in search_terms:
                entities = await self._search_entities(term, top_k, entity_types)
                for entity in entities:
                    entity_id = entity.get("data", {}).get("id")
                    if entity_id and entity_id not in seen_entity_ids:
                        seen_entity_ids.add(entity_id)
                        all_entities.append(entity)
                
                relationships = await self._search_relationships(term, top_k, relation_types)
                for rel in relationships:
                    source_id = rel.get("source", {}).get("id", "")
                    target_id = rel.get("target", {}).get("id", "")
                    rel_key = f"{source_id}-{target_id}"
                    if rel_key not in seen_rel_keys:
                        seen_rel_keys.add(rel_key)
                        all_relationships.append(rel)
                
                related = await self._search_related_entities(term, top_k)
                for r in related:
                    center_id = r.get("center", {}).get("id", "")
                    neighbor_id = r.get("neighbor", {}).get("id", "")
                    rel_key = f"{center_id}-{neighbor_id}"
                    if rel_key not in seen_rel_keys:
                        seen_rel_keys.add(rel_key)
                        all_related.append(r)
            
            logger.info(f"检索到 {len(all_entities)} 个实体, {len(all_relationships)} 个关系, {len(all_related)} 个相关实体")

            documents = self._convert_to_documents(all_entities, all_relationships, all_related)

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
                AND (coalesce(n.id, '') CONTAINS $query OR coalesce(n.name, '') CONTAINS $query OR coalesce(n.description, '') CONTAINS $query)
                RETURN n
                LIMIT $limit
                """
            else:
                cypher = """
                MATCH (n)
                WHERE coalesce(n.id, '') CONTAINS $query OR coalesce(n.name, '') CONTAINS $query OR coalesce(n.description, '') CONTAINS $query
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
                WHERE coalesce(a.id, '') CONTAINS $query OR coalesce(a.name, '') CONTAINS $query OR coalesce(b.id, '') CONTAINS $query OR coalesce(b.name, '') CONTAINS $query
                RETURN a, r, b
                LIMIT $limit
                """
            else:
                cypher = """
                MATCH (a)-[r]->(b)
                WHERE coalesce(a.id, '') CONTAINS $query OR coalesce(a.name, '') CONTAINS $query OR coalesce(b.id, '') CONTAINS $query OR coalesce(b.name, '') CONTAINS $query
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
            WHERE coalesce(center.id, '') CONTAINS $query OR coalesce(center.name, '') CONTAINS $query
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
            
            if not isinstance(data, dict):
                logger.warning(f"实体数据格式错误 - data: {type(data)}")
                continue
            
            logger.debug(f"处理实体 - data keys: {list(data.keys())}")
            
            name = data.get("name", data.get("id", "未知实体"))
            description = data.get("description", "")
            entity_type = data.get("type", "未知类型")
            content_text = data.get("content", "")

            content_parts = [f"【实体】{name}", f"类型：{entity_type}"]
            
            if description:
                content_parts.append(f"描述：{description}")
            
            if content_text:
                content_parts.append(f"内容：{content_text}")

            for key, value in data.items():
                if key not in ["name", "description", "type", "id", "content"]:
                    content_parts.append(f"{key}：{value}")

            content = "\n".join(content_parts) + "\n"

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
            
            if not isinstance(source, dict) or not isinstance(target, dict):
                logger.warning(f"关系数据格式错误 - source: {type(source)}, target: {type(target)}")
                continue
            
            logger.debug(f"处理关系 - source keys: {list(source.keys())}, target keys: {list(target.keys())}")
            
            if isinstance(relation, tuple):
                rel_type = relation[1] if len(relation) > 1 else str(relation)
            elif isinstance(relation, dict):
                rel_type = relation.get("type", "相关")
            else:
                rel_type = str(relation) if relation else "相关"

            source_name = source.get("name", source.get("id", "未知"))
            target_name = target.get("name", target.get("id", "未知"))
            
            content_parts = [f"【关系】{source_name} -[{rel_type}]-> {target_name}"]
            content_parts.append(f"源实体：{source_name}")
            content_parts.append(f"目标实体：{target_name}")
            content_parts.append(f"关系类型：{rel_type}")

            if source.get("description"):
                content_parts.append(f"源实体描述：{source['description']}")
            if source.get("content"):
                content_parts.append(f"源实体内容：{source['content']}")
            if target.get("description"):
                content_parts.append(f"目标实体描述：{target['description']}")
            if target.get("content"):
                content_parts.append(f"目标实体内容：{target['content']}")
            
            for key, value in source.items():
                if key not in ["name", "description", "type", "id", "content"]:
                    content_parts.append(f"源实体{key}：{value}")
            
            for key, value in target.items():
                if key not in ["name", "description", "type", "id", "content"]:
                    content_parts.append(f"目标实体{key}：{value}")
            
            if isinstance(relation, dict):
                for key, value in relation.items():
                    if key != "type":
                        content_parts.append(f"关系属性{key}：{value}")

            content = "\n".join(content_parts) + "\n"

            documents.append(Document(
                page_content=content,
                metadata={
                    "source": "knowledge_graph",
                    "type": "relationship",
                    "source_entity": source_name,
                    "target_entity": target_name,
                    "relation_type": rel_type,
                    **{f"source_{k}": v for k, v in source.items() if k not in ["name", "id"]},
                    **{f"target_{k}": v for k, v in target.items() if k not in ["name", "id"]}
                }
            ))

        for related in related_entities:
            center = related.get("center", {})
            neighbor = related.get("neighbor", {})
            relation = related.get("relation", {})
            
            if not isinstance(center, dict) or not isinstance(neighbor, dict):
                logger.warning(f"相关实体数据格式错误 - center: {type(center)}, neighbor: {type(neighbor)}")
                continue
            
            logger.debug(f"处理相关实体 - center keys: {list(center.keys())}, neighbor keys: {list(neighbor.keys())}")
            
            if isinstance(relation, tuple):
                rel_type = relation[1] if len(relation) > 1 else str(relation)
            elif isinstance(relation, dict):
                rel_type = relation.get("type", "相关")
            else:
                rel_type = str(relation) if relation else "相关"

            center_name = center.get("name", center.get("id", "未知"))
            neighbor_name = neighbor.get("name", neighbor.get("id", "未知"))
            
            content_parts = [f"【相关实体】{center_name} <-> {neighbor_name}"]
            content_parts.append(f"中心实体：{center_name}")
            content_parts.append(f"关联实体：{neighbor_name}")
            content_parts.append(f"关系类型：{rel_type}")

            if center.get("description"):
                content_parts.append(f"中心实体描述：{center['description']}")
            if center.get("content"):
                content_parts.append(f"中心实体内容：{center['content']}")
            if neighbor.get("description"):
                content_parts.append(f"关联实体描述：{neighbor['description']}")
            if neighbor.get("content"):
                content_parts.append(f"关联实体内容：{neighbor['content']}")
            
            for key, value in center.items():
                if key not in ["name", "description", "type", "id", "content"]:
                    content_parts.append(f"中心实体{key}：{value}")
            
            for key, value in neighbor.items():
                if key not in ["name", "description", "type", "id", "content"]:
                    content_parts.append(f"关联实体{key}：{value}")

            content = "\n".join(content_parts) + "\n"

            documents.append(Document(
                page_content=content,
                metadata={
                    "source": "knowledge_graph",
                    "type": "related_entity",
                    "center_entity": center_name,
                    "neighbor_entity": neighbor_name,
                    "relation_type": rel_type,
                    **{f"center_{k}": v for k, v in center.items() if k not in ["name", "id"]},
                    **{f"neighbor_{k}": v for k, v in neighbor.items() if k not in ["name", "id"]}
                }
            ))

        return documents
