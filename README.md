需求：构建法律AI问答系统

---------------------------------------------------------------------------------------------------
技术栈：

前端：Vue3  
后端：FastAPI + 混合检索RAG
agent智能体框架：Langchain  
项目依赖管理工具：uv  

docker中部署：ollama 向量嵌入模型，neo4j 图数据库，chroma 向量数据库，redis 任务队列。  

---------------------------------------------------------------------------------------------------
后端目前架构：
```bash
backend/
├── app/
│   ├── main.py              # 整个应用的入口，配置中间件和路由总装
│   ├── core/
│   │   ├── config.py        # 使用 Pydantic-settings 管理 .env 环境变量
│   │   └── constants.py    # 状态码和常量定义
│   ├── schema/
│   │   ├── chat.py          # 对话请求体和响应体的 Pydantic 模型
│   │   └── rag.py           # RAG相关的请求和响应模型
│   ├── api/
│   │   └── v1/
│   │       ├── chat.py      # 多轮对话接口路由（支持SSE流式输出）
│   │       └── rag.py        # RAG文档管理接口路由
│   └── service/             # 业务逻辑服务层
│       ├── agent/           # LangGraph多轮对话Agent
│       │   ├── factory.py               # Agent工厂，管理LLM和RAG检索器实例
│       │   ├── legal_conversation_agent.py # LangGraph多轮对话Agent核心
│       │   ├── conversation_state.py    # 对话状态定义（TypedDict）
│       │   ├── conversation_manager.py   # 对话管理器（滑动窗口、历史压缩）
│       │   ├── rag_retriever.py       # RAG检索器（集成AdvancedRAGService）
│       │   ├── sse_streamer.py        # SSE流式输出处理器
│       │   ├── tools.py               # 法律查询、赔偿计算等自定义工具
│       ├── prompts/          # 提示词模板集中管理
│       │   └── conversation_prompts.py # 多轮对话提示词模板
│       ├── rag/             # RAG文档处理服务
│       │   ├── hybrid_retriever.py    # 混合检索器（Vector+BM25+MMR+MultiQuery）
│       │   ├── text_embedding.py    # RAG文档处理核心服务
│       │   ├── file_hasher.py       # 文件MD5去重
│       │   ├── file_processor.py    # 文件处理（PDF、Word、Excel等）
│       │   ├── ollama_embedding.py  # Ollama文本嵌入服务
│       │   └── reranker.py          # 检索结果重排序
│       ├── vector_db.py     # 向量数据库（Chroma）的初始化与检索封装
│       └── tasks/           # 异步任务处理
│           └── document_tasks.py  # 文档处理异步任务
├── scripts/
│   ├── init-model.sh        # 模型初始化脚本
│   └── init-model-optimized.sh  # 优化的模型初始化脚本
├── .env                     # 存放 API_KEY 和数据库连接串
├── pyproject.toml           # 项目依赖配置
├── backend/ollama_models/   # Ollama 模型存储目录（Docker 挂载点）
├── backend/neo4j/           # Neo4j 图数据库目录（Docker 挂载点）
│   ├── data/               # 数据库数据
│   ├── logs/               # 日志文件
│   └── import/             # 数据导入文件
├── backend/chroma_data/     # Chroma 向量数据库数据目录（Docker 挂载点）
├── backend/uploads/         # 上传文件存储目录
├── data/                    # 存放法律文档、向量数据库等数据
├── docs/                    # 存放 API 文档（如 Swagger/OpenAPI）
└── tests/                   # 存放单元测试代码
```


---------------------------------------------------------------------------------------------------
命令：
激活环境：
```bash
cd backend
.venv\Scripts\activate
```

启动docker容器：
```bash
docker-compose up -d
```

向量模型下载启动脚本：
```bash
docker exec legal-embedding-server bash /scripts/init-model.sh
```

启动后端服务：
```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动Celery Worker（用于异步任务处理）：
```bash
cd backend
# Windows
scripts\start-celery.bat

# Linux/Mac
bash scripts/start-celery.sh
```

API文档：
启动服务后访问：http://localhost:8000/docs

---------------------------------------------------------------------------------------------------
多轮对话API说明：

基于LangGraph实现的多轮对话系统，支持流式输出和可选的RAG检索。

核心特性：
- 多轮对话管理：基于session_id维护对话上下文
- 滑动窗口：自动控制历史记录长度（默认10轮，可配置1-50）
- 流式输出：支持SSE实时输出，提升用户体验
- RAG集成：可选启用RAG检索，支持多种检索策略
- 会话管理：完整的会话生命周期管理（创建、查询、删除、清空）

检索策略：
- vector：向量检索（基于语义相似度）
- hybrid：混合检索（向量+BM25关键词）
- mmr：最大边际相关性检索（平衡相关性和多样性）
- multi_query：多查询检索（生成多个查询变体）

API接口：
- POST /api/v1/chat/message - 发送消息（支持流式和RAG）
- GET /api/v1/chat/sessions/{session_id} - 获取会话信息
- GET /api/v1/chat/sessions/{session_id}/history - 获取对话历史
- DELETE /api/v1/chat/sessions/{session_id} - 删除会话
- GET /api/v1/chat/sessions - 获取会话列表
- POST /api/v1/chat/sessions/{session_id}/clear - 清空会话历史

请求示例：
```json
{
  "message": "劳动纠纷中如何计算经济补偿金？",
  "session_id": "session-123",
  "user_id": "user-456",
  "use_rag": true,
  "retrieval_strategy": "hybrid",
  "max_history": 10,
  "stream": false
}
```

Apifox接口文档：
backend/docs/apifox_chat_api.json