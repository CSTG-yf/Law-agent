from fastapi import APIRouter, Header
from typing import Optional
from app.schema.auth import RegisterRequest, LoginRequest, AuthResponse
from app.service import auth_service
from app.core.constants import HttpStatus
from app.core.logger import get_logger

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = get_logger("auth_api")


@router.post("/register")
def register(request: RegisterRequest) -> dict:
    logger.info(f"收到注册请求 - username: {request.username}")

    try:
        result = auth_service.register_user(request.username, request.password)
        logger.info(f"注册成功 - username: {request.username}, user_id: {result['user_id']}")
        return {
            "code": HttpStatus.CREATED,
            "status": "success",
            "message": "注册成功",
            "data": result,
        }
    except ValueError as e:
        logger.warning(f"注册失败 - username: {request.username}, 原因: {e}")
        return {
            "code": HttpStatus.CONFLICT,
            "status": "error",
            "message": str(e),
            "data": None,
        }
    except Exception as e:
        logger.error(f"注册异常 - username: {request.username}, 错误: {e}")
        return {
            "code": HttpStatus.INTERNAL_SERVER_ERROR,
            "status": "error",
            "message": "服务器内部错误",
            "data": None,
        }


@router.post("/login")
def login(request: LoginRequest) -> dict:
    logger.info(f"收到登录请求 - username: {request.username}")

    try:
        result = auth_service.login_user(request.username, request.password)
        logger.info(f"登录成功 - username: {request.username}, user_id: {result['user_id']}")
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "登录成功",
            "data": result,
        }
    except ValueError as e:
        logger.warning(f"登录失败 - username: {request.username}, 原因: {e}")
        return {
            "code": HttpStatus.UNAUTHORIZED,
            "status": "error",
            "message": str(e),
            "data": None,
        }
    except Exception as e:
        logger.error(f"登录异常 - username: {request.username}, 错误: {e}")
        return {
            "code": HttpStatus.INTERNAL_SERVER_ERROR,
            "status": "error",
            "message": "服务器内部错误",
            "data": None,
        }


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)) -> dict:
    logger.info("收到登出请求")

    try:
        logger.info("用户登出成功")
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "登出成功",
            "data": None,
        }
    except Exception as e:
        logger.error(f"登出异常 - 错误: {e}")
        return {
            "code": HttpStatus.INTERNAL_SERVER_ERROR,
            "status": "error",
            "message": "服务器内部错误",
            "data": None,
        }
