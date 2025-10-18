"""
Sistema de métricas básico para monitoreo de rendimiento.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

from src.config.settings import get_settings


@dataclass
class MetricValue:
    """
    Valor de una métrica con timestamp.
    """
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Counter:
    """
    Contador para métricas incrementales.
    """
    value: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    
    def inc(self, amount: int = 1) -> None:
        """Incrementa el contador."""
        self.value += amount
    
    def reset(self) -> None:
        """Resetea el contador."""
        self.value = 0


@dataclass
class Gauge:
    """
    Gauge para métricas que pueden subir o bajar.
    """
    value: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    
    def set(self, value: float) -> None:
        """Establece el valor."""
        self.value = value
    
    def inc(self, amount: float = 1.0) -> None:
        """Incrementa el valor."""
        self.value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        """Decrementa el valor."""
        self.value -= amount


@dataclass
class Histogram:
    """
    Histograma para distribución de valores.
    """
    buckets: List[float] = field(default_factory=lambda: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0])
    bucket_counts: Dict[float, int] = field(default_factory=dict)
    count: int = 0
    sum: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Inicializa los buckets."""
        for bucket in self.buckets:
            self.bucket_counts[bucket] = 0
    
    def observe(self, value: float) -> None:
        """Observa un valor."""
        self.count += 1
        self.sum += value
        
        for bucket in sorted(self.buckets):
            if value <= bucket:
                self.bucket_counts[bucket] += 1
    
    def get_percentile(self, percentile: float) -> float:
        """
        Calcula un percentil aproximado.
        
        Args:
            percentile: Percentil a calcular (0-100)
            
        Returns:
            Valor del percentil
        """
        if self.count == 0:
            return 0.0
        
        # Implementación simplificada - en producción usar algoritmo más preciso
        threshold = self.count * (percentile / 100)
        
        cumulative = 0
        for bucket in sorted(self.buckets):
            cumulative += self.bucket_counts[bucket]
            if cumulative >= threshold:
                return bucket
        
        return max(self.buckets)


@dataclass
class Summary:
    """
    Summary para estadísticas básicas.
    """
    count: int = 0
    sum: float = 0.0
    min: float = float('inf')
    max: float = float('-inf')
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def observe(self, value: float) -> None:
        """Observa un valor."""
        self.count += 1
        self.sum += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.values.append(value)
    
    def get_mean(self) -> float:
        """Calcula el promedio."""
        return self.sum / self.count if self.count > 0 else 0.0
    
    def get_percentile(self, percentile: float) -> float:
        """
        Calcula un percentil.
        
        Args:
            percentile: Percentil a calcular (0-100)
            
        Returns:
            Valor del percentil
        """
        if not self.values:
            return 0.0
        
        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * (percentile / 100))
        return sorted_values[min(index, len(sorted_values) - 1)]


