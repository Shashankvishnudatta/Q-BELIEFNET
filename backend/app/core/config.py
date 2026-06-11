import json
from typing import Annotated, List, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

RuntimeMode = Literal["demo", "hybrid", "live"]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_ignore_empty=True, 
        extra="ignore"
    )

    APP_NAME: str = "Q-Belief Net API"
    PROJECT_NAME: str = "Q-Belief Net API"
    APP_ENV: str = "local"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    APP_MODE: RuntimeMode = "demo"
    DATA_MODE: RuntimeMode = "demo"
    # Allow frontend domain (modify as needed for production)
    ALLOWED_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:3000", "http://localhost:5173"]
    RAPIDAPI_KEY: str | None = None
    RAPIDAPI_HOST: str = "apidojo-yahoo-finance-v1.p.rapidapi.com"
    YOUTUBE_API_KEY: str | None = None
    WEBSHARE_USERNAME: str | None = None
    WEBSHARE_PASSWORD: str | None = None
    REDDIT_CLIENT_ID: str | None = None
    REDDIT_CLIENT_SECRET: str | None = None
    REDDIT_USER_AGENT: str = "Q-Belief Net/1.0"
    STOCKTWITS_TOKEN: str | None = None
    MARKET_DATA_TICKERS: str = "NVDA,TSLA,AAPL,AMD,MSFT,META,AMZN,GOOGL,PLTR,SMCI,COIN,MARA,JPM,UNH,XOM,V,JNJ,WMT,PG,MA"
    REDIS_URL: str | None = None
    HF_API_KEY: str | None = None
    HF_MODEL_ID: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    ENABLE_EVIDENCE_CACHE: bool = True
    EVIDENCE_CACHE_TTL_SECONDS: int = 300
    ALLOW_LIVE_MODE_DEMO_FALLBACK: bool = False
    ALLOW_STALE_CACHE_ON_PROVIDER_FAILURE: bool = True
    STALE_CACHE_MAX_AGE_SECONDS: int = 1800
    PROVIDER_TIMEOUT_SECONDS: float = 8.0
    PROVIDER_RETRY_COUNT: int = 1
    PROVIDER_CIRCUIT_FAILURE_THRESHOLD: int = 3
    PROVIDER_CIRCUIT_RESET_SECONDS: int = 120
    ENABLE_BACKGROUND_REFRESH: bool = False
    BACKGROUND_REFRESH_INTERVAL_SECONDS: int = 60
    BACKGROUND_REFRESH_SYMBOLS: str = "AAPL,TSLA,NVDA,MSFT,AMZN"
    ENABLE_PERSISTENCE: bool = True
    DATABASE_URL: str = "sqlite:///backend/data/qbeliefnet.db"
    PERSISTENCE_MODE: str = "sqlite"
    MAX_SNAPSHOTS_PER_SYMBOL: int = 100
    ENABLE_MANUAL_REFRESH: bool = True
    MANUAL_REFRESH_TOKEN: str | None = None
    REQUIRE_MANUAL_REFRESH_TOKEN: bool = False
    MAX_MANUAL_REFRESH_SYMBOLS: int = 10

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, list):
            return [origin.strip().rstrip("/") for origin in value if isinstance(origin, str) and origin.strip()]

        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []

            # Accept JSON arrays in env, but gracefully fall back to comma-separated values.
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [
                            origin.strip().rstrip("/")
                            for origin in parsed
                            if isinstance(origin, str) and origin.strip()
                        ]
                except json.JSONDecodeError:
                    pass

            return [origin.strip().rstrip("/") for origin in stripped.split(",") if origin.strip()]

        return ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("APP_MODE", "DATA_MODE", mode="before")
    @classmethod
    def normalize_mode(cls, value):
        mode = str(value or "demo").strip().lower()
        return mode if mode in {"demo", "hybrid", "live"} else "demo"

settings = Settings()
