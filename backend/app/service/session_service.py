from typing import Optional, List, Dict, Any
from datetime import datetime
from redis.asyncio import Redis
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)


class SessionService:
    """会话持久化服务 - 使用Redis存储"""
    
    def __init__(self):
        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        
        # Redis key前缀
        self.SESSION_PREFIX = "chat:session:"
        self.SESSION_LIST_PREFIX = "chat:sessions:"
        self.MESSAGE_PREFIX = "chat:message:"
        
        logger.info(f"SessionService初始化完成 - Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    
    async def create_session(
        self,
        session_id: str,
        user_id: str,
        rag_enabled: bool = False,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建新会话"""
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "rag_enabled": str(rag_enabled),
            "title": title or "",
            "message_count": "0"
        }
        
        # 存储会话信息
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        await self.redis.hset(session_key, mapping=session_data)
        
        # 添加到用户会话列表
        user_sessions_key = f"{self.SESSION_LIST_PREFIX}{user_id}"
        await self.redis.sadd(user_sessions_key, session_id)
        
        logger.info(f"创建会话成功 - session_id: {session_id}, user_id: {user_id}")
        return session_data
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        session_data = await self.redis.hgetall(session_key)
        
        if not session_data:
            return None
        
        # 转换类型
        session_data["rag_enabled"] = session_data.get("rag_enabled") == "True"
        session_data["message_count"] = int(session_data.get("message_count", 0))
        
        return session_data
    
    async def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        rag_enabled: Optional[bool] = None
    ) -> bool:
        """更新会话信息"""
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        
        # 检查会话是否存在
        if not await self.redis.exists(session_key):
            return False
        
        # 更新字段
        update_data = {
            "updated_at": datetime.now().isoformat()
        }
        if title is not None:
            update_data["title"] = title
        if rag_enabled is not None:
            update_data["rag_enabled"] = str(rag_enabled)
        
        await self.redis.hset(session_key, mapping=update_data)
        
        logger.info(f"更新会话成功 - session_id: {session_id}")
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话及其所有消息"""
        session_data = await self.get_session(session_id)
        if not session_data:
            return False
        
        # 删除会话
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        await self.redis.delete(session_key)
        
        # 从用户会话列表中移除
        user_id = session_data["user_id"]
        user_sessions_key = f"{self.SESSION_LIST_PREFIX}{user_id}"
        await self.redis.srem(user_sessions_key, session_id)
        
        # 删除该会话的所有消息
        message_list_key = f"{self.MESSAGE_PREFIX}{session_id}"
        await self.redis.delete(message_list_key)
        
        logger.info(f"删除会话成功 - session_id: {session_id}")
        return True
    
    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取会话列表"""
        sessions = []
        
        if user_id:
            # 获取指定用户的会话
            user_sessions_key = f"{self.SESSION_LIST_PREFIX}{user_id}"
            session_ids = await self.redis.smembers(user_sessions_key)
            
            for session_id in session_ids:
                session_data = await self.get_session(session_id)
                if session_data:
                    sessions.append(session_data)
        else:
            # 获取所有会话（需要遍历所有session key）
            pattern = f"{self.SESSION_PREFIX}*"
            async for key in self.redis.scan_iter(match=pattern):
                session_id = key.replace(self.SESSION_PREFIX, "")
                session_data = await self.get_session(session_id)
                if session_data:
                    sessions.append(session_data)
        
        # 按创建时间倒序排序
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        
        # 限制数量
        if limit and limit > 0:
            sessions = sessions[:limit]
        
        logger.info(f"查询会话列表成功 - user_id: {user_id}, total: {len(sessions)}")
        return sessions
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: List[Dict[str, Any]] = None,
        related_laws: List[Dict[str, Any]] = None,
        related_cases: List[Dict[str, Any]] = None,
        timestamp: Optional[str] = None
    ) -> bool:
        """添加消息到会话"""
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        
        # 检查会话是否存在
        if not await self.redis.exists(session_key):
            return False
        
        # 创建消息
        message_data = {
            "role": role,
            "content": content,
            "sources": json.dumps(sources or []),
            "related_laws": json.dumps(related_laws or []),
            "related_cases": json.dumps(related_cases or []),
            "timestamp": timestamp or datetime.now().isoformat()
        }
        
        # 存储消息
        message_list_key = f"{self.MESSAGE_PREFIX}{session_id}"
        await self.redis.rpush(message_list_key, json.dumps(message_data))
        
        # 更新会话的消息计数和更新时间
        await self.redis.hincrby(session_key, "message_count", 1)
        await self.redis.hset(session_key, "updated_at", datetime.now().isoformat())

        current_message_count = await self.redis.llen(message_list_key)
        session_message_count = await self.get_message_count(session_id)
        logger.info(
            f"添加消息成功 - session_id: {session_id}, role: {role}, "
            f"redis_list_count: {current_message_count}, session_message_count: {session_message_count}"
        )
        return True
    
    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取会话的所有消息"""
        message_list_key = f"{self.MESSAGE_PREFIX}{session_id}"
        
        # 获取所有消息
        message_count = await self.redis.llen(message_list_key)
        if message_count == 0:
            return []
        
        # 限制获取数量
        if limit and limit > 0:
            messages_json = await self.redis.lrange(message_list_key, -limit, -1)
        else:
            messages_json = await self.redis.lrange(message_list_key, 0, -1)
        
        # 解析消息
        messages = []
        for msg_json in messages_json:
            msg_data = json.loads(msg_json)
            msg_data["sources"] = json.loads(msg_data.get("sources") or "[]")
            msg_data["related_laws"] = json.loads(msg_data.get("related_laws") or "[]")
            msg_data["related_cases"] = json.loads(msg_data.get("related_cases") or "[]")
            messages.append(msg_data)

        logger.info(
            f"获取会话消息成功 - session_id: {session_id}, limit: {limit}, "
            f"redis_list_count: {message_count}, returned_count: {len(messages)}"
        )
        return messages
    
    async def clear_messages(self, session_id: str) -> bool:
        """清空会话的所有消息"""
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        
        # 检查会话是否存在
        if not await self.redis.exists(session_key):
            return False
        
        # 删除所有消息
        message_list_key = f"{self.MESSAGE_PREFIX}{session_id}"
        await self.redis.delete(message_list_key)
        
        # 重置消息计数
        await self.redis.hset(session_key, "message_count", 0)
        await self.redis.hset(session_key, "updated_at", datetime.now().isoformat())
        
        logger.info(f"清空消息成功 - session_id: {session_id}")
        return True
    
    async def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        return await self.redis.exists(session_key) > 0
    
    async def get_message_count(self, session_id: str) -> int:
        """获取会话的消息数量"""
        session_data = await self.get_session(session_id)
        if not session_data:
            return 0
        return session_data.get("message_count", 0)


# 全局实例
_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """获取SessionService单例"""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
