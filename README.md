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

1. Crear y activar un entorno virtual (recomendado):
```bash
python -m venv venv
source venv/bin/activate
```

2. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar las variables de entorno en el archivo `.env`:
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

## Instalar como servicio systemd

Requisitos: tener el entorno virtual creado y las dependencias instaladas.


Aviso sobre .env:
- Este servicio carga variables desde el archivo `.env` en la raíz del proyecto (EnvironmentFile).
- Para comenzar, crea tu configuración a partir del ejemplo:
```bash
cp .env.example .env
```
- Edita al menos: `IP_BIND`, `PORT_BIND`, `IP_LISTENER`, `PORT_LISTENER`, `API_KEY`, `LOG_LEVEL`.
- Cada vez que modifiques `.env`, reinicia el servicio para aplicar cambios:
```bash
sudo systemctl restart api-sec
```
- Mantén secretos fuera del repositorio (no subas `.env` a control de versiones).

Comandos principales:
```bash
sudo scripts/install_systemd_service.sh api-sec
sudo systemctl status api-sec
journalctl -u api-sec -f
sudo systemctl restart api-sec
sudo systemctl enable api-sec
sudo systemctl disable api-sec
```

Desinstalar el servicio:
```bash
sudo systemctl disable --now api-sec
sudo rm /etc/systemd/system/api-sec.service
sudo systemctl daemon-reload
```

Nota: asegúrate de que el script sea ejecutable (permisos recomendados 755):
```bash
chmod 755 scripts/install_systemd_service.sh
```


## Pruebas rápidas con curl

Validación rápida de autenticación y reenvío:

- Solicitud válida (token correcto):
```bash
curl -X POST http://localhost:8010/api/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"model":"gpt-oss:20b","prompt":"Hello"}'
```

- Solicitud inválida (token erróneo):
```bash
curl -X POST http://localhost:8010/api/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer WRONG_TOKEN" \
  -d '{"model":"gpt-oss:20b","prompt":"Hello"}'
# Esperado: 401 {"error":"Invalid authentication token"}
```

Notas:
- El endpoint de destino puede responder en modo streaming (múltiples líneas JSON).
- Sustituye YOUR_API_KEY por el valor real configurado en tu `.env`.


Para modo de desarrollo con recarga automática:
```bash
uvicorn src.server.app:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

## Próximos Pasos

- Implementar cliente de reenvío de solicitudes
- Agregar autenticación mediante API key
- Implementar persistencia de logs
- Agregar métricas y monitoreo