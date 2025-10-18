import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Importaciones locales
from src.config.settings import settings
from src.server.middleware import LoggingMiddleware, RequestDataMiddleware
from src.server.auth_middleware import AuthenticationMiddleware
from src.server.routes import proxy_router
from src.server.health import health_router
from src.utils.logging_config import setup_logging, get_logger, get_logger_with_context, log_exception
from src.utils.metrics import get_metrics
from src.utils.exceptions import (
    ProxyError, ConnectionError, TimeoutError, HTTPError,
    AuthenticationError, RateLimitError, ValidationError,
    ConfigurationError, ServiceUnavailableError,
    ResourceExhaustedError
)


# Configurar logging
def setup_application_logging():
    """Configura el logging de la aplicación usando el sistema avanzado"""
    try:
        # Usar el sistema de logging avanzado
        setup_logging(
            log_level=getattr(settings, 'LOG_LEVEL', 'INFO'),
            log_file=getattr(settings, 'LOG_FILE', 'logs/proxy.log'),
            log_max_size=getattr(settings, 'LOG_MAX_SIZE', '10MB'),
            log_backup_count=getattr(settings, 'LOG_BACKUP_COUNT', 5)
        )
        return get_logger("proxy_server")
    except Exception as e:
        # Fallback a logging básico si hay error
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        logger = logging.getLogger("proxy_server")
        logger.error(f"Failed to setup advanced logging: {e}")
        return logger


# Logger global
logger = setup_application_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación FastAPI"""
    
    # Startup
    logger.info("🚀 Starting Proxy Server...")
    logger.info(f"📍 Bind Address: {settings.ip_bind}:{settings.port_bind}")
    logger.info(f"🎯 Target: {settings.ip_listener}:{settings.port_listener}")
    logger.info(f"🔑 API Key configured: {'Yes' if settings.api_key else 'No'}")
    logger.info(f"🐛 Debug mode: {settings.debug}")
    
    # Inicializar métricas
    metrics = get_metrics()
    logger.info("📊 Metrics system initialized")
    
    # Inicializar health checks
    from src.server.health import get_health_checker
    health_checker = get_health_checker()
    logger.info("🏥 Health checks initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Proxy Server...")
    logger.info("📊 Final metrics: %s", metrics.get_all_metrics())


# Crear aplicación FastAPI
app = FastAPI(
    title="API Proxy Server",
    description="Servidor proxy para capturar y reenviar solicitudes HTTP",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware personalizado
app.add_middleware(RequestDataMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthenticationMiddleware, exclude_paths=["/health"])


# Manejadores de excepciones mejorados
@app.exception_handler(ProxyError)
async def proxy_exception_handler(request: Request, exc: ProxyError):
    """Maneja excepciones de proxy"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'proxy_error'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    log_exception(logger, exc, "Proxy error occurred")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "status_code": 500
        }
    )


@app.exception_handler(ConnectionError)
async def connection_exception_handler(request: Request, exc: ConnectionError):
    """Maneja excepciones de conexión"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'connection_error'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    log_exception(logger, exc, "Connection error occurred")
    
    return JSONResponse(
        status_code=503,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "status_code": 503
        }
    )


@app.exception_handler(TimeoutError)
async def timeout_exception_handler(request: Request, exc: TimeoutError):
    """Maneja excepciones de timeout"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'timeout_error'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    log_exception(logger, exc, "Timeout error occurred")
    
    return JSONResponse(
        status_code=504,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "status_code": 504
        }
    )


@app.exception_handler(HTTPError)
async def http_exception_handler(request: Request, exc: HTTPError):
    """Maneja excepciones HTTP"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'http_error'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    log_exception(logger, exc, "HTTP error occurred")
    
    # Usar el código de estado de la excepción si está disponible
    status_code = exc.status_code if exc.status_code else 500
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "status_code": status_code
        }
    )


@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Maneja excepciones de autenticación"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'authentication_error'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    log_exception(logger, exc, "Authentication error occurred")
    
    return JSONResponse(
        status_code=401,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "status_code": 401
        }
    )


@app.exception_handler(RateLimitError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """Maneja excepciones de límite de tasa"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'rate_limit_error'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    log_exception(logger, exc, "Rate limit error occurred")
    
    return JSONResponse(
        status_code=429,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "status_code": 429
        }
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Maneja excepciones de validación"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'validation_error'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    log_exception(logger, exc, "Validation error occurred")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "status_code": 400
        }
    )


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_exception_handler(request: Request, exc: ServiceUnavailableError):
    """Maneja excepciones de servicio no disponible"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'service_unavailable_error'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    log_exception(logger, exc, "Service unavailable error occurred")
    
    return JSONResponse(
        status_code=503,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "status_code": 503
        }
    )


@app.exception_handler(HTTPException)
async def fastapi_http_exception_handler(request: Request, exc: HTTPException):
    """Maneja excepciones HTTP de FastAPI"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'fastapi_http_error'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    logger.error(f"FastAPI HTTP Exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Maneja excepciones generales no capturadas"""
    metrics = get_metrics()
    metrics.increment_counter('errors_total', tags={'error_type': 'unhandled_exception'})
    
    logger = get_logger_with_context(
        "proxy_server",
        request_id=getattr(request.state, 'request_id', None),
        ip_address=request.client.host if request.client else None
    )
    
    log_exception(logger, exc, "Unhandled exception occurred")
    
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )


# Incluir rutas (el orden es importante - las rutas específicas primero)
app.include_router(health_router, tags=["health"])
app.include_router(proxy_router, tags=["proxy"])


# Función principal para ejecutar el servidor
def run_server():
    """Función para ejecutar el servidor directamente"""
    import uvicorn
    
    logger.info(f"🚀 Starting server on {settings.ip_bind}:{settings.port_bind}")
    
    uvicorn.run(
        "src.server.app:app",
        host=settings.ip_bind,
        port=settings.port_bind,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


# Punto de entrada para ejecución directa
if __name__ == "__main__":
    run_server()