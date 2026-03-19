import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
import json


def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(handler)
    return logger


class APILogger:
    def __init__(self, name: str = "api"):
        self.logger = get_logger(name)
    
    def log_request(self, method: str, path: str, params: dict = None, headers: dict = None):
        request_info = {
            "type": "REQUEST",
            "method": method,
            "path": path,
            "timestamp": datetime.now().isoformat()
        }
        
        if params:
            request_info["params"] = self._sanitize_params(params)
        
        if headers:
            request_info["headers"] = self._sanitize_headers(headers)
        
        self.logger.info(json.dumps(request_info, ensure_ascii=False, indent=2))
    
    def log_response(self, method: str, path: str, status_code: int, response_data: dict = None, duration: float = None):
        response_info = {
            "type": "RESPONSE",
            "method": method,
            "path": path,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        }
        
        if duration is not None:
            response_info["duration_ms"] = round(duration * 1000, 2)
        
        if response_data:
            response_info["data"] = self._sanitize_response(response_data)
        
        log_level = logging.INFO if status_code < 400 else logging.ERROR
        self.logger.log(log_level, json.dumps(response_info, ensure_ascii=False, indent=2))
    
    def log_error(self, method: str, path: str, error: Exception, duration: float = None):
        error_info = {
            "type": "ERROR",
            "method": method,
            "path": path,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat()
        }
        
        if duration is not None:
            error_info["duration_ms"] = round(duration * 1000, 2)
        
        self.logger.error(json.dumps(error_info, ensure_ascii=False, indent=2))
    
    def _sanitize_params(self, params: dict) -> dict:
        if not params:
            return {}
        
        sensitive_keys = ["password", "token", "api_key", "secret", "authorization"]
        sanitized = {}
        
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, (dict, list)):
                sanitized[key] = str(type(value).__name__) + "..."
            else:
                sanitized[key] = str(value)[:500]
        
        return sanitized
    
    def _sanitize_headers(self, headers: dict) -> dict:
        if not headers:
            return {}
        
        sensitive_keys = ["authorization", "cookie", "x-api-key", "token"]
        sanitized = {}
        
        for key, value in headers.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = str(value)[:200]
        
        return sanitized
    
    def _sanitize_response(self, response_data: dict) -> dict:
        if not response_data:
            return {}
        
        sanitized = {}
        
        for key, value in response_data.items():
            if isinstance(value, str):
                sanitized[key] = value[:1000]
            elif isinstance(value, (dict, list)):
                sanitized[key] = str(type(value).__name__) + f" (length: {len(value)})"
            else:
                sanitized[key] = str(value)[:500]
        
        return sanitized


api_logger = APILogger()
