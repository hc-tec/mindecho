from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./mindecho.db"
    EAI_BASE_URL: str = "http://127.0.0.1:8000"
    EAI_API_KEY: str = "testkey"
    
    class Config:
        env_file = ".env"

settings = Settings()
