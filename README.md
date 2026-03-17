需求：构建法律AI问答系统

---------------------------------------------------------------------------------------------------
技术栈：

前端：Vue3  
后端：FastAPI + 混合检索RAG
agent智能体框架：Langchain  
项目依赖管理工具：uv  

docker中部署：ollama 向量嵌入模型，neo4j 图数据库，chroma 向量数据库。  

---------------------------------------------------------------------------------------------------
后端目前架构：
backend/
├── app/
│   ├── main.py              # 整个应用的入口，配置中间件和路由总装
│   ├── core/
│   │   └── config.py        # 使用 Pydantic-settings 管理 .env 环境变量
│   ├── schema/
│   │   └── chat.py          # 定义请求体（Message）和响应体的 Pydantic 模型
│   ├── api/
│   │   └── v1/
│   │       └── chat.py      # 具体的聊天接口路由
│   └── service/             # 业务逻辑服务层
│       ├── agent/           # LangChain 核心逻辑
│       │   ├── factory.py   # 根据配置生产不同的 Agent（如 RAG Agent 或 Graph Agent）
│       │   ├── tools.py     # 法律查询、赔偿计算等自定义工具
│       │   └── prompts.py   # 管理复杂的法律 Prompt 模板
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
├── data/                    # 存放法律文档、向量数据库等数据
├── docs/                    # 存放 API 文档（如 Swagger/OpenAPI）
└── tests/                   # 存放单元测试代码



---------------------------------------------------------------------------------------------------
命令：
激活环境：    .venv\Scripts\activate
启动docker容器：docker-compose up -d
向量模型下载脚本 docker exec legal-embedding-server bash /scripts/init-model.sh  
