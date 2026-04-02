from typing import List
from langchain_experimental.graph_transformers import LLMGraphTransformer
from app.core.logger import get_logger

logger = get_logger("legal_graph_schema")


class LegalGraphSchema:
    """法律知识图谱 Schema 定义"""
    
    ALLOWED_NODES = [
        "LawArticle",
        "LegalConcept",
        "LegalTerm",
        "LegalCase",
        "Party",
        "Court",
        "LegalDocument",
        "LegalProcedure",
        "LegalSubject",
        "LegalObject",
    ]
    
    ALLOWED_RELATIONSHIPS = [
        "DEFINES",
        "CONTAINS",
        "REFERS_TO",
        "RELATED_TO",
        "APPLIES_LAW",
        "INVOLVES",
        "JUDGED_BY",
        "PLAINTIFF",
        "DEFENDANT",
        "SIMILAR_TO",
        "PRECEDES",
        "FOLLOWS",
        "AMENDS",
        "REPEALS",
    ]
    
    NODE_PROPERTIES = {
        "LawArticle": ["name", "code", "content", "category", "effective_date"],
        "LegalConcept": ["name", "description", "category"],
        "LegalTerm": ["name", "definition", "usage"],
        "LegalCase": ["name", "case_no", "summary", "outcome", "judgment_date"],
        "Party": ["name", "role", "type", "contact"],
        "Court": ["name", "level", "jurisdiction"],
        "LegalDocument": ["name", "type", "content", "create_date"],
        "LegalProcedure": ["name", "description", "duration", "requirements"],
        "LegalSubject": ["name", "type", "capacity"],
        "LegalObject": ["name", "type", "value"],
    }
    
    RELATIONSHIP_PROPERTIES = {
        "APPLIES_LAW": ["context", "relevance"],
        "INVOLVES": ["role", "description"],
        "SIMILAR_TO": ["similarity_score", "reason"],
    }


class CaseGraphSchema:
    """案例知识图谱 Schema 定义"""
    
    ALLOWED_NODES = [
        "LegalCase",
        "Party",
        "LawArticle",
        "Court",
        "Evidence",
        "LegalBasis",
        "Judgment",
        "Lawyer",
        "Agent",
    ]
    
    ALLOWED_RELATIONSHIPS = [
        "PLAINTIFF",
        "DEFENDANT",
        "THIRD_PARTY",
        "APPLIES_LAW",
        "JUDGED_BY",
        "SUBMITS_EVIDENCE",
        "BASED_ON",
        "REPRESENTED_BY",
        "CITES_CASE",
        "APPEALS_TO",
    ]
    
    NODE_PROPERTIES = {
        "LegalCase": ["name", "case_no", "summary", "outcome", "judgment_date", "case_type"],
        "Party": ["name", "role", "type", "gender", "age"],
        "LawArticle": ["name", "code", "content"],
        "Court": ["name", "level", "location"],
        "Evidence": ["name", "type", "description", "submitter"],
        "LegalBasis": ["name", "content", "relevance"],
        "Judgment": ["content", "result", "amount"],
        "Lawyer": ["name", "license_no", "firm"],
        "Agent": ["name", "type", "authorization"],
    }
    
    RELATIONSHIP_PROPERTIES = {
        "APPLIES_LAW": ["context", "application"],
        "SUBMITS_EVIDENCE": ["date", "purpose"],
        "REPRESENTED_BY": ["authorization_type", "scope"],
    }


def create_legal_graph_transformer(llm, strict_mode: bool = True) -> LLMGraphTransformer:
    """
    创建法律知识图谱转换器
    
    Args:
        llm: 大语言模型实例
        strict_mode: 是否启用严格模式（只提取定义的类型）
        
    Returns:
        LLMGraphTransformer 实例
    """
    logger.info(f"创建法律知识图谱转换器 - strict_mode: {strict_mode}")
    
    try:
        transformer = LLMGraphTransformer(
            llm=llm,
            allowed_nodes=LegalGraphSchema.ALLOWED_NODES,
            allowed_relationships=LegalGraphSchema.ALLOWED_RELATIONSHIPS,
            strict_mode=strict_mode,
            node_properties=True,
        )
        
        logger.info(
            f"图谱转换器创建成功 - "
            f"nodes: {len(LegalGraphSchema.ALLOWED_NODES)}, "
            f"relationships: {len(LegalGraphSchema.ALLOWED_RELATIONSHIPS)}"
        )
        
        return transformer
        
    except Exception as e:
        logger.error(f"创建图谱转换器失败 - error: {str(e)}")
        raise


def create_case_graph_transformer(llm, strict_mode: bool = True) -> LLMGraphTransformer:
    """
    创建案例知识图谱转换器
    
    Args:
        llm: 大语言模型实例
        strict_mode: 是否启用严格模式
        
    Returns:
        LLMGraphTransformer 实例
    """
    logger.info(f"创建案例知识图谱转换器 - strict_mode: {strict_mode}")
    
    try:
        transformer = LLMGraphTransformer(
            llm=llm,
            allowed_nodes=CaseGraphSchema.ALLOWED_NODES,
            allowed_relationships=CaseGraphSchema.ALLOWED_RELATIONSHIPS,
            strict_mode=strict_mode,
            node_properties=True,
        )
        
        logger.info(
            f"图谱转换器创建成功 - "
            f"nodes: {len(CaseGraphSchema.ALLOWED_NODES)}, "
            f"relationships: {len(CaseGraphSchema.ALLOWED_RELATIONSHIPS)}"
        )
        
        return transformer
        
    except Exception as e:
        logger.error(f"创建图谱转换器失败 - error: {str(e)}")
        raise
