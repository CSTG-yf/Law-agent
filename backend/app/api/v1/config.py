from fastapi import APIRouter, HTTPException
from pathlib import Path
from app.schema.config import EnvConfigUpdate, EnvConfigResponse

router = APIRouter(prefix="/config", tags=["Config"])

ENV_FILE_PATH = Path(__file__).parent.parent.parent.parent / ".env"


def read_env_file():
    if not ENV_FILE_PATH.exists():
        raise HTTPException(status_code=404, detail="Environment file not found")
    
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
        config = read_env_file()
        return EnvConfigResponse(
            status="success",
            message="Configuration retrieved successfully",
            config=config
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read configuration: {str(e)}")


@router.put("/", response_model=EnvConfigResponse)
async def update_config(config_update: EnvConfigUpdate):
    try:
        current_config = read_env_file()
        
        update_data = config_update.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            current_config[key] = value
        
        write_env_file(current_config)
        
        return EnvConfigResponse(
            status="success",
            message="Configuration updated successfully",
            config=current_config
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")
