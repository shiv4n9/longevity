from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/longevity"
    
    # SSH Credentials
    ssh_username: str
    ssh_password: str
    
    # Jump Host
    jump_host: str = "ttbg-shell012.juniper.net"
    jump_host_username: str = "sshivang"
    jump_host_password: str
    
    # Alternative Credentials
    alt_username: str = ""
    alt_password: str = ""
    
    # Application
    app_name: str = "Longevity Dashboard"
    debug: bool = False
    
    class Config:
        # Use absolute path to .env file
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables

def get_settings():
    return Settings()
