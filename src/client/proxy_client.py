"""
Cliente proxy específico para reenviar solicitudes con autenticación Bearer Token.

Este módulo implementa la lógica de proxy que agrega autenticación,
preserva headers y reenvía solicitudes al servidor destino.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin

from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from .http_client import HTTPClient
from src.config.settings import settings
from src.utils.logging_config import get_logger, get_logger_with_context, log_exception
from src.utils.metrics import get_metrics, Timer
from src.utils.exceptions import (
    ProxyError, ConnectionError, TimeoutError, HTTPError,
    ServiceUnavailableError, ValidationError, ConfigurationError
)

# Configurar logger
logger = get_logger("proxy_client")


class ProxyClient:
    """
    Cliente proxy que reenvía solicitudes agregando autenticación Bearer Token.
    """
    
    def __init__(self):
        """Inicializa el cliente proxy."""
        try:
            self.http_client = HTTPClient()
            self.base_url = f"http://{settings.ip_listener}:{settings.port_listener}"
            self.api_key = settings.api_key
            
            # Validar configuración
            if not settings.ip_listener:
                raise ConfigurationError("Target IP listener not configured", config_key="ip_listener")
            if not settings.port_listener:
                raise ConfigurationError("Target port listener not configured", config_key="port_listener")
            
            logger.info("ProxyClient initialized", extra={
                "target_url": self.base_url,
                "api_key_configured": bool(self.api_key)
            })
            
        except Exception as e:
            logger.error("Failed to initialize ProxyClient", extra={"error": str(e)})
            raise ConfigurationError(f"Failed to initialize ProxyClient: {str(e)}")
    
    def _build_target_url(self, path: str, query_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Construye la URL completa para el servidor destino.
        
        Args:
            path: Path de la solicitud
            query_params: Query parameters (opcional)
            
        Returns:
            str: URL completa
            
        Raises:
            ValidationError: Si el path es inválido
        """
        try:
            # Validar path
            if not path:
                raise ValidationError("Path cannot be empty", field="path", value=path)
            
            # Validar que el path no contenga caracteres peligrosos
            dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
            if any(char in path for char in dangerous_chars):
                raise ValidationError("Path contains invalid characters", field="path", value=path)
            
            # Construir URL base
            url = urljoin(self.base_url, path.lstrip('/'))
            
            # Agregar query parameters si existen
            if query_params:
                from urllib.parse import urlencode
                query_string = urlencode(query_params, doseq=True)
                url = f"{url}?{query_string}"
            
            logger.debug("Target URL built", extra={
                "original_path": path,
                "target_url": url,
                "query_params_count": len(query_params) if query_params else 0
            })
            
            return url
            
        except ValidationError:
            raise
        except Exception as e:
            raise ProxyError(f"Failed to build target URL: {str(e)}", details={
                "path": path,
                "base_url": self.base_url
            })
    
    def _prepare_headers(self, original_headers: Dict[str, str]) -> Dict[str, str]:
        """
        Prepara los headers para la solicitud destino.
        
        Args:
            original_headers: Headers originales de la solicitud
            
        Returns:
            Dict[str, str]: Headers preparados con autenticación
            
        Raises:
            ValidationError: Si los headers son inválidos
        """
        try:
            # Validar headers
            if not isinstance(original_headers, dict):
                raise ValidationError("Headers must be a dictionary", field="headers")
            
            # Copiar headers originales
            headers = {}
            
            # Headers que debemos omitir para evitar conflictos
            headers_to_omit = {
                'host',  # El host debe ser el del destino
                'content-length',  # Se recalcula automáticamente
                'transfer-encoding',  # Se maneja automáticamente
                'connection',  # Se maneja automáticamente
                'keep-alive',  # Se maneja automáticamente
                'proxy-authorization',  # No reenviar autenticación de proxy
                'proxy-connection',  # No reenviar headers de proxy
            }
            
            # Preservar el header Authorization de la solicitud entrante si existe
            auth_header_preserved = False
            
            # Copiar headers originales (excepto los omitidos)
            for key, value in original_headers.items():
                if key.lower() not in headers_to_omit:
                    # Validar que el header no sea demasiado largo
                    if len(str(value)) > 8192:  # 8KB limit
                        logger.warning("Header value too long, truncating", extra={
                            "header_name": key,
                            "original_length": len(str(value))
                        })
                        value = str(value)[:8192]
                    headers[key] = value
                    
                    # Verificar si preservamos el header Authorization
                    if key.lower() == 'authorization':
                        auth_header_preserved = True
                        logger.debug("Preserved Authorization header from incoming request")
            
            # Solo agregar header de autenticación si no existe uno en la solicitud original
            # y si tenemos una API key configurada
            if not auth_header_preserved and self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
                logger.debug("Added Bearer Token authentication header (no original auth found)")
            
            logger.debug("Headers prepared", extra={
                "original_headers_count": len(original_headers),
                "prepared_headers_count": len(headers),
                "auth_preserved": auth_header_preserved,
                "auth_added": not auth_header_preserved and bool(self.api_key)
            })
            
            return headers
            
        except ValidationError:
            raise
        except Exception as e:
            raise ProxyError(f"Failed to prepare headers: {str(e)}", details={
                "headers_count": len(original_headers) if original_headers else 0
            })
    
    async def _prepare_body(self, request: Request) -> Optional[Union[str, bytes, Dict[str, Any]]]:
        """
        Prepara el body de la solicitud para reenviar.
        
        Args:
            request: Solicitud FastAPI original
            
        Returns:
            Body procesado o None
            
        Raises:
            ValidationError: Si el body es inválido
        """
        try:
            # Obtener body de la solicitud
            body = await request.body()
            
            if not body:
                logger.debug("Empty request body")
                return None
            
            # Validar tamaño del body
            max_body_size = 10 * 1024 * 1024  # 10MB
            if len(body) > max_body_size:
                raise ValidationError(f"Request body too large: {len(body)} bytes", field="body", value=len(body))
            
            # Intentar decodificar como JSON si el content-type lo indica
            content_type = request.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type:
                try:
                    import json
                    json_data = json.loads(body.decode('utf-8'))
                    logger.debug("JSON body parsed successfully", extra={
                        "body_size": len(body),
                        "json_keys": list(json_data.keys()) if isinstance(json_data, dict) else "not_dict"
                    })
                    return json_data
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning("Failed to parse JSON body, using raw bytes", extra={
                        "error": str(e),
                        "body_size": len(body)
                    })
                    return body
            
            # Para otros content-types, devolver bytes
            logger.debug("Body prepared as raw bytes", extra={
                "body_size": len(body),
                "content_type": content_type
            })
            return body
            
        except ValidationError:
            raise
        except Exception as e:
            raise ProxyError(f"Failed to prepare request body: {str(e)}", details={
                "content_type": request.headers.get('content-type', ''),
                "body_size": len(body) if 'body' in locals() else 0
            })
    
    async def forward_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        query_params: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> Response:
        """
        Reenvía una solicitud al servidor destino con autenticación.
        
        Args:
            method: Método HTTP
            path: Path de la solicitud
            headers: Headers originales
            query_params: Query parameters
            request: Objeto Request original (para obtener body)
            
        Returns:
            Response: Respuesta FastAPI con los datos del destino
            
        Raises:
            ValidationError: Si los parámetros son inválidos
            ConnectionError: Si hay error de conexión
            TimeoutError: Si hay timeout
            HTTPError: Si hay error HTTP
            ServiceUnavailableError: Si el servicio no está disponible
            ProxyError: Para otros errores del proxy
        """
        # Crear logger con contexto
        context_logger = get_logger_with_context(
            "proxy_client",
            method=method,
            path=path,
            target_url=self.base_url
        )
        
        with Timer("proxy_request_duration", tags={'method': method}):
            try:
                # Validar parámetros
                if not method:
                    raise ValidationError("HTTP method is required", field="method")
                
                valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']
                if method.upper() not in valid_methods:
                    raise ValidationError(f"Invalid HTTP method: {method}", field="method", value=method)
                
                # Construir URL destino
                target_url = self._build_target_url(path, query_params)
                context_logger.info("Forwarding request", extra={
                    "target_url": target_url,
                    "method": method
                })
                
                # Preparar headers con autenticación
                prepared_headers = self._prepare_headers(headers)
                
                # Preparar body si es necesario
                body_data = None
                json_data = None
                
                if request and method.upper() in ['POST', 'PUT', 'PATCH']:
                    body = await self._prepare_body(request)
                    if isinstance(body, dict):
                        json_data = body
                    elif body is not None:
                        body_data = body
                
                # Realizar solicitud HTTP proxyando como stream real
                import httpx
                from starlette.background import BackgroundTask
                
                # Deshabilitamos el timeout estricto de lectura (read timeout) para permitir
                # peticiones de streaming largas (por ejemplo, generación de IA) sin que se corten a los 30s.
                # Mantenemos el timeout de conexión en 30s.
                timeout_config = httpx.Timeout(timeout=None, connect=30.0)
                client = httpx.AsyncClient(verify=False, timeout=timeout_config)
                
                req = client.build_request(
                    method=method.upper(),
                    url=target_url,
                    headers=prepared_headers,
                    content=body_data,
                    json=json_data
                )
                
                try:
                    # Enviar la solicitud en modo stream
                    response = await client.send(req, stream=True)
                except httpx.TimeoutException:
                    await client.aclose()
                    raise TimeoutError("Request to target server timed out", timeout_seconds=30.0)
                except Exception as e:
                    await client.aclose()
                    raise e
                
                context_logger.info("Response stream established with target", extra={
                    "status_code": response.status_code,
                })
                
                # Registrar métricas
                metrics = get_metrics()
                metrics.increment_counter('proxy_requests_success', tags={
                    'method': method,
                    'status_code': str(response.status_code)
                })
                
                # Verificar si la respuesta indica error
                if response.status_code >= 500:
                    await response.aclose()
                    await client.aclose()
                    raise ServiceUnavailableError(
                        f"Target server returned error status: {response.status_code}",
                        service_name="target_server"
                    )
                elif response.status_code >= 400:
                    # Si es error del cliente, leemos el cuerpo para reportarlo, y luego cerramos
                    await response.aread()
                    error_text = response.text
                    await response.aclose()
                    await client.aclose()
                    raise HTTPError(
                        f"Target server returned client error: {response.status_code}",
                        status_code=response.status_code,
                        response_text=error_text
                    )
                
                # Preparar headers de respuesta (omitir algunos que pueden causar conflictos)
                response_headers = {}
                headers_to_omit = {
                    'content-length',  # FastAPI / httpx recalculan o usan chunked
                    'transfer-encoding',
                    'connection',
                    'keep-alive',
                    'content-encoding', # Si el contenido viene comprimido, mejor no pasarlo tal cual si interfiere
                }
                
                for key, value in response.headers.items():
                    if key.lower() not in headers_to_omit:
                        response_headers[key] = value
                
                # Función de limpieza para cerrar el stream y el cliente de forma segura
                async def cleanup():
                    try:
                        await response.aclose()
                    finally:
                        await client.aclose()
                
                # Crear respuesta FastAPI (Streaming)
                if method.upper() == 'HEAD':
                    # Para HEAD, no devolver body
                    await cleanup()
                    return Response(
                        status_code=response.status_code,
                        headers=response_headers
                    )
                else:
                    # Retornamos un StreamingResponse real
                    return StreamingResponse(
                        response.aiter_raw(),
                        status_code=response.status_code,
                        headers=response_headers,
                        media_type=response.headers.get('content-type'),
                        background=BackgroundTask(cleanup)
                    )
            
            except (ValidationError, ConnectionError, TimeoutError, HTTPError, ServiceUnavailableError):
                # Re-lanzar excepciones personalizadas
                raise
            
            except asyncio.TimeoutError:
                raise TimeoutError("Request to target server timed out", timeout_seconds=30.0)
            
            except Exception as e:
                # Manejar errores de conexión específicos
                error_msg = str(e).lower()
                if "connection" in error_msg or "network" in error_msg:
                    raise ConnectionError(f"Connection error: {str(e)}", host=settings.ip_listener, port=settings.port_listener)
                elif "timeout" in error_msg:
                    raise TimeoutError(f"Timeout error: {str(e)}")
                else:
                    raise ProxyError(f"Unexpected error forwarding request: {str(e)}", details={
                        "method": method,
                        "path": path,
                        "target_url": self.base_url
                    })
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con el servidor destino.
        
        Returns:
            Dict con resultado de la prueba
            
        Raises:
            ConnectionError: Si hay error de conexión
            TimeoutError: Si hay timeout
            ServiceUnavailableError: Si el servicio no está disponible
            ProxyError: Para otros errores
        """
        context_logger = get_logger_with_context("proxy_client", target_url=self.base_url)
        
        try:
            context_logger.info("Testing connection to target server")
            
            # Realizar una solicitud simple de health check con timeout
            try:
                response = await asyncio.wait_for(
                    self.http_client.get(f"{self.base_url}/health"),
                    timeout=10.0  # 10 segundos timeout para test
                )
            except asyncio.TimeoutError:
                raise TimeoutError("Connection test timed out", timeout_seconds=10.0)
            
            # Verificar respuesta
            if response.status_code >= 500:
                raise ServiceUnavailableError(
                    f"Target server returned error status: {response.status_code}",
                    service_name="target_server"
                )
            elif response.status_code >= 400:
                raise HTTPError(
                    f"Target server returned client error: {response.status_code}",
                    status_code=response.status_code,
                    response_text=response.text if hasattr(response, 'text') else ''
                )
            
            # Registrar métricas
            metrics = get_metrics()
            metrics.increment_counter('connection_tests_success')
            
            result = {
                "status": "success",
                "target_url": self.base_url,
                "status_code": response.status_code,
                "response": response.text if hasattr(response, 'text') else '',
                "response_time_ms": 0  # TODO: Implementar medición de tiempo
            }
            
            context_logger.info("Connection test successful", extra={
                "status_code": response.status_code,
                "response_size": len(result['response'])
            })
            
            return result
        
        except (ConnectionError, TimeoutError, ServiceUnavailableError, HTTPError):
            # Re-lanzar excepciones personalizadas
            raise
        
        except asyncio.TimeoutError:
            raise TimeoutError("Connection test timed out", timeout_seconds=10.0)
        
        except Exception as e:
            # Manejar errores de conexión específicos
            error_msg = str(e).lower()
            if "connection" in error_msg or "network" in error_msg:
                raise ConnectionError(f"Connection test failed: {str(e)}", host=settings.ip_listener, port=settings.port_listener)
            elif "timeout" in error_msg:
                raise TimeoutError(f"Connection test timeout: {str(e)}")
            else:
                raise ProxyError(f"Unexpected error during connection test: {str(e)}", details={
                    "target_url": self.base_url
                })