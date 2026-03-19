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
backend/
├── app/
│   ├── main.py              # 整个应用的入口，配置中间件和路由总装
│   ├── core/
│   │   └── config.py        # 使用 Pydantic-settings 管理 .env 环境变量
│   ├── schema/
│   │   ├── chat.py          # 定义请求体（Message）和响应体的 Pydantic 模型
│   │   └── rag.py           # RAG相关的请求和响应模型
│   ├── api/
│   │   └── v1/
│   │       ├── chat.py      # 具体的聊天接口路由
│   │       └── rag.py        # RAG文档管理接口路由
│   └── service/             # 业务逻辑服务层
│       ├── agent/           # LangChain 核心逻辑
│       │   ├── factory.py   # 根据配置生产不同的 Agent（如 RAG Agent 或 Graph Agent）
│       │   ├── tools.py     # 法律查询、赔偿计算等自定义工具
│       │   └── prompts.py   # 管理复杂的法律 Prompt 模板
│       ├── rag/             # RAG文档处理服务
│       │   ├── text_embedding.py    # RAG文档处理核心服务
│       │   ├── file_hasher.py       # 文件MD5去重
│       │   ├── file_processor.py    # 文件处理（PDF、Word、Excel等）
│       │   └── ollama_embedding.py  # Ollama文本嵌入服务
│       └── vector_db.py     # 向量数据库（Chroma/Milvus）的初始化与检索封装
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