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


from fastapi.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para limitar la cantidad de peticiones (Rate Limiting)"""
    
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60, exclude_paths: list = None):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or ["/health", "/info"]
        # Estructura: { "ip_address": [timestamp1, timestamp2, ...] }
        self.request_records = {}
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Ignorar rutas excluidas
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Inicializar registro si no existe
        if client_ip not in self.request_records:
            self.request_records[client_ip] = []
            
        # Limpiar registros antiguos (fuera de la ventana de tiempo)
        self.request_records[client_ip] = [
            ts for ts in self.request_records[client_ip] 
            if current_time - ts < self.window_seconds
        ]
        
        # Verificar si superó el límite
        if len(self.request_records[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": f"Rate limit reached ({self.max_requests} reqs/{self.window_seconds}s). Please try again later.",
                        "type": "requests",
                        "param": None,
                        "code": "rate_limit_exceeded"
                    }
                }
            )
            
        # Registrar petición permitida
        self.request_records[client_ip].append(current_time)
        
        # Continuar con la petición
        return await call_next(request)