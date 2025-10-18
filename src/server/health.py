"""
Endpoints de health check para monitoreo del servicio.
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.utils.metrics import get_metrics
from src.utils.logging_config import get_logger
from src.config.settings import get_settings

health_router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger(__name__)


class HealthResponse(BaseModel):
    """Modelo de respuesta para health checks."""
    status: str
    timestamp: str
    uptime_seconds: int
    version: str = "1.0.0"
    service: str = "proxy-server"


class DetailedHealthResponse(BaseModel):
    """Modelo de respuesta para health checks detallados."""
    status: str
    timestamp: str
    uptime_seconds: int
    version: str = "1.0.0"
    service: str = "proxy-server"
    checks: Dict[str, Dict[str, Any]]
    system_info: Dict[str, Any]


class CheckStatus(BaseModel):
    """Modelo de estado de un chequeo."""
    status: str
    message: str
    last_check: str
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = {}


@dataclass
class HealthStatus:
    """
    Estado de salud de un componente.
    """
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    last_check: datetime
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = None


class HealthChecker:
    """
    Verificador de salud del sistema.
    """
    
    def __init__(self):
        """Inicializa el verificador de salud."""
        self.start_time = datetime.now()
        self._checks: Dict[str, HealthStatus] = {}
        self._lock = threading.RLock()
        
        # Registros de estado
        self._last_db_check = None
        self._last_cache_check = None
        self._last_external_check = None
    
    def register_check(self, name: str, status: HealthStatus) -> None:
        """
        Registra un chequeo de salud.
        
        Args:
            name: Nombre del chequeo
            status: Estado del chequeo
        """
        with self._lock:
            self._checks[name] = status
    
    def get_check(self, name: str) -> Optional[HealthStatus]:
        """
        Obtiene el estado de un chequeo.
        
        Args:
            name: Nombre del chequeo
            
        Returns:
            Estado del chequeo
        """
        with self._lock:
            return self._checks.get(name)
    
    def get_all_checks(self) -> Dict[str, HealthStatus]:
        """
        Obtiene todos los chequeos de salud.
        
        Returns:
            Diccionario con todos los chequeos
        """
        with self._lock:
            return self._checks.copy()
    
    def get_overall_status(self) -> str:
        """
        Calcula el estado general del sistema.
        
        Returns:
            Estado general ("healthy", "degraded", "unhealthy")
        """
        with self._lock:
            if not self._checks:
                return "healthy"
            
            statuses = [check.status for check in self._checks.values()]
            
            if "unhealthy" in statuses:
                return "unhealthy"
            elif "degraded" in statuses:
                return "degraded"
            else:
                return "healthy"
    
    def check_database(self) -> HealthStatus:
        """
        Verifica la salud de la base de datos.
        
        Returns:
            Estado de la base de datos
        """
        start_time = time.time()
        
        try:
            # Simulación de chequeo de base de datos
            # En producción, aquí se verificaría la conexión real
            time.sleep(0.01)  # Simular latencia
            
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus(
                status="healthy",
                message="Database connection successful",
                last_check=datetime.now(),
                response_time_ms=response_time,
                details={
                    "connection_pool": "available",
                    "active_connections": 5,
                    "max_connections": 100
                }
            )
            
            self._last_db_check = datetime.now()
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus(
                status="unhealthy",
                message=f"Database connection failed: {str(e)}",
                last_check=datetime.now(),
                response_time_ms=response_time,
                details={"error": str(e)}
            )
        
        self.register_check("database", status)
        return status
    
    def check_cache(self) -> HealthStatus:
        """
        Verifica la salud del cache.
        
        Returns:
            Estado del cache
        """
        start_time = time.time()
        
        try:
            # Simulación de chequeo de cache
            time.sleep(0.005)  # Simular latencia
            
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus(
                status="healthy",
                message="Cache service operational",
                last_check=datetime.now(),
                response_time_ms=response_time,
                details={
                    "hit_rate": 0.85,
                    "memory_usage": "45%",
                    "evictions": 12
                }
            )
            
            self._last_cache_check = datetime.now()
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus(
                status="degraded",
                message=f"Cache service degraded: {str(e)}",
                last_check=datetime.now(),
                response_time_ms=response_time,
                details={"error": str(e)}
            )
        
        self.register_check("cache", status)
        return status
    
    def check_external_services(self) -> HealthStatus:
        """
        Verifica la salud de servicios externos.
        
        Returns:
            Estado de servicios externos
        """
        start_time = time.time()
        
        try:
            # Simulación de chequeo de servicios externos
            time.sleep(0.02)  # Simular latencia
            
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus(
                status="healthy",
                message="External services accessible",
                last_check=datetime.now(),
                response_time_ms=response_time,
                details={
                    "api_gateway": "healthy",
                    "auth_service": "healthy",
                    "notification_service": "healthy"
                }
            )
            
            self._last_external_check = datetime.now()
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus(
                status="degraded",
                message=f"Some external services unavailable: {str(e)}",
                last_check=datetime.now(),
                response_time_ms=response_time,
                details={"error": str(e)}
            )
        
        self.register_check("external_services", status)
        return status
    
    def check_system_resources(self) -> HealthStatus:
        """
        Verifica los recursos del sistema.
        
        Returns:
            Estado de los recursos del sistema
        """
        try:
            # Obtener métricas del sistema
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determinar estado basado en umbrales
            status = "healthy"
            message = "System resources normal"
            
            if cpu_percent > 90:
                status = "unhealthy"
                message = f"High CPU usage: {cpu_percent}%"
            elif cpu_percent > 70:
                status = "degraded"
                message = f"Elevated CPU usage: {cpu_percent}%"
            elif memory.percent > 90:
                status = "unhealthy"
                message = f"High memory usage: {memory.percent}%"
            elif memory.percent > 80:
                status = "degraded"
                message = f"Elevated memory usage: {memory.percent}%"
            elif disk.percent > 90:
                status = "unhealthy"
                message = f"High disk usage: {disk.percent}%"
            elif disk.percent > 80:
                status = "degraded"
                message = f"Elevated disk usage: {disk.percent}%"
            
            health_status = HealthStatus(
                status=status,
                message=message,
                last_check=datetime.now(),
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024**3)
                }
            )
            
            self.register_check("system_resources", health_status)
            return health_status
            
        except Exception as e:
            status = HealthStatus(
                status="unhealthy",
                message=f"Failed to check system resources: {str(e)}",
                last_check=datetime.now(),
                details={"error": str(e)}
            )
            
            self.register_check("system_resources", status)
            return status


# Instancia global del health checker
_health_checker: Optional[HealthChecker] = None
_health_lock = threading.Lock()


def get_health_checker() -> HealthChecker:
    """
    Obtiene la instancia global del health checker.
    
    Returns:
        Health checker
    """
    global _health_checker
    
    if _health_checker is None:
        with _health_lock:
            if _health_checker is None:
                _health_checker = HealthChecker()
    
    return _health_checker


@health_router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Endpoint básico de health check.
    
    Returns:
        JSON con estado básico del servicio
    """
    health_checker = get_health_checker()
    
    # Realizar chequeos básicos
    system_status = health_checker.check_system_resources()
    
    uptime = datetime.now() - health_checker.start_time
    
    status = "healthy" if system_status.status == "healthy" else "degraded"
    
    response = HealthResponse(
        status=status,
        timestamp=datetime.now().isoformat(),
        uptime_seconds=int(uptime.total_seconds())
    )
    
    if response.status != "healthy":
        raise HTTPException(status_code=503, detail="Service degraded")
    
    return response


