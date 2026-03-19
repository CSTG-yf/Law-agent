from fastapi import APIRouter, HTTPException
from pathlib import Path
from app.schema.config import EnvConfigUpdate, EnvConfigResponse, EnvConfigData
from app.core.constants import HttpStatus, get_message
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
                env_config[key.strip()] = value.strip()
    
    return env_config


def write_env_file(env_config: dict):
    with open(ENV_FILE_PATH, 'w', encoding='utf-8') as f:
        for key, value in env_config.items():
            f.write(f"{key}={value}\n")


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
            current_config[key] = value
        
        write_env_file(current_config)
        
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
