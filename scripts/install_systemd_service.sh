#!/usr/bin/env bash
set -euo pipefail

# Instalador de servicio systemd para API-SEC (FastAPI Proxy)
# Uso:
#   bash scripts/install_systemd_service.sh [nombre-servicio]
# Ejemplo:
#   bash scripts/install_systemd_service.sh api-sec
# Requisitos:
#   - El usuario actual debe tener sudo sin contraseña (NOPASSWD)
#   - systemd disponible (Linux)

SERVICE_NAME="${1:-api-sec}"

# Directorio de la app (raíz del repo)
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="$(id -un)"
GROUP_NAME="$(id -gn)"

# Python del entorno virtual, si existe; de lo contrario usa python del PATH
VENV_PYTHON="$APP_DIR/venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  VENV_PYTHON="$(command -v python)"
fi

# Verificar sudo sin contraseña
if ! sudo -n true 2>/dev/null; then
  echo "[ERROR] Este script requiere que el usuario $USER_NAME tenga sudo sin contraseña (NOPASSWD)." >&2
  echo "        Configure /etc/sudoers y vuelva a intentar." >&2
  exit 1
fi

UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "[INFO] Instalando servicio systemd: $SERVICE_NAME"
echo "[INFO] APP_DIR: $APP_DIR"
echo "[INFO] Python: $VENV_PYTHON"

# Crear unidad systemd
sudo tee "$UNIT_FILE" >/dev/null <<EOF
[Unit]
Description=API-SEC FastAPI Proxy (${SERVICE_NAME})
After=network.target

[Service]
Type=simple
User=${USER_NAME}
Group=${GROUP_NAME}
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
# Carga variables desde .env si existe (opcional)
EnvironmentFile=-${APP_DIR}/.env
# Ejecuta la app como módulo usando el Python del venv (si existe)
ExecStart=${VENV_PYTHON} -m src.server.app
Restart=always
RestartSec=5
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
EOF

# Recargar, habilitar y arrancar
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"
sudo systemctl restart "${SERVICE_NAME}.service"

# Mostrar estado abreviado
sudo systemctl --no-pager --full status "${SERVICE_NAME}.service" || true

echo
echo "[OK] Servicio '${SERVICE_NAME}.service' instalado y arrancado."
echo "    Ver logs: journalctl -u ${SERVICE_NAME}.service -f"
echo "    Detener:  sudo systemctl stop ${SERVICE_NAME}.service"
echo "    Arrancar: sudo systemctl start ${SERVICE_NAME}.service"
echo "    Reiniciar: sudo systemctl restart ${SERVICE_NAME}.service"
echo "    Habilitar al arranque: sudo systemctl enable ${SERVICE_NAME}.service"
echo "    Deshabilitar:          sudo systemctl disable ${SERVICE_NAME}.service"