@health_router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Endpoint detallado de health check.
    
    Returns:
        JSON con estado detallado de todos los componentes
    """
    health_checker = get_health_checker()
    
    # Realizar todos los chequeos
    checks = {
        "system": health_checker.check_system_resources(),
        "database": health_checker.check_database(),
        "cache": health_checker.check_cache(),
        "external_services": health_checker.check_external_services()
    }
    
    # Calcular estado general
    overall_status = health_checker.get_overall_status()
    
    uptime = datetime.now() - health_checker.start_time
    
    # Construir respuesta
    checks_dict = {}
    for name, check in checks.items():
        checks_dict[name] = {
            "status": check.status,
            "message": check.message,
            "last_check": check.last_check.isoformat(),
            "response_time_ms": check.response_time_ms,
            "details": check.details or {}
        }
    
    system_info = {
        "hostname": psutil.os.uname().nodename if hasattr(psutil.os, 'uname') else "unknown",
        "platform": psutil.os.name,
        "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}"
    }
    
    response = DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        uptime_seconds=int(uptime.total_seconds()),
        checks=checks_dict,
        system_info=system_info
    )
    
    # Determinar código de estado HTTP
    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail="Service unhealthy")
    elif overall_status == "degraded":
        raise HTTPException(status_code=200, detail="Service degraded")
    
    return response


@health_router.get("/ready")
async def readiness_check():
    """
    Endpoint de readiness check (Kubernetes).
    
    Returns:
        JSON con estado de readiness del servicio
    """
    health_checker = get_health_checker()
    
    # Verificar componentes críticos
    system_status = health_checker.check_system_resources()
    db_status = health_checker.check_database()
    
    # El servicio está ready si los componentes críticos están healthy
    is_ready = (
        system_status.status == "healthy" and
        db_status.status == "healthy"
    )
    
    response = {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "system": system_status.status,
            "database": db_status.status
        }
    }
    
    if not is_ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return response


@health_router.get("/live")
async def liveness_check():
    """
    Endpoint de liveness check (Kubernetes).
    
    Returns:
        JSON con estado de liveness del servicio
    """
    health_checker = get_health_checker()
    
    # Verificar si el servicio está vivo (básico)
    uptime = datetime.now() - health_checker.start_time
    is_alive = uptime.total_seconds() > 5  # Considerar vivo después de 5 segundos
    
    response = {
        "status": "alive" if is_alive else "starting",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": int(uptime.total_seconds())
    }
    
    if not is_alive:
        raise HTTPException(status_code=503, detail="Service not alive")
    
    return response


@health_router.get("/metrics")
async def metrics_endpoint():
    """
    Endpoint para obtener métricas del servicio.
    
    Returns:
        JSON con métricas del sistema
    """
    metrics = get_metrics()
    health_checker = get_health_checker()
    
    # Obtener métricas de la aplicación
    app_metrics = metrics.get_all_metrics()
    
    # Obtener métricas del sistema
    system_metrics = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent,
            "used": psutil.virtual_memory().used,
            "free": psutil.virtual_memory().free
        },
        "disk": {
            "total": psutil.disk_usage('/').total,
            "used": psutil.disk_usage('/').used,
            "free": psutil.disk_usage('/').free,
            "percent": psutil.disk_usage('/').percent
        }
    }
    
    response = {
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": int((datetime.now() - health_checker.start_time).total_seconds()),
        "application_metrics": app_metrics,
        "system_metrics": system_metrics
    }
    
    return response