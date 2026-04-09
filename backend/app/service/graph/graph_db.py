from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("graph_db")


class Neo4jGraphStore:
    """Neo4j 图数据库封装"""
    
    def __init__(self):
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            logger.info(f"Neo4j 连接初始化成功 - URI: {settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"Neo4j 连接初始化失败 - error: {str(e)}")
            self.driver = None
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j 连接已关闭")
    
    def is_connected(self) -> bool:
        """检查数据库连接状态"""
        if not self.driver:
            return False
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败 - error: {str(e)}")
            return False
    
    def execute_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """
        执行 Cypher 查询
        
        Args:
            query: Cypher 查询语句
            parameters: 查询参数
            
        Returns:
            查询结果列表
        """
        if not self.driver:
            logger.error("数据库未连接")
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                records = [record.data() for record in result]
                logger.debug(f"查询执行成功 - query: {query[:100]}, results: {len(records)}")
                return records
        except Exception as e:
            logger.error(f"查询执行失败 - query: {query[:100]}, error: {str(e)}")
            return []
    
    def create_node(self, label: str, properties: Dict[str, Any]) -> Optional[str]:
        """
        创建节点
        
        Args:
            label: 节点标签
            properties: 节点属性
            
        Returns:
            节点 ID
        """
        if not self.driver:
            logger.error("数据库未连接")
            return None
        
        try:
            query = f"""
            MERGE (n:{label} {{id: $properties.id}})
            SET n += $properties
            RETURN elementId(n) as id
            """
            result = self.execute_query(query, {"properties": properties})
            
            if result and len(result) > 0:
                node_id = result[0]["id"]
                logger.info(f"创建节点成功 - label: {label}, id: {properties.get('id', 'unknown')}")
                return node_id
            else:
                logger.warning(f"创建节点失败 - label: {label}")
                return None
                
        except Exception as e:
            logger.error(f"创建节点失败 - label: {label}, error: {str(e)}")
            return None
    
    def create_relationship(
        self, 
        from_id: str, 
        to_id: str, 
        rel_type: str, 
        properties: Dict = None
    ) -> bool:
        """
        创建关系
        
        Args:
            from_id: 源节点 ID
            to_id: 目标节点 ID
            rel_type: 关系类型
            properties: 关系属性
            
        Returns:
            是否创建成功
        """
        if not self.driver:
            logger.error("数据库未连接")
            return False
        
        try:
            query = f"""
            MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += $properties
            RETURN r
            """
            result = self.execute_query(query, {
                "from_id": from_id,
                "to_id": to_id,
                "properties": properties or {}
            })
            
            success = len(result) > 0
            if success:
                logger.info(f"创建关系成功 - {from_id} -[{rel_type}]-> {to_id}")
            else:
                logger.warning(f"创建关系失败 - {from_id} -[{rel_type}]-> {to_id}")
            
            return success
                
        except Exception as e:
            logger.error(f"创建关系失败 - {from_id} -[{rel_type}]-> {to_id}, error: {str(e)}")
            return False
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict]:
        """根据 ID 获取节点"""
        query = """
        MATCH (n {id: $node_id})
        RETURN n
        """
        result = self.execute_query(query, {"node_id": node_id})
        return result[0] if result else None
    
    def get_node_by_name(self, name: str, label: str = None) -> Optional[Dict]:
        """根据名称获取节点"""
        if label:
            query = f"""
            MATCH (n:{label} {{name: $name}})
            RETURN n
            """
        else:
            query = """
            MATCH (n {name: $name})
            RETURN n
            """
        result = self.execute_query(query, {"name": name})
        return result[0] if result else None
    
    def delete_node(self, node_id: str) -> bool:
        """删除节点及其关系"""
        query = """
        MATCH (n {id: $node_id})
        DETACH DELETE n
        """
        try:
            self.execute_query(query, {"node_id": node_id})
            logger.info(f"删除节点成功 - id: {node_id}")
            return True
        except Exception as e:
            logger.error(f"删除节点失败 - id: {node_id}, error: {str(e)}")
            return False
    
    def clear_all(self) -> bool:
        """清空所有数据"""
        query = "MATCH (n) DETACH DELETE n"
        try:
            self.execute_query(query)
            logger.info("清空所有数据成功")
            return True
        except Exception as e:
            logger.error(f"清空数据失败 - error: {str(e)}")
            return False
    
    def delete_nodes_by_property(self, property_name: str, property_value: str) -> Dict[str, Any]:
        """
        根据属性删除节点
        
        Args:
            property_name: 属性名
            property_value: 属性值
            
        Returns:
            删除结果
        """
        query = f"""
        MATCH (n {{{property_name}: $value}})
        WITH n, count(n) as total
        DETACH DELETE n
        RETURN total
        """
        try:
            result = self.execute_query(query, {"value": property_value})
            deleted_count = result[0]["total"] if result else 0
            logger.info(f"删除节点成功 - property: {property_name}={property_value}, count: {deleted_count}")
            return {"success": True, "deleted_count": deleted_count}
        except Exception as e:
            logger.error(f"删除节点失败 - property: {property_name}={property_value}, error: {str(e)}")
            return {"success": False, "deleted_count": 0, "error": str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        try:
            node_count_query = "MATCH (n) RETURN count(n) as count"
            node_count = self.execute_query(node_count_query)[0]["count"]
            
            relationship_count_query = "MATCH ()-[r]->() RETURN count(r) as count"
            relationship_count = self.execute_query(relationship_count_query)[0]["count"]
            
            node_types_query = """
            MATCH (n)
            RETURN labels(n)[0] as type, count(n) as count
            ORDER BY count DESC
            """
            node_types = self.execute_query(node_types_query)
            
            relationship_types_query = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
            """
            relationship_types = self.execute_query(relationship_types_query)
            
            return {
                "total_nodes": node_count,
                "total_relationships": relationship_count,
                "node_types": node_types,
                "relationship_types": relationship_types
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败 - error: {str(e)}")
            return {
                "total_nodes": 0,
                "total_relationships": 0,
                "node_types": [],
                "relationship_types": []
            }

    def get_visualization_data(
        self,
        node_types: List[str] = None,
        relation_types: List[str] = None,
        node_limit: int = 100,
        depth: int = 2,
        search_term: str = None
    ) -> Dict[str, Any]:
        """
        获取可视化数据（NVL 兼容格式）
        
        Args:
            node_types: 过滤节点类型
            relation_types: 过滤关系类型
            node_limit: 节点数量限制
            depth: 关系深度
            search_term: 搜索关键词
            
        Returns:
            包含 nodes 和 relationships 的字典
        """
        if not self.driver:
            logger.error("数据库未连接")
            return {"nodes": [], "relationships": []}
        
        try:
            nodes = []
            relationships = []
            node_ids = set()
            rel_ids = set()
            
            node_filter = ""
            if node_types:
                node_filter = f"WHERE labels(n)[0] IN {node_types}"
            
            if search_term:
                if node_filter:
                    node_filter += f" AND n.name CONTAINS $search_term"
                else:
                    node_filter = "WHERE n.name CONTAINS $search_term"
            
            node_query = f"""
            MATCH (n)
            {node_filter}
            RETURN n
            LIMIT $limit
            """
            
            params = {"limit": node_limit}
            if search_term:
                params["search_term"] = search_term
            
            node_results = self.execute_query(node_query, params)
            
            for record in node_results:
                node_data = record.get("n", {})
                node_id = node_data.get("id") or node_data.get("name", "")
                if node_id and node_id not in node_ids:
                    node_ids.add(node_id)
                    nodes.append({
                        "id": node_id,
                        "labels": node_data.get("labels", []),
                        "properties": {k: v for k, v in node_data.items() if k not in ["id", "labels"]}
                    })
            
            if node_ids:
                depth_query = f"""
                MATCH (n)
                WHERE n.id IN $node_ids OR n.name IN $node_ids
                CALL {{
                    WITH n
                    MATCH (n)-[r*1..{depth}]-(related)
                    RETURN related, r
                    LIMIT $limit
                }}
                RETURN DISTINCT related, r
                """
                
                depth_results = self.execute_query(depth_query, {
                    "node_ids": list(node_ids),
                    "limit": node_limit * 2
                })
                
                for record in depth_results:
                    related_node = record.get("related", {})
                    related_id = related_node.get("id") or related_node.get("name", "")
                    
                    if related_id and related_id not in node_ids:
                        node_ids.add(related_id)
                        nodes.append({
                            "id": related_id,
                            "labels": related_node.get("labels", []),
                            "properties": {k: v for k, v in related_node.items() if k not in ["id", "labels"]}
                        })
                    
                    rel_list = record.get("r", [])
                    if isinstance(rel_list, list):
                        for rel in rel_list:
                            if isinstance(rel, tuple):
                                rel_id = str(rel[0]) if len(rel) > 0 else ""
                                rel_type = rel[1] if len(rel) > 1 else ""
                                start_node = str(rel[2]) if len(rel) > 2 else ""
                                end_node = str(rel[3]) if len(rel) > 3 else ""
                                rel_props = rel[4] if len(rel) > 4 and isinstance(rel[4], dict) else {}
                            elif isinstance(rel, dict):
                                rel_id = rel.get("id", "")
                                rel_type = rel.get("type", "")
                                start_node = rel.get("startNode", "")
                                end_node = rel.get("endNode", "")
                                rel_props = rel.get("properties", {})
                            else:
                                continue
                            
                            if rel_id and rel_id not in rel_ids:
                                if relation_types and rel_type not in relation_types:
                                    continue
                                rel_ids.add(rel_id)
                                relationships.append({
                                    "id": rel_id,
                                    "type": rel_type,
                                    "startNode": start_node,
                                    "endNode": end_node,
                                    "properties": rel_props
                                })
            
            if node_ids:
                rel_query = f"""
                MATCH (a)-[r]->(b)
                WHERE (a.id IN $node_ids OR a.name IN $node_ids)
                  AND (b.id IN $node_ids OR b.name IN $node_ids)
                RETURN a, b, r
                LIMIT $limit
                """
                
                rel_results = self.execute_query(rel_query, {
                    "node_ids": list(node_ids),
                    "limit": node_limit * 3
                })
                
                for record in rel_results:
                    rel_data = record.get("r", {})
                    
                    if isinstance(rel_data, tuple):
                        rel_id = str(rel_data[0]) if len(rel_data) > 0 else ""
                        rel_type = rel_data[1] if len(rel_data) > 1 else ""
                        start_node = str(rel_data[2]) if len(rel_data) > 2 else ""
                        end_node = str(rel_data[3]) if len(rel_data) > 3 else ""
                        rel_props = rel_data[4] if len(rel_data) > 4 and isinstance(rel_data[4], dict) else {}
                    elif isinstance(rel_data, dict):
                        rel_id = rel_data.get("id", "")
                        rel_type = rel_data.get("type", "")
                        start_node = rel_data.get("startNode", "")
                        end_node = rel_data.get("endNode", "")
                        rel_props = rel_data.get("properties", {})
                    else:
                        continue
                    
                    if relation_types and rel_type not in relation_types:
                        continue
                    
                    if rel_id and rel_id not in rel_ids:
                        rel_ids.add(rel_id)
                        relationships.append({
                            "id": rel_id,
                            "type": rel_type,
                            "startNode": start_node,
                            "endNode": end_node,
                            "properties": rel_props
                        })
            
            logger.info(
                f"获取可视化数据成功 - "
                f"nodes: {len(nodes)}, relationships: {len(relationships)}"
            )
            
            return {
                "nodes": nodes,
                "relationships": relationships
            }
            
        except Exception as e:
            logger.error(f"获取可视化数据失败 - error: {str(e)}")
            return {"nodes": [], "relationships": []}
    
    def get_visualization_data_v2(
        self,
        node_types: List[str] = None,
        relation_types: List[str] = None,
        node_limit: int = 100,
        depth: int = 2,
        search_term: str = None
    ) -> Dict[str, Any]:
        """
        获取可视化数据（NVL 兼容格式）- 优化版本
        
        使用单次查询获取所有数据，性能更好
        
        Args:
            node_types: 过滤节点类型
            relation_types: 过滤关系类型
            node_limit: 节点数量限制
            depth: 关系深度
            search_term: 搜索关键词
            
        Returns:
            包含 nodes 和 relationships 的字典
        """
        if not self.driver:
            logger.error("数据库未连接")
            return {"nodes": [], "relationships": []}
        
        try:
            node_filter_parts = []
            params = {"limit": node_limit, "depth": depth}
            
            if node_types:
                params["node_types"] = node_types
                node_filter_parts.append("labels(n)[0] IN $node_types")
            
            if search_term:
                params["search_term"] = search_term
                node_filter_parts.append("n.name CONTAINS $search_term")
            
            node_filter = "WHERE " + " AND ".join(node_filter_parts) if node_filter_parts else ""
            
            query = f"""
            MATCH (n)
            {node_filter}
            WITH n LIMIT $limit
            CALL {{
                WITH n
                MATCH path = (n)-[r*1..{depth}]-(connected)
                RETURN connected, relationships(path) as rels
            }}
            WITH n, connected, rels
            UNWIND rels as rel
            WITH DISTINCT n, connected, rel
            RETURN 
                n.id as node_id,
                labels(n) as node_labels,
                properties(n) as node_props,
                connected.id as connected_id,
                labels(connected) as connected_labels,
                properties(connected) as connected_props,
                elementId(rel) as rel_id,
                type(rel) as rel_type,
                startNode(rel).id as start_id,
                endNode(rel).id as end_id,
                properties(rel) as rel_props
            """
            
            results = self.execute_query(query, params)
            
            nodes_map = {}
            relationships = []
            rel_ids = set()
            
            for record in results:
                node_id = record.get("node_id") or record.get("node_labels", [""])[0]
                if node_id and node_id not in nodes_map:
                    nodes_map[node_id] = {
                        "id": node_id,
                        "labels": record.get("node_labels", []),
                        "properties": record.get("node_props", {})
                    }
                
                connected_id = record.get("connected_id")
                if connected_id and connected_id not in nodes_map:
                    nodes_map[connected_id] = {
                        "id": connected_id,
                        "labels": record.get("connected_labels", []),
                        "properties": record.get("connected_props", {})
                    }
                
                rel_id = record.get("rel_id", "")
                rel_type = record.get("rel_type", "")
                
                if relation_types and rel_type not in relation_types:
                    continue
                
                if rel_id and rel_id not in rel_ids:
                    rel_ids.add(rel_id)
                    relationships.append({
                        "id": rel_id,
                        "type": rel_type,
                        "startNode": record.get("start_id", ""),
                        "endNode": record.get("end_id", ""),
                        "properties": record.get("rel_props", {})
                    })
            
            nodes = list(nodes_map.values())
            
            logger.info(
                f"获取可视化数据成功 - "
                f"nodes: {len(nodes)}, relationships: {len(relationships)}"
            )
            
            return {
                "nodes": nodes,
                "relationships": relationships
            }
            
        except Exception as e:
            logger.error(f"获取可视化数据失败 - error: {str(e)}")
            return {"nodes": [], "relationships": []}
