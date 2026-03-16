from langchain_openai import  ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate,ChatMessagePromptTemplate, FewShotChatMessagePromptTemplate,FewShotPromptTemplate,PromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

#1.设置模型

# 从环境变量获取API密钥
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_BASE_URL")

llm = ChatOpenAI(
    model = "qwen-max",
    openai_api_key=str(api_key),
    openai_api_base=str(api_base),
    temperature=0,
    streaming=True
)

system_message_template = ChatMessagePromptTemplate.from_template(
    template="你是一位{role}专家，擅长回答{domain}领域的内容",
    role="system"
)

human_message_template = ChatMessagePromptTemplate.from_template(
    template="用户问题：{question}",
    role="user"
)

chat_prompt_template = ChatPromptTemplate.from_messages([
    system_message_template,
    human_message_template
]

)

prompt = chat_prompt_template.format_messages(role="编程",domain="web开发",question="如何构建一个基于vue的前端应用？")


chain = chat_prompt_template | llm
# print(prompt)
resp = chain.stream(input={"role":"法律","domain":"法律","question":"非机动车闯红灯需罚款多少？"})

for chunk in resp:
    print(chunk.content,end = "")