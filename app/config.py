from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    vllm_base_url: str = "http://172.16.28.63:30154"
    request_timeout: float = 120.0
    proxy_port: int = 8000

    class Config:
        env_prefix = "VLLM_PROXY_"


settings = Settings()
