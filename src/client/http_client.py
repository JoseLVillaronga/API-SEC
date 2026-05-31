"""
Cliente HTTP asíncrono basado en httpx.

Este módulo implementa un cliente HTTP asíncrono con soporte para
reintentos, timeouts configurables y manejo de errores.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Union, Tuple
from urllib.parse import urljoin

import httpx
from httpx import AsyncClient, Response, TimeoutException, ConnectError

from src.config.settings import settings

# Configurar logger
logger = logging.getLogger("proxy_client")


class HTTPClient:
    """
    Cliente HTTP asíncrono con soporte para reintentos y configuración avanzada.
    """
    
    def __init__(
        self,
        timeout: float = 180.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0
    ):
        """
        Inicializa el cliente HTTP.
        
        Args:
            timeout: Timeout en segundos para las solicitudes
            max_retries: Número máximo de reintentos
            retry_delay: Delay inicial entre reintentos en segundos
            backoff_factor: Factor de backoff exponencial
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        
        # Configuración del cliente httpx
        self.client_config = {
            "timeout": httpx.Timeout(timeout),
            "follow_redirects": True,
            "verify": False,  # Desactivar verificación SSL para entornos de desarrollo
        }
        
        logger.info(f"HTTPClient initialized with timeout={timeout}s, max_retries={max_retries}")
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """
        Realiza una solicitud HTTP con reintentos.
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE, etc.)
            url: URL completa para la solicitud
            headers: Headers adicionales
            params: Query parameters
            data: Body de la solicitud (form data)
            json: Body de la solicitud (JSON)
            **kwargs: Argumentos adicionales para httpx
            
        Returns:
            Response: Respuesta HTTP
            
        Raises:
            Exception: Si todos los reintentos fallan
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with AsyncClient(**self.client_config) as client:
                    logger.debug(f"Attempt {attempt + 1}/{self.max_retries + 1}: {method} {url}")
                    
                    response = await client.request(
                        method=method.upper(),
                        url=url,
                        headers=headers,
                        params=params,
                        data=data,
                        json=json,
                        **kwargs
                    )
                    
                    logger.debug(f"Response: {response.status_code} from {url}")
                    return response
                    
            except (TimeoutException, ConnectError) as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")
                    
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                break
        
        # Si llegamos aquí, todos los intentos fallaron
        raise last_exception or Exception("Unknown error occurred")
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """Realiza una solicitud GET."""
        return await self._make_request("GET", url, headers=headers, params=params, **kwargs)
    
    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """Realiza una solicitud POST."""
        return await self._make_request("POST", url, headers=headers, params=params, data=data, json=json, **kwargs)
    
    async def put(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """Realiza una solicitud PUT."""
        return await self._make_request("PUT", url, headers=headers, params=params, data=data, json=json, **kwargs)
    
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """Realiza una solicitud DELETE."""
        return await self._make_request("DELETE", url, headers=headers, params=params, **kwargs)
    
    async def patch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """Realiza una solicitud PATCH."""
        return await self._make_request("PATCH", url, headers=headers, params=params, data=data, json=json, **kwargs)
    
    async def options(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """Realiza una solicitud OPTIONS."""
        return await self._make_request("OPTIONS", url, headers=headers, params=params, **kwargs)
    
    async def head(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """Realiza una solicitud HEAD."""
        return await self._make_request("HEAD", url, headers=headers, params=params, **kwargs)
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Response:
        """
        Realiza una solicitud HTTP con cualquier método.
        
        Args:
            method: Método HTTP
            url: URL para la solicitud
            headers: Headers adicionales
            params: Query parameters
            data: Body de la solicitud
            json: Body JSON de la solicitud
            **kwargs: Argumentos adicionales
            
        Returns:
            Response: Respuesta HTTP
        """
        return await self._make_request(method, url, headers=headers, params=params, data=data, json=json, **kwargs)
