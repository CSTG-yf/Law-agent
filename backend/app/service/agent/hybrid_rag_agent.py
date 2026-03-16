# backend/app/service/agent/hybrid_rag_agent.py

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

class HybridRAGAgent:
    def __init__(self, vector_db, graph_db, llm):
        self.vector_db = vector_db
        self.graph_db = graph_db
        self.llm = llm
        self.agent = self._create_agent()
    
    def _create_agent(self):
        # 创建检索工具
        tools = [
            Tool(
                name="vector_search",
                func=self._search_vector_db,
                description="在向量数据库中搜索相似案例和法律解释"
            ),
            Tool(
                name="graph_search",
                func=self._search_graph_db,
                description="在图数据库中查找相关联的法条和案例"
            ),
            Tool(
                name="legal_analysis",
                func=self._analyze_legal_context,
                description="综合分析法律上下文并给出专业建议"
            )
        ]
        
        # 创建 Agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的法律AI助手，擅长混合检索分析"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_openai_tools_agent(self.llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    def _search_vector_db(self, query: str) -> str:
        """向量检索：查找相似案例和法律解释"""
        results = self.vector_db.similarity_search(query, k=3)
        return self._format_vector_results(results)
    
    def _search_graph_db(self, query: str) -> str:
        """图谱检索：查找相关联的法条"""
        cypher_query = self._build_cypher_query(query)
        results = self.graph_db.run(cypher_query)
        return self._format_graph_results(results)
    
    def _analyze_legal_context(self, context: str) -> str:
        """综合分析和汇总"""
        prompt = f"""
        基于以下检索结果，提供专业的法律分析：
        
        向量检索结果：{context.get('vector_results', '')}
        图谱检索结果：{context.get('graph_results', '')}
        
        请提供：
        1. 相关法律条文
        2. 相似案例分析
        3. 专业建议
        """
        return self.llm.invoke(prompt).content
    
    def query(self, user_question: str) -> dict:
        """执行混合检索查询"""
        result = self.agent.invoke({"input": user_question})
        return {
            "answer": result["output"],
            "vector_sources": result.get("vector_sources", []),
            "graph_sources": result.get("graph_sources", []),
            "confidence": self._calculate_confidence(result)
        }