import logging
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Response, HTTPException, Query
from fastapi.responses import JSONResponse

# Importaciones locales
from src.client.proxy_client import ProxyClient
from src.utils.logging_config import get_logger, get_logger_with_context, log_exception
from src.utils.metrics import get_metrics, Timer
from src.utils.exceptions import (
    ProxyError, ConnectionError, TimeoutError, HTTPError,
    ServiceUnavailableError, ValidationError
)

# Configurar logger
logger = get_logger("proxy_server.routes")

# Instancia global del cliente proxy
proxy_client = ProxyClient()


# Crear router principal
proxy_router = APIRouter()


@proxy_router.get("/")
async def root():
    """Endpoint raíz que muestra información básica del servidor"""
    return {
        "message": "API Proxy Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "info": "/info",
            "test-connection": "/test-connection",
            "proxy": "/{path:path}"
        }
    }


@proxy_router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Endpoint de health check para verificar que el servidor está funcionando
    
    Returns:
        Dict con estado del servidor
    """
    return {"status": "healthy", "service": "proxy-server"}


@proxy_router.get("/info")
async def server_info() -> Dict[str, Any]:
    """
    Endpoint que muestra información del servidor proxy
    
    Returns:
        Dict con información del servidor
    """
    return {
        "service": "API Proxy Server",
        "version": "1.0.0",
        "methods_supported": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
        "status": "active"
    }


@proxy_router.get("/test-connection")
async def test_target_connection() -> Dict[str, Any]:
    """
    Endpoint para probar la conexión con el servidor destino
    
    Returns:
        Dict con resultado de la prueba de conexión
    """
    with Timer("test_connection_duration"):
        try:
            metrics = get_metrics()
            metrics.increment_counter('connection_tests_total')
            
            context_logger = get_logger_with_context("proxy_server.routes")
            context_logger.info("Testing connection to target server")
            result = await proxy_client.test_connection()
            
            metrics.increment_counter('connection_tests_success')
            logger.info("Connection test successful")
            
            return result
            
        except ConnectionError as e:
            metrics = get_metrics()
            metrics.increment_counter('connection_tests_failed', tags={'error_type': 'connection_error'})
            
            context_logger = get_logger_with_context("proxy_server.routes")
            log_exception(context_logger, e, "Connection test failed")
            
            return {
                "status": "error",
                "error": e.message,
                "error_code": e.error_code,
                "details": e.details,
                "message": "Failed to test connection to target server"
            }
            
        except TimeoutError as e:
            metrics = get_metrics()
            metrics.increment_counter('connection_tests_failed', tags={'error_type': 'timeout_error'})
            
            context_logger = get_logger_with_context("proxy_server.routes")
            log_exception(context_logger, e, "Connection test timeout")
            
            return {
                "status": "error",
                "error": e.message,
                "error_code": e.error_code,
                "details": e.details,
                "message": "Connection test timed out"
            }
            
        except ServiceUnavailableError as e:
            metrics = get_metrics()
            metrics.increment_counter('connection_tests_failed', tags={'error_type': 'service_unavailable'})
            
            context_logger = get_logger_with_context("proxy_server.routes")
            log_exception(context_logger, e, "Target service unavailable")
            
            return {
                "status": "error",
                "error": e.message,
                "error_code": e.error_code,
                "details": e.details,
                "message": "Target service is unavailable"
            }
            
        except Exception as e:
            metrics = get_metrics()
            metrics.increment_counter('connection_tests_failed', tags={'error_type': 'unknown_error'})
            
            context_logger = get_logger_with_context("proxy_server.routes")
            log_exception(context_logger, e, "Unexpected error during connection test")
            
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to test connection to target server"
            }


@proxy_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_request(
    request: Request,
    path: str,
    # Capturar todos los query parameters posibles
    query_params: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Endpoint que captura todas las solicitudes HTTP y las reenvía al servidor destino
    
    Args:
        request: Objeto de solicitud FastAPI
        path: Path de la URL solicitada
        query_params: Parámetros de consulta (opcional)
    
    Returns:
        Response: Respuesta HTTP del servidor destino
    """
    # Generar ID de solicitud para tracking
    request_id = f"{int(time.time() * 1000)}-{hash(str(request.url)) % 10000}"
    
    # Guardar request_id en el estado para uso en middleware
    request.state.request_id = request_id
    
    # Crear logger con contexto
    context_logger = get_logger_with_context(
        "proxy_server.routes",
        request_id=request_id,
        ip_address=request.client.host if request.client else None,
        method=request.method,
        path=f"/{path}"
    )
    
    with Timer("request_duration", tags={'method': request.method}):
        try:
            # Inicializar métricas
            metrics = get_metrics()
            metrics.increment_counter('requests_total', tags={
                'method': request.method,
                'path': path[:50]  # Limitar longitud del path
            })
            
            # Capturar información de la solicitud
            method = request.method
            url = str(request.url)
            headers = dict(request.headers)
            
            # Validar solicitud
            if not path or path.isspace():
                raise ValidationError("Path cannot be empty", field="path", value=path)
            
            # Capturar query parameters de forma explícita
            query_dict = dict(request.query_params)
            
            # Logging de la solicitud recibida
            context_logger.info("PROXY REQUEST RECEIVED", extra={
                "method": method,
                "path": f"/{path}",
                "full_url": url,
                "headers_count": len(headers),
                "query_params_count": len(query_dict)
            })
            
            # Capturar body para métodos que lo permiten
            body_size = 0
            if method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    body_size = len(body) if body else 0
                    if body:
                        # Intentar decodificar como texto
                        try:
                            body_text = body.decode("utf-8")
                            context_logger.info("Request body captured", extra={
                                "body_size": body_size,
                                "body_preview": body_text[:200] + "..." if len(body_text) > 200 else body_text
                            })
                        except UnicodeDecodeError:
                            context_logger.info("Binary request body captured", extra={
                                "body_size": body_size
                            })
                except Exception as e:
                    context_logger.warning("Error reading request body", extra={
                        "error": str(e)
                    })
            
            context_logger.info("FORWARDING REQUEST TO TARGET SERVER")
            
            # Reenviar la solicitud usando el cliente proxy
            response = await proxy_client.forward_request(
                method=method,
                path=f"/{path}",
                headers=headers,
                query_params=query_dict,
                request=request
            )
            
            # Registrar métricas de respuesta
            metrics.increment_counter('responses_total', tags={
                'method': method,
                'status_code': str(response.status_code)
            })
            
            metrics.observe_histogram('response_size_bytes', len(response.body) if hasattr(response, 'body') else 0)
            
            context_logger.info("RESPONSE FROM TARGET", extra={
                "status_code": response.status_code,
                "response_size": len(response.body) if hasattr(response, 'body') else 0
            })
            
            return response
            
        except ValidationError as e:
            metrics = get_metrics()
            metrics.increment_counter('requests_failed', tags={'error_type': 'validation_error'})
            
            log_exception(context_logger, e, "Request validation failed")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": e.message,
                    "error_code": e.error_code,
                    "details": e.details,
                    "request_id": request_id
                }
            )
            
        except ConnectionError as e:
            metrics = get_metrics()
            metrics.increment_counter('requests_failed', tags={'error_type': 'connection_error'})
            
            log_exception(context_logger, e, "Connection error during proxy request")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": e.message,
                    "error_code": e.error_code,
                    "details": e.details,
                    "request_id": request_id
                }
            )
            
        except TimeoutError as e:
            metrics = get_metrics()
            metrics.increment_counter('requests_failed', tags={'error_type': 'timeout_error'})
            
            log_exception(context_logger, e, "Timeout during proxy request")
            raise HTTPException(
                status_code=504,
                detail={
                    "error": e.message,
                    "error_code": e.error_code,
                    "details": e.details,
                    "request_id": request_id
                }
            )
            
        except HTTPError as e:
            metrics = get_metrics()
            metrics.increment_counter('requests_failed', tags={'error_type': 'http_error'})
            
            log_exception(context_logger, e, "HTTP error during proxy request")
            status_code = e.status_code if e.status_code else 502
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": e.message,
                    "error_code": e.error_code,
                    "details": e.details,
                    "request_id": request_id
                }
            )
            
        except ServiceUnavailableError as e:
            metrics = get_metrics()
            metrics.increment_counter('requests_failed', tags={'error_type': 'service_unavailable'})
            
            log_exception(context_logger, e, "Target service unavailable")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": e.message,
                    "error_code": e.error_code,
                    "details": e.details,
                    "request_id": request_id
                }
            )
            
        except Exception as e:
            metrics = get_metrics()
            metrics.increment_counter('requests_failed', tags={'error_type': 'unknown_error'})
            
            log_exception(context_logger, e, "Unexpected error during proxy request")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "request_id": request_id
                }
            )