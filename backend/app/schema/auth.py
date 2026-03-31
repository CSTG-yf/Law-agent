from typing import Optional
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class UserInfo(BaseModel):
    username: str = Field(..., description="用户名")
    user_id: str = Field(..., description="用户ID")
    created_at: str = Field(..., description="注册时间")


class AuthResponse(BaseModel):
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    token: str = Field(..., description="认证token")
    created_at: str = Field(..., description="注册时间")
