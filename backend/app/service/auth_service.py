import json
import uuid
from datetime import datetime
from pathlib import Path
from app.core.logger import get_logger

logger = get_logger("auth_service")

USERS_FILE = Path("data/users.json")


def _load_users() -> dict:
    if not USERS_FILE.exists():
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {}
    try:
        content = USERS_FILE.read_text(encoding="utf-8")
        return json.loads(content) if content.strip() else {}
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"读取用户文件失败: {e}")
        return {}


def _save_users(users: dict) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("用户数据已保存")


def register_user(username: str, password: str) -> dict:
    users = _load_users()

    for user in users.values():
        if user["username"] == username:
            raise ValueError("用户名已存在")

    user_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    users[user_id] = {
        "username": username,
        "password": password,
        "user_id": user_id,
        "created_at": now,
    }

    _save_users(users)
    logger.info(f"用户注册成功: {username}, user_id: {user_id}")

    return {
        "user_id": user_id,
        "username": username,
        "token": user_id,
        "created_at": now,
    }


def login_user(username: str, password: str) -> dict:
    users = _load_users()

    matched_user = None
    for user in users.values():
        if user["username"] == username:
            matched_user = user
            break

    if not matched_user:
        raise ValueError("用户名或密码错误")

    if matched_user["password"] != password:
        raise ValueError("用户名或密码错误")

    logger.info(f"用户登录成功: {username}, user_id: {matched_user['user_id']}")

    return {
        "user_id": matched_user["user_id"],
        "username": matched_user["username"],
        "token": matched_user["user_id"],
        "created_at": matched_user["created_at"],
    }
