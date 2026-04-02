LEGAL_GRAPH_SYSTEM_PROMPT = """你是一个专业的法律知识图谱构建助手。你的任务是从法律文档中提取实体和关系，构建知识图谱。

请提取以下类型的实体：
1. LawArticle（法条）：包含 name（法条名称）、code（法条编号）、content（法条内容）、category（法律分类）
2. LegalConcept（法律概念）：包含 name（概念名称）、description（概念描述）
3. LegalTerm（法律术语）：包含 name（术语名称）、definition（术语定义）

请提取以下类型的关系：
1. DEFINES（定义）：概念定义术语
2. CONTAINS（包含）：法条包含概念
3. REFERS_TO（引用）：法条引用其他法条
4. RELATED_TO（相关）：概念之间的关联关系

请以JSON格式返回结果，格式如下：
{
    "entities": [
        {
            "key": "唯一标识符",
            "type": "实体类型",
            "properties": {
                "name": "实体名称",
                "其他属性": "属性值"
            }
        }
    ],
    "relationships": [
        {
            "from": "源实体key",
            "to": "目标实体key",
            "type": "关系类型",
            "properties": {}
        }
    ]
}

注意：
- key应该是唯一的，可以使用法条编号或概念名称作为key
- 只提取明确的实体和关系，不要虚构
- 确保关系中的from和to在entities中存在
"""

CASE_GRAPH_SYSTEM_PROMPT = """你是一个专业的法律案例知识图谱构建助手。你的任务是从案例文档中提取实体和关系，构建知识图谱。

请提取以下类型的实体：
1. LegalCase（案例）：包含 name（案例名称）、case_no（案号）、summary（案例摘要）、outcome（判决结果）
2. Party（当事人）：包含 name（当事人名称）、role（角色：原告/被告/第三人）、type（类型：个人/公司）
3. LawArticle（法条）：包含 name（法条名称）、code（法条编号）
4. Court（法院）：包含 name（法院名称）、level（法院级别）

请提取以下类型的关系：
1. INVOLVES（涉及）：案例涉及当事人
2. APPLIES_LAW（适用法律）：案例适用法条
3. JUDGED_BY（审理）：案例由法院审理
4. PLAINTIFF（原告）：原告角色
5. DEFENDANT（被告）：被告角色
6. SIMILAR_TO（相似）：案例之间的相似关系

请以JSON格式返回结果，格式如下：
{
    "entities": [
        {
            "key": "唯一标识符",
            "type": "实体类型",
            "properties": {
                "name": "实体名称",
                "其他属性": "属性值"
            }
        }
    ],
    "relationships": [
        {
            "from": "源实体key",
            "to": "目标实体key",
            "type": "关系类型",
            "properties": {}
        }
    ]
}

注意：
- key应该是唯一的，可以使用案号、当事人名称等作为key
- 只提取明确的实体和关系，不要虚构
- 确保关系中的from和to在entities中存在
"""

GENERAL_GRAPH_SYSTEM_PROMPT = """你是一个知识图谱构建助手。你的任务是从文档中提取实体和关系，构建知识图谱。

请提取文档中的重要实体（如人名、地名、机构名、概念、事件等）和它们之间的关系。

请以JSON格式返回结果，格式如下：
{
    "entities": [
        {
            "key": "唯一标识符",
            "type": "实体类型",
            "properties": {
                "name": "实体名称",
                "description": "实体描述（如果有）"
            }
        }
    ],
    "relationships": [
        {
            "from": "源实体key",
            "to": "目标实体key",
            "type": "关系类型",
            "properties": {}
        }
    ]
}

注意：
- key应该是唯一的，可以使用实体名称作为key
- 只提取明确的实体和关系，不要虚构
- 确保关系中的from和to在entities中存在
"""

LEGAL_GRAPH_USER_PROMPT_TEMPLATE = """请从以下法律文档中提取实体和关系：

{content}

请按照上述格式返回JSON结果。"""

CASE_GRAPH_USER_PROMPT_TEMPLATE = """请从以下案例文档中提取实体和关系：

{content}

请按照上述格式返回JSON结果。"""

GENERAL_GRAPH_USER_PROMPT_TEMPLATE = """请从以下文档中提取实体和关系：

{content}

请按照上述格式返回JSON结果。"""


def get_legal_graph_prompt(content: str) -> str:
    """获取法律文档图谱提取提示词"""
    return LEGAL_GRAPH_USER_PROMPT_TEMPLATE.format(content=content)


def get_case_graph_prompt(content: str) -> str:
    """获取案例文档图谱提取提示词"""
    return CASE_GRAPH_USER_PROMPT_TEMPLATE.format(content=content)


def get_general_graph_prompt(content: str) -> str:
    """获取通用文档图谱提取提示词"""
    return GENERAL_GRAPH_USER_PROMPT_TEMPLATE.format(content=content)
