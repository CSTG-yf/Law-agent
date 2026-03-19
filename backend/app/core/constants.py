"""状态码和常量定义模块

该模块集中定义了应用程序中使用的所有状态码和常量，
确保前后端状态码定义的一致性。

状态码分类：
- 2xx: 成功响应
- 4xx: 客户端错误
- 5xx: 服务器错误
"""
from enum import IntEnum
from typing import List


class HttpStatus(IntEnum):
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


class BusinessCode(IntEnum):
    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    VALIDATION_ERROR = 422
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503


RETRYABLE_STATUS_CODES: List[int] = [
    0,
    408,
    429,
    500,
    502,
    503,
    504,
]


DEFAULT_MESSAGES = {
    HttpStatus.OK: "success",
    HttpStatus.CREATED: "资源创建成功",
    HttpStatus.ACCEPTED: "请求已接受",
    HttpStatus.NO_CONTENT: "操作成功",
    HttpStatus.BAD_REQUEST: "请求参数错误",
    HttpStatus.UNAUTHORIZED: "认证失败，请重新登录",
    HttpStatus.FORBIDDEN: "权限不足",
    HttpStatus.NOT_FOUND: "请求的资源不存在",
    HttpStatus.METHOD_NOT_ALLOWED: "请求方法不允许",
    HttpStatus.REQUEST_TIMEOUT: "请求超时",
    HttpStatus.CONFLICT: "资源冲突",
    HttpStatus.UNPROCESSABLE_ENTITY: "数据验证失败",
    HttpStatus.TOO_MANY_REQUESTS: "请求过于频繁，请稍后再试",
    HttpStatus.INTERNAL_SERVER_ERROR: "服务器内部错误",
    HttpStatus.NOT_IMPLEMENTED: "功能暂未实现",
    HttpStatus.BAD_GATEWAY: "网关错误",
    HttpStatus.SERVICE_UNAVAILABLE: "服务暂时不可用",
    HttpStatus.GATEWAY_TIMEOUT: "网关超时",
}


def get_message(status_code: int, default: str = "未知错误") -> str:
    return DEFAULT_MESSAGES.get(status_code, default)
