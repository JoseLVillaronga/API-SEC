"""
Utilidades comunes para la aplicación proxy.
"""

from .exceptions import (
    ProxyError,
    ConnectionError,
    TimeoutError,
    HTTPError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    ConfigurationError
)

from .logging_config import setup_logging, get_logger
from .metrics import MetricsCollector, get_metrics

__all__ = [
    # Excepciones
    'ProxyError',
    'ConnectionError', 
    'TimeoutError',
    'HTTPError',
    'AuthenticationError',
    'RateLimitError',
    'ValidationError',
    'ConfigurationError',
    # Logging
    'setup_logging',
    'get_logger',
    # Métricas
    'MetricsCollector',
    'get_metrics'
]