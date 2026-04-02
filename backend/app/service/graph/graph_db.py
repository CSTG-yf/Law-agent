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
