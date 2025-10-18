"""
Middleware de autenticación Bearer Token para el servidor proxy.

Este módulo implementa la validación de autenticación para las solicitudes entrantes,
exigiendo un header Authorization: Bearer <API_KEY> válido.
"""

import logging
from typing import Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config.settings import settings
from src.utils.logging_config import get_logger_with_context
from src.utils.metrics import get_metrics


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware que valida el header Authorization: Bearer <API_KEY>
    en las solicitudes entrantes.
    
    Excluye los endpoints de health check (/health/*) de la validación.
    """
    
    def __init__(self, app, exclude_paths: list = None):
        """
        Inicializa el middleware de autenticación.
        
        Args:
            app: Aplicación FastAPI
            exclude_paths: Lista de paths a excluir de la autenticación
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health"]
        self.logger = get_logger_with_context("auth_middleware")
        self.metrics = get_metrics()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Procesa la solicitud y valida la autenticación.
        
        Args:
            request: Solicitud HTTP entrante
            call_next: Función para continuar con el siguiente middleware
            
        Returns:
            Response: Respuesta HTTP
        """
        # Verificar si el path está en la lista de exclusión
        path = request.url.path
        if any(path.startswith(exclude_path) for exclude_path in self.exclude_paths):
            self.logger.debug(f"Path excluido de autenticación: {path}")
            return await call_next(request)
        
        # Obtener el header Authorization
        auth_header = request.headers.get("Authorization")
        
        # Validar que el header exista
        if not auth_header:
            self._log_unauthorized_attempt(request, "Missing Authorization header")
            self.metrics.increment_counter('auth_failures', tags={'reason': 'missing_header'})
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authorization header is required",
                    "status_code": 401
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validar formato del header (Bearer <token>)
        if not auth_header.startswith("Bearer "):
            self._log_unauthorized_attempt(request, "Invalid Authorization header format")
            self.metrics.increment_counter('auth_failures', tags={'reason': 'invalid_format'})
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authorization header must be in format 'Bearer <token>'",
                    "status_code": 401
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Extraer el token
        token = auth_header[7:]  # Eliminar "Bearer " (7 caracteres)
        
        # Validar que el token no esté vacío
        if not token:
            self._log_unauthorized_attempt(request, "Empty token")
            self.metrics.increment_counter('auth_failures', tags={'reason': 'empty_token'})
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token cannot be empty",
                    "status_code": 401
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validar que el token coincida con la API_KEY configurada
        if token != settings.api_key:
            self._log_unauthorized_attempt(request, "Invalid token")
            self.metrics.increment_counter('auth_failures', tags={'reason': 'invalid_token'})
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Invalid authentication token",
                    "status_code": 401
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Si llegamos aquí, la autenticación es exitosa
        client_ip = request.client.host if request.client else "unknown"
        self.logger.info(f"Authentication successful", extra={
            "client_ip": client_ip,
            "path": path,
            "method": request.method
        })
        self.metrics.increment_counter('auth_success')
        
        # Continuar con el siguiente middleware
        return await call_next(request)
    
    def _log_unauthorized_attempt(self, request: Request, reason: str):
        """
        Registra un intento de acceso no autorizado.
        
        Args:
            request: Solicitud HTTP
            reason: Razón del fallo de autenticación
        """
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        self.logger.warning(
            f"Unauthorized access attempt: {reason}",
            extra={
                "client_ip": client_ip,
                "path": request.url.path,
                "method": request.method,
                "user_agent": user_agent,
                "reason": reason
            }
        )