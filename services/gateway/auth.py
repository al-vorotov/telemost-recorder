from fastapi import Header, HTTPException

from shared.config.settings import get_settings


async def verify_api_secret(x_api_secret: str = Header(..., alias="X-Api-Secret")) -> None:
    settings = get_settings()
    if x_api_secret != settings.bot_api_secret:
        raise HTTPException(status_code=401, detail="Invalid API secret")
