from typing import Dict, Any
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from app.service.graph.graph_db import Neo4jGraphStore
from app.service.graph.legal_graph_schema import (
    create_legal_graph_transformer,
    create_case_graph_transformer
)
from app.service.rag.file_processor import FileProcessor
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("graph_builder_v2")


class KnowledgeGraphBuilderV2:
    """基于 LangChain LLMGraphTransformer 的知识图谱构建器"""
    
    def __init__(
        self,
        graph_store: Neo4jGraphStore = None,
        llm = None,
        strict_mode: bool = None
    ):
        if graph_store is None:
            graph_store = Neo4jGraphStore()
        
        self.graph_store = graph_store
        
        if llm is None:
            llm = ChatOpenAI(
                base_url=settings.OPENAI_BASE_URL,
                api_key=settings.OPENAI_API_KEY,
                model=settings.GRAPH_MODEL_NAME,
                temperature=0
            )
            logger.info(f"使用配置模型 - model: {settings.GRAPH_MODEL_NAME}")
        
        self.llm = llm
        
        if strict_mode is None:
            strict_mode = settings.GRAPH_STRICT_MODE
            logger.info(f"使用配置严格模式 - strict_mode: {strict_mode}")
        
        self.strict_mode = strict_mode
        self.file_processor = FileProcessor()
        
        self.legal_transformer = create_legal_graph_transformer(llm, strict_mode)
        self.case_transformer = create_case_graph_transformer(llm, strict_mode)
        
        logger.info(f"知识图谱构建器V2初始化成功 - strict_mode: {strict_mode}")
    
    async def build_from_document(
        self,
        file_path: str,
        document_type: str = "legal",
        chunk_size: int = 1000,
        chunk_overlap: int = 100
    ) -> Dict[str, Any]:
        """
        从文档构建知识图谱
        
        Args:
            file_path: 文档路径
            document_type: 文档类型 (legal/case/general)
            chunk_size: 文本分块大小
            chunk_overlap: 文本分块重叠大小
            
        Returns:
            构建结果统计
        """
        logger.info(f"开始从文档构建知识图谱 - file: {file_path}, type: {document_type}")
        
        try:
            text = self.file_processor.extract_text(file_path)
            if not text:
                logger.error("文档内容为空")
                return {"success": False, "error": "文档内容为空"}
            
            logger.info(f"文档文本提取完成 - length: {len(text)}")
            
            chunks = self.file_processor.split_text(
                text,
                strategy="recursive"
            )
            
            logger.info(f"文本分块完成 - chunks: {len(chunks)}")
            
            if document_type == "legal":
                transformer = self.legal_transformer
            elif document_type == "case":
                transformer = self.case_transformer
            else:
                transformer = self.legal_transformer
            
            documents = [
                Document(page_content=chunk, metadata={"chunk_index": i})
                for i, chunk in enumerate(chunks)
            ]
            
            graph_documents = await transformer.aconvert_to_graph_documents(documents)
            
            logger.info(f"图谱提取完成 - graph_documents: {len(graph_documents)}")
            
            nodes_count = 0
            relationships_count = 0
            
            for graph_doc in graph_documents:
                for node in graph_doc.nodes:
                    node_id = self.graph_store.create_node(
                        node.type,
                        {
                            "id": node.id,
                            "type": node.type,
                            **node.properties
                        }
                    )
                    if node_id:
                        nodes_count += 1
                        logger.debug(f"创建节点 - type: {node.type}, id: {node.id}")
                
                for relationship in graph_doc.relationships:
                    success = self.graph_store.create_relationship(
                        relationship.source.id,
                        relationship.target.id,
                        relationship.type,
                        relationship.properties
                    )
                    if success:
                        relationships_count += 1
                        logger.debug(
                            f"创建关系 - "
                            f"{relationship.source.id} -[{relationship.type}]-> {relationship.target.id}"
                        )
            
            logger.info(
                f"知识图谱构建完成 - "
                f"nodes: {nodes_count}, relationships: {relationships_count}"
            )
            
            return {
                "success": True,
                "nodes_count": nodes_count,
                "relationships_count": relationships_count,
                "file_path": file_path,
                "chunks_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"构建知识图谱失败 - error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def build_from_text(
        self,
        text: str,
        document_type: str = "legal"
    ) -> Dict[str, Any]:
        """
        从文本构建知识图谱
        
        Args:
            text: 文本内容
            document_type: 文档类型
            
        Returns:
            构建结果统计
        """
        logger.info(
            f"开始从文本构建知识图谱 - "
            f"type: {document_type}, length: {len(text)}"
        )
        
        try:
            if document_type == "legal":
                transformer = self.legal_transformer
            elif document_type == "case":
                transformer = self.case_transformer
            else:
                transformer = self.legal_transformer
            
            document = Document(page_content=text)
            
            graph_documents = await transformer.aconvert_to_graph_documents([document])
            
            logger.info(f"图谱提取完成 - graph_documents: {len(graph_documents)}")
            
            nodes_count = 0
            relationships_count = 0
            
            for graph_doc in graph_documents:
                for node in graph_doc.nodes:
                    node_id = self.graph_store.create_node(
                        node.type,
                        {
                            "id": node.id,
                            "type": node.type,
                            **node.properties
                        }
                    )
                    if node_id:
                        nodes_count += 1
                
                for relationship in graph_doc.relationships:
                    success = self.graph_store.create_relationship(
                        relationship.source.id,
                        relationship.target.id,
                        relationship.type,
                        relationship.properties
                    )
                    if success:
                        relationships_count += 1
            
            logger.info(
                f"知识图谱构建完成 - "
                f"nodes: {nodes_count}, relationships: {relationships_count}"
            )
            
            return {
                "success": True,
                "nodes_count": nodes_count,
                "relationships_count": relationships_count
            }
            
        except Exception as e:
            logger.error(f"构建知识图谱失败 - error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """获取知识图谱统计信息"""
        return self.graph_store.get_statistics()
