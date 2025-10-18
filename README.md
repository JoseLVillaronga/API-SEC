# API Proxy Server - Componente Servidor

Servidor proxy implementado con FastAPI para capturar y procesar solicitudes HTTP.

## Estructura del Proyecto

```
.
├── .env                    # Variables de entorno
├── requirements.txt        # Dependencias Python
├── run_server.py          # Script de inicio
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py    # Configuración con Pydantic
│   └── server/
│       ├── __init__.py
│       ├── app.py         # Aplicación FastAPI principal
│       ├── middleware.py  # Middleware para logging
│       └── routes.py      # Rutas del proxy
```

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

2. Configurar las variables de entorno en el archivo `.env`:
```
IP_BIND=0.0.0.0
PORT_BIND=8000
IP_LISTENER=127.0.0.1
PORT_LISTENER=11434
API_KEY=0480469fba14b87ad14588f6a4877ac19dfb9986be342a88a4535f7b631a753ecdcf003ed8ea61adcf51a30619fd2a664a2aa45037eb801646011a52b32ef761
```

## Ejecución

### Método 1: Usando el script de inicio
```bash
python run_server.py
```

### Método 2: Ejecución directa
```bash
python -m src.server.app
```

### Método 3: Usando uvicorn directamente
```bash
uvicorn src.server.app:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

### Endpoints de información
- `GET /` - Información básica del servidor
- `GET /health` - Health check del servidor
- `GET /info` - Información detallada del servidor

### Endpoint proxy
- `ALL METHODS /{path:path}` - Captura todas las solicitudes HTTP

## Características

- ✅ Captura todos los métodos HTTP (GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD)
- ✅ Preserva todos los headers, query parameters y body de las solicitudes
- ✅ Middleware para logging básico y avanzado
- ✅ Configuración mediante variables de entorno
- ✅ Manejo de errores y excepciones
- ✅ CORS habilitado
- ✅ Estructura modular y extensible

## Logging

El servidor implementa dos niveles de middleware para logging:

1. **LoggingMiddleware**: Registra información básica de solicitudes y respuestas
2. **RequestDataMiddleware**: Captura y registra detalles adicionales como query parameters y body

## Desarrollo

Para modo de desarrollo con recarga automática:
```bash
uvicorn src.server.app:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

## Próximos Pasos

- Implementar cliente de reenvío de solicitudes
- Agregar autenticación mediante API key
- Implementar persistencia de logs
- Agregar métricas y monitoreo