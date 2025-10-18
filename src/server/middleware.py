import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# Configurar logger
logger = logging.getLogger("proxy_server")
logger.setLevel(logging.INFO)

# Crear handler para consola si no existe
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de solicitudes HTTP"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Capturar tiempo de inicio
        start_time = time.time()
        
        # Extraer información de la solicitud
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Registrar solicitud entrante
        logger.info(
            f"📥 REQUEST: {method} {url} | IP: {client_ip} | User-Agent: {user_agent}"
        )
        
        # Log de headers (solo en modo debug)
        if logger.isEnabledFor(logging.DEBUG):
            headers = dict(request.headers)
            logger.debug(f"Headers: {headers}")
        
        # Procesar la solicitud
        response = await call_next(request)
        
        # Calcular tiempo de procesamiento
        process_time = time.time() - start_time
        
        # Registrar respuesta
        logger.info(
            f"📤 RESPONSE: {response.status_code} | Time: {process_time:.4f}s"
        )
        
        # Agregar header de tiempo de procesamiento
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class RequestDataMiddleware(BaseHTTPMiddleware):
    """Middleware para capturar y loggear datos de la solicitud"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Capturar query parameters
        query_params = dict(request.query_params)
        if query_params:
            logger.info(f"Query Parameters: {query_params}")
        
        # Capturar body para métodos que lo permiten
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Intentar decodificar como texto
                    try:
                        body_text = body.decode("utf-8")
                        # Limitar longitud para no saturar logs
                        if len(body_text) > 500:
                            body_text = body_text[:500] + "...[truncated]"
                        logger.info(f"Request Body: {body_text}")
                    except UnicodeDecodeError:
                        logger.info(f"Request Body: {len(body)} bytes (binary data)")
            except Exception as e:
                logger.warning(f"Error reading request body: {e}")
        
        # Procesar la solicitud
        response = await call_next(request)
        
        return response