from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    webhook_url: str = "http://localhost:8000/webhook/mock"

    # Zerodha (Kite Connect) — https://developers.kite.trade
    zerodha_api_key: Optional[str] = None
    zerodha_api_secret: Optional[str] = None
    zerodha_access_token: Optional[str] = None

    # Fyers — https://myapi.fyers.in/dashboard
    fyers_app_id: Optional[str] = None
    fyers_secret_key: Optional[str] = None
    fyers_access_token: Optional[str] = None

    # Angel One (SmartAPI) — https://smartapi.angelone.in/
    angelone_api_key: Optional[str] = None
    angelone_client_id: Optional[str] = None
    angelone_password: Optional[str] = None
    angelone_totp_secret: Optional[str] = None

    # Groww — No official public trading API (REST-based placeholder)
    groww_api_key: Optional[str] = None
    groww_api_secret: Optional[str] = None

    # Upstox — https://account.upstox.com/developer/apps
    upstox_api_key: Optional[str] = None
    upstox_api_secret: Optional[str] = None
    upstox_access_token: Optional[str] = None
    upstox_redirect_uri: Optional[str] = "http://localhost:3000/callback"

    # Dhan — https://api.dhan.co
    dhan_client_id: Optional[str] = None
    dhan_access_token: Optional[str] = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
