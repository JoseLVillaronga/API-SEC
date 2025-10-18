"""
Configuración avanzada de logging para la aplicación proxy.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime

from src.config.settings import get_settings


class StructuredFormatter(logging.Formatter):
    """
    Formateador personalizado para logs estructurados en JSON.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formatea el registro de log como JSON estructurado.
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Agregar campos adicionales si existen
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address
        
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        
        if hasattr(record, "error_code"):
            log_data["error_code"] = record.error_code
        
        # Agregar campos extra si existen
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Formateador para consola con colores.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formatea el registro de log con colores para consola.
        """
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Formato básico para consola
        log_format = (
            f"{color}%(asctime)s - %(name)s - %(levelname)s{reset} - "
            f"%(message)s"
        )
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_format += f"\n{color}%(exc_info)s{reset}"
        
        formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_max_size: Optional[str] = None,
    log_backup_count: Optional[int] = None,
    enable_console: bool = True,
    enable_file: bool = True
) -> None:
    """
    Configura el sistema de logging para la aplicación.
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Ruta del archivo de log
        log_max_size: Tamaño máximo del archivo de log (ej: "10MB")
        log_backup_count: Número de archivos de backup
        enable_console: Habilitar logging a consola
        enable_file: Habilitar logging a archivo
    """
    settings = get_settings()
    
    # Usar valores de configuración si no se proporcionan
    log_level = log_level or getattr(settings, 'LOG_LEVEL', 'INFO')
    log_file = log_file or getattr(settings, 'LOG_FILE', 'logs/proxy.log')
    log_max_size = log_max_size or getattr(settings, 'LOG_MAX_SIZE', '10MB')
    log_backup_count = log_backup_count or getattr(settings, 'LOG_BACKUP_COUNT', 5)
    
    # Convertir nivel de log a constante de logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Crear directorio de logs si no existe
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # Configurar handler para consola
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(ColoredConsoleFormatter())
        root_logger.addHandler(console_handler)
    
    # Configurar handler para archivo
    if enable_file:
        # Convertir tamaño a bytes
        max_bytes = _parse_size(log_max_size)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=log_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    # Configurar loggers específicos
    _configure_specific_loggers(numeric_level)


def _parse_size(size_str: str) -> int:
    """
    Convierte una cadena de tamaño a bytes.
    
    Args:
        size_str: Tamaño como cadena (ej: "10MB", "1GB")
        
    Returns:
        Tamaño en bytes
    """
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        # Asumir bytes si no hay unidad
        return int(size_str)


def _configure_specific_loggers(numeric_level: int) -> None:
    """
    Configura loggers específicos para componentes de la aplicación.
    """
    # Logger para el servidor
    server_logger = logging.getLogger('src.server')
    server_logger.setLevel(numeric_level)
    
    # Logger para el cliente
    client_logger = logging.getLogger('src.client')
    client_logger.setLevel(numeric_level)
    
    # Logger para middleware
    middleware_logger = logging.getLogger('src.server.middleware')
    middleware_logger.setLevel(numeric_level)
    
    # Reducir verbosity de loggers de terceros
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('requests.packages.urllib3').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado con el nombre especificado.
    
    Args:
        name: Nombre del logger
        
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Adaptador de logger para agregar contexto adicional.
    """
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]):
        super().__init__(logger, extra)
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Procesa el mensaje y kwargs para agregar contexto.
        """
        # Agregar campos extra al registro
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs


def get_logger_with_context(
    name: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    **extra_fields
) -> logging.LoggerAdapter:
    """
    Obtiene un logger con contexto adicional.
    
    Args:
        name: Nombre del logger
        request_id: ID de la solicitud
        user_id: ID del usuario
        ip_address: Dirección IP
        **extra_fields: Campos adicionales
        
    Returns:
        Logger con contexto
    """
    logger = get_logger(name)
    
    extra = {}
    if request_id:
        extra['request_id'] = request_id
    if user_id:
        extra['user_id'] = user_id
    if ip_address:
        extra['ip_address'] = ip_address
    
    extra.update(extra_fields)
    
    return LoggerAdapter(logger, extra)


def log_exception(
    logger: logging.Logger,
    exception: Exception,
    message: str = "Exception occurred",
    **extra_fields
) -> None:
    """
    Logea una excepción con contexto adicional.
    
    Args:
        logger: Logger a usar
        exception: Excepción a logear
        message: Mensaje adicional
        **extra_fields: Campos adicionales
    """
    extra = {}
    
    # Agregar información de la excepción si es una excepción personalizada
    if hasattr(exception, 'error_code'):
        extra['error_code'] = exception.error_code
    if hasattr(exception, 'details'):
        extra['error_details'] = exception.details
    
    extra.update(extra_fields)
    
    logger.error(
        f"{message}: {str(exception)}",
        exc_info=True,
        extra=extra
    )