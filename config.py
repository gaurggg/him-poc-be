from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    db_name: str = "technosport_poc"

    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_deployment: str = "gpt-4o"

    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@technosport.demo"
    mail_port: int = 587
    mail_server: str = "smtp.ethereal.email"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    vendor_email: str = "vendor@technosport.demo"
    support_email: str = "support@technosport.demo"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
