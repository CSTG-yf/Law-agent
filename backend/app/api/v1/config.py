from fastapi import APIRouter, HTTPException
from pathlib import Path
from langchain_openai import ChatOpenAI
from app.schema.config import EnvConfigUpdate, EnvConfigResponse, EnvConfigData, TestModelRequest, TestModelResponse
from app.core.constants import HttpStatus, get_message
from app.core.config import settings
from app.core.logger import get_logger

router = APIRouter(prefix="/config", tags=["Config"])
logger = get_logger("config_api")

ENV_FILE_PATH = Path(__file__).parent.parent.parent.parent / ".env"


def read_env_file():
    if not ENV_FILE_PATH.exists():
        raise HTTPException(status_code=HttpStatus.NOT_FOUND, detail="Environment file not found")
    
    env_config = {}
    with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if '#' in value:
                    value = value.split('#')[0].strip()
                env_config[key.strip()] = value.strip()
    
    return env_config


def write_env_file(env_config: dict):
    lines = []
    if ENV_FILE_PATH.exists():
        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    updated_keys = set()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in env_config:
                comment = ""
                if '#' in stripped:
                    comment = "   # " + stripped.split('#', 1)[1].strip()
                lines[i] = f"{key}={env_config[key]}{comment}\n"
                updated_keys.add(key)
    
    for key, value in env_config.items():
        if key not in updated_keys:
            lines.append(f"{key}={value}\n")
    
    with open(ENV_FILE_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)


@router.get("/", response_model=EnvConfigResponse)
async def get_config():
    try:
        logger.info("获取配置信息")
        config = read_env_file()
        logger.info(f"获取配置信息成功 - config_keys: {len(config)}")
        return EnvConfigResponse(
            code=HttpStatus.OK,
            status="success",
            message="Configuration retrieved successfully",
            data=EnvConfigData(config=config)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配置信息失败 - error: {str(e)}")
        raise HTTPException(status_code=HttpStatus.INTERNAL_SERVER_ERROR, detail=f"Failed to read configuration: {str(e)}")


@router.put("/", response_model=EnvConfigResponse)
async def update_config(config_update: EnvConfigUpdate):
    try:
        logger.info(f"更新配置 - update_data: {config_update.model_dump(exclude_unset=True)}")
        current_config = read_env_file()
        
        update_data = config_update.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            current_config[key] = str(value)
        
        write_env_file(current_config)
        
        from app.core.config import reload_settings
        reload_settings()
        logger.info("重新加载配置成功")
        
        logger.info(f"更新配置成功 - updated_keys: {list(update_data.keys())}")
        return EnvConfigResponse(
            code=HttpStatus.OK,
            status="success",
            message="Configuration updated successfully",
            data=EnvConfigData(config=current_config)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新配置失败 - error: {str(e)}")
        raise HTTPException(status_code=HttpStatus.INTERNAL_SERVER_ERROR, detail=f"Failed to update configuration: {str(e)}")


@router.post("/test", response_model=TestModelResponse)
async def test_model(request: TestModelRequest):
    try:
        logger.info(f"测试模型配置 - message: {request.message[:50]}")
        
        llm = ChatOpenAI(
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            model=settings.MODEL_NAME,
            temperature=0.7,
            max_tokens=20
        )
        
        response = await llm.ainvoke(request.message)
        
        response_text = response.content if hasattr(response, 'content') else str(response)
        response_text = response_text[:20]
        
        logger.info(f"模型测试成功 - response: {response_text}")
        
        return TestModelResponse(
            code=HttpStatus.OK,
            status="success",
            message="Model test successful",
            data={
                "model": settings.MODEL_NAME,
                "response": response_text,
                "original_message": request.message
            }
        )
    except Exception as e:
        logger.error(f"模型测试失败 - error: {str(e)}")
        return TestModelResponse(
            code=HttpStatus.INTERNAL_SERVER_ERROR,
            status="error",
            message=f"Model test failed: {str(e)}",
            data={
                "model": settings.MODEL_NAME,
                "error": str(e),
                "original_message": request.message
            }
        )


@router.get("/graph", response_model=EnvConfigResponse)
async def get_graph_config():
    """获取知识图谱配置"""
    try:
        logger.info("获取知识图谱配置")
        
        graph_config = {
            "GRAPH_MODEL_NAME": settings.GRAPH_MODEL_NAME,
            "GRAPH_STRICT_MODE": str(settings.GRAPH_STRICT_MODE),
            "GRAPH_MAX_CHUNK_SIZE": str(settings.GRAPH_MAX_CHUNK_SIZE),
            "NEO4J_URI": settings.NEO4J_URI,
            "NEO4J_USER": settings.NEO4J_USER,
            "NEO4J_PASSWORD": "******"  # 隐藏密码
        }
        
        logger.info(f"获取知识图谱配置成功 - config: {graph_config}")
        
        return EnvConfigResponse(
            code=HttpStatus.OK,
            status="success",
            message="Graph configuration retrieved successfully",
            data=EnvConfigData(config=graph_config)
        )
    except Exception as e:
        logger.error(f"获取知识图谱配置失败 - error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graph configuration: {str(e)}"
        )
