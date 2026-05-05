from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

class Settings(BaseSettings):
    """Configuración de la aplicación proxy"""
    
    # Configuración del servidor
    ip_bind: str = os.getenv('IP_BIND')
    port_bind: int = os.getenv('PORT_BIND')
    
    # Configuración del listener (destino)
    ip_listener: str = os.getenv('IP_LISTENER')
    port_listener: int = os.getenv('PORT_LISTENER')
    
    # API Key para autenticación
    api_key: str = os.getenv('API_KEY')
    
    # Límite de peticiones por minuto
    api_rate_limit: int = int(os.getenv('API_RATE_LIMIT', 50))
    
    # Configuración adicional
    debug: bool = False
    log_level: str = os.getenv('LOG_LEVEL')
    
    # Configuración de logging avanzado
    LOG_LEVEL: str = log_level
    LOG_FILE: str = os.getenv('LOG_FILE')
    LOG_MAX_SIZE: str = os.getenv('LOG_MAX_SIZE')
    LOG_BACKUP_COUNT: int = os.getenv('LOG_BACKUP_COUNT')
    
    # Configuración de métricas
    METRICS_ENABLED: bool = os.getenv('METRICS_ENABLED')
    
    # Configuración de health checks
    HEALTH_CHECK_ENABLED: bool = os.getenv('HEALTH_CHECK_ENABLED')
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instancia global de configuración
settings = Settings()


def get_settings() -> Settings:
    """
    Obtiene la instancia de configuración global.
    
    Returns:
        Settings: Configuración de la aplicación
    """
    return settings