class MetricsCollector:
    """
    Colector de métricas para la aplicación.
    """
    
    def __init__(self):
        """Inicializa el colector de métricas."""
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self.summaries: Dict[str, Summary] = {}
        self._lock = threading.RLock()
        
        # Métricas por defecto
        self._setup_default_metrics()
    
    def _setup_default_metrics(self) -> None:
        """Configura métricas por defecto."""
        # Contadores
        self.counter('requests_total', 'Total number of requests')
        self.counter('errors_total', 'Total number of errors')
        self.counter('connections_total', 'Total number of connections')
        
        # Gauges
        self.gauge('active_connections', 'Number of active connections')
        self.gauge('memory_usage_mb', 'Memory usage in MB')
        
        # Histograms
        self.histogram('request_duration_seconds', 'Request duration in seconds')
        self.histogram('response_size_bytes', 'Response size in bytes')
        
        # Summaries
        self.summary('response_time_seconds', 'Response time summary')
    
    def counter(self, name: str, description: str = "", tags: Dict[str, str] = None) -> Counter:
        """
        Crea o obtiene un contador.
        
        Args:
            name: Nombre del contador
            description: Descripción
            tags: Etiquetas
            
        Returns:
            Contador
        """
        with self._lock:
            key = self._make_key(name, tags)
            if key not in self.counters:
                self.counters[key] = Counter(tags=tags or {})
            return self.counters[key]
    
    def gauge(self, name: str, description: str = "", tags: Dict[str, str] = None) -> Gauge:
        """
        Crea o obtiene un gauge.
        
        Args:
            name: Nombre del gauge
            description: Descripción
            tags: Etiquetas
            
        Returns:
            Gauge
        """
        with self._lock:
            key = self._make_key(name, tags)
            if key not in self.gauges:
                self.gauges[key] = Gauge(tags=tags or {})
            return self.gauges[key]
    
    def histogram(
        self,
        name: str,
        description: str = "",
        buckets: List[float] = None,
        tags: Dict[str, str] = None
    ) -> Histogram:
        """
        Crea o obtiene un histograma.
        
        Args:
            name: Nombre del histograma
            description: Descripción
            buckets: Buckets del histograma
            tags: Etiquetas
            
        Returns:
            Histograma
        """
        with self._lock:
            key = self._make_key(name, tags)
            if key not in self.histograms:
                self.histograms[key] = Histogram(
                    buckets=buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
                    tags=tags or {}
                )
            return self.histograms[key]
    
    def summary(self, name: str, description: str = "", tags: Dict[str, str] = None) -> Summary:
        """
        Crea o obtiene un summary.
        
        Args:
            name: Nombre del summary
            description: Descripción
            tags: Etiquetas
            
        Returns:
            Summary
        """
        with self._lock:
            key = self._make_key(name, tags)
            if key not in self.summaries:
                self.summaries[key] = Summary(tags=tags or {})
            return self.summaries[key]
    
    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """
        Crea una clave única para una métrica con etiquetas.
        
        Args:
            name: Nombre de la métrica
            tags: Etiquetas
            
        Returns:
            Clave única
        """
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"
    
    def increment_counter(self, name: str, amount: int = 1, tags: Dict[str, str] = None) -> None:
        """
        Incrementa un contador.
        
        Args:
            name: Nombre del contador
            amount: Cantidad a incrementar
            tags: Etiquetas
        """
        counter = self.counter(name, tags=tags)
        counter.inc(amount)
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """
        Establece el valor de un gauge.
        
        Args:
            name: Nombre del gauge
            value: Valor a establecer
            tags: Etiquetas
        """
        gauge = self.gauge(name, tags=tags)
        gauge.set(value)
    
    def observe_histogram(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """
        Observa un valor en un histograma.
        
        Args:
            name: Nombre del histograma
            value: Valor a observar
            tags: Etiquetas
        """
        histogram = self.histogram(name, tags=tags)
        histogram.observe(value)
    
    def observe_summary(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """
        Observa un valor en un summary.
        
        Args:
            name: Nombre del summary
            value: Valor a observar
            tags: Etiquetas
        """
        summary = self.summary(name, tags=tags)
        summary.observe(value)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Obtiene todas las métricas en formato serializable.
        
        Returns:
            Diccionario con todas las métricas
        """
        with self._lock:
            metrics = {}
            
            # Contadores
            metrics['counters'] = {}
            for key, counter in self.counters.items():
                metrics['counters'][key] = {
                    'value': counter.value,
                    'tags': counter.tags
                }
            
            # Gauges
            metrics['gauges'] = {}
            for key, gauge in self.gauges.items():
                metrics['gauges'][key] = {
                    'value': gauge.value,
                    'tags': gauge.tags
                }
            
            # Histograms
            metrics['histograms'] = {}
            for key, histogram in self.histograms.items():
                metrics['histograms'][key] = {
                    'count': histogram.count,
                    'sum': histogram.sum,
                    'bucket_counts': histogram.bucket_counts,
                    'buckets': histogram.buckets,
                    'tags': histogram.tags
                }
            
            # Summaries
            metrics['summaries'] = {}
            for key, summary in self.summaries.items():
                metrics['summaries'][key] = {
                    'count': summary.count,
                    'sum': summary.sum,
                    'min': summary.min,
                    'max': summary.max,
                    'mean': summary.get_mean(),
                    'p50': summary.get_percentile(50),
                    'p95': summary.get_percentile(95),
                    'p99': summary.get_percentile(99),
                    'tags': summary.tags
                }
            
            return metrics
    
    def reset_all(self) -> None:
        """Resetea todas las métricas."""
        with self._lock:
            for counter in self.counters.values():
                counter.reset()
            
            for gauge in self.gauges.values():
                gauge.set(0.0)
            
            self.histograms.clear()
            self.summaries.clear()
            
            # Recrear métricas por defecto
            self._setup_default_metrics()


# Instancia global del colector de métricas
_metrics_collector: Optional[MetricsCollector] = None
_metrics_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """
    Obtiene la instancia global del colector de métricas.
    
    Returns:
        Colector de métricas
    """
    global _metrics_collector
    
    if _metrics_collector is None:
        with _metrics_lock:
            if _metrics_collector is None:
                _metrics_collector = MetricsCollector()
    
    return _metrics_collector


def measure_time(metric_name: str, tags: Dict[str, str] = None):
    """
    Decorador para medir el tiempo de ejecución de una función.
    
    Args:
        metric_name: Nombre de la métrica
        tags: Etiquetas
        
    Returns:
        Decorador
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                get_metrics().observe_histogram(metric_name, duration, tags)
                get_metrics().observe_summary(f"{metric_name}_summary", duration, tags)
        
        return wrapper
    return decorator


class Timer:
    """
    Context manager para medir tiempo.
    """
    
    def __init__(self, metric_name: str, tags: Dict[str, str] = None):
        """
        Inicializa el timer.
        
        Args:
            metric_name: Nombre de la métrica
            tags: Etiquetas
        """
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        """Inicia el timer."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Detiene el timer y registra la métrica."""
        if self.start_time is not None:
            duration = time.time() - self.start_time
            get_metrics().observe_histogram(self.metric_name, duration, self.tags)
            get_metrics().observe_summary(f"{self.metric_name}_summary", duration, self.tags)