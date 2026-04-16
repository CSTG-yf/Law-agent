from typing import List
import httpx
from app.core.config import settings


class OllamaEmbedding:
    """Ollama文本嵌入服务"""

    def __init__(self, host: str = None, model: str = None):
        """
        初始化Ollama嵌入服务

        Args:
            host: Ollama服务地址
            model: 嵌入模型名称
        """
        self.host = host or settings.OLLAMA_HOST
        self.model = model or settings.OLLAMA_MODEL
        self.api_url = f"{self.host}/api/embeddings"

    async def embed_text(self, text: str) -> List[float]:
        """
        生成文本的嵌入向量

        Args:
            text: 待嵌入的文本

        Returns:
            嵌入向量
        """
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                return await self._embed_text_with_async_client(client, text)
        except Exception as e:
            print(f"生成嵌入向量失败: {e}")
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成文本的嵌入向量

        Args:
            texts: 待嵌入的文本列表

        Returns:
            嵌入向量列表
        """
        embeddings = []
        async with httpx.AsyncClient(timeout=300.0) as client:
            for text in texts:
                embedding = await self._embed_text_with_async_client(client, text)
                embeddings.append(embedding)
        return embeddings

    def embed_text_sync(self, text: str) -> List[float]:
        """
        同步生成文本的嵌入向量

        Args:
            text: 待嵌入的文本

        Returns:
            嵌入向量
        """
        try:
            with httpx.Client(timeout=300.0) as client:
                return self._embed_text_with_client(client, text)
        except Exception as e:
            print(f"生成嵌入向量失败: {e}")
            raise

    def embed_texts_sync(self, texts: List[str]) -> List[List[float]]:
        """
        同步批量生成文本的嵌入向量

        Args:
            texts: 待嵌入的文本列表

        Returns:
            嵌入向量列表
        """
        embeddings = []
        with httpx.Client(timeout=300.0) as client:
            for text in texts:
                embedding = self._embed_text_with_client(client, text)
                embeddings.append(embedding)
        return embeddings

    async def _embed_text_with_async_client(self, client: httpx.AsyncClient, text: str) -> List[float]:
        payload = {
            "model": self.model,
            "prompt": text
        }
        response = await client.post(self.api_url, json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get("embedding", [])

    def _embed_text_with_client(self, client: httpx.Client, text: str) -> List[float]:
        payload = {
            "model": self.model,
            "prompt": text
        }
        response = client.post(self.api_url, json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get("embedding", [])
