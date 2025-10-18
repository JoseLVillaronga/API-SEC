"""
Excepciones personalizadas para la aplicación proxy.
"""


class ProxyError(Exception):
    """
    Excepción base para todos los errores del proxy.
    """
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConnectionError(ProxyError):
    """
    Excepción para errores de conexión.
    """
    def __init__(self, message: str, host: str = None, port: int = None, **kwargs):
        super().__init__(message, error_code="CONN_ERROR", **kwargs)
        self.host = host
        self.port = port
        if host and port:
            self.details.update({"host": host, "port": port})


class TimeoutError(ProxyError):
    """
    Excepción para errores de timeout.
    """
    def __init__(self, message: str, timeout_seconds: float = None, **kwargs):
        super().__init__(message, error_code="TIMEOUT_ERROR", **kwargs)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            self.details.update({"timeout_seconds": timeout_seconds})


class HTTPError(ProxyError):
    """
    Excepción para errores HTTP.
    """
    def __init__(self, message: str, status_code: int = None, response_text: str = None, **kwargs):
        super().__init__(message, error_code="HTTP_ERROR", **kwargs)
        self.status_code = status_code
        self.response_text = response_text
        if status_code:
            self.details.update({"status_code": status_code})
        if response_text:
            self.details.update({"response_text": response_text})


class AuthenticationError(ProxyError):
    """
    Excepción para errores de autenticación.
    """
    def __init__(self, message: str, auth_type: str = None, **kwargs):
        super().__init__(message, error_code="AUTH_ERROR", **kwargs)
        self.auth_type = auth_type
        if auth_type:
            self.details.update({"auth_type": auth_type})


class RateLimitError(ProxyError):
    """
    Excepción para errores de límite de tasa.
    """
    def __init__(self, message: str, retry_after: int = None, limit: int = None, **kwargs):
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)
        self.retry_after = retry_after
        self.limit = limit
        if retry_after:
            self.details.update({"retry_after": retry_after})
        if limit:
            self.details.update({"limit": limit})


class ValidationError(ProxyError):
    """
    Excepción para errores de validación de datos.
    """
    def __init__(self, message: str, field: str = None, value: str = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field = field
        self.value = value
        if field:
            self.details.update({"field": field})
        if value:
            self.details.update({"value": value})


class ConfigurationError(ProxyError):
    """
    Excepción para errores de configuración.
    """
    def __init__(self, message: str, config_key: str = None, config_value: str = None, **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        self.config_key = config_key
        self.config_value = config_value
        if config_key:
            self.details.update({"config_key": config_key})
        if config_value:
            self.details.update({"config_value": config_value})


class ServiceUnavailableError(ProxyError):
    """
    Excepción para cuando un servicio no está disponible.
    """
    def __init__(self, message: str, service_name: str = None, **kwargs):
        super().__init__(message, error_code="SERVICE_UNAVAILABLE", **kwargs)
        self.service_name = service_name
        if service_name:
            self.details.update({"service_name": service_name})


class ResourceExhaustedError(ProxyError):
    """
    Excepción para cuando se agotan los recursos.
    """
    def __init__(self, message: str, resource_type: str = None, usage: str = None, **kwargs):
        super().__init__(message, error_code="RESOURCE_EXHAUSTED", **kwargs)
        self.resource_type = resource_type
        self.usage = usage
        if resource_type:
            self.details.update({"resource_type": resource_type})
        if usage:
            self.details.update({"usage": usage})