from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", 
api_key=api_key)

completion = client.chat.completions.create(
    model="qwen-max",
    messages=[

        {
            "role":"system",
            "content": "回答不得少于100个字."
        },
                {
            "role": "user",
             "content": "今天怎么样"
         }

    ],
    stream=True,
)

for chunk in completion:
    print("下一个内容")
    print(chunk.choices[0].delta.content, end="")
