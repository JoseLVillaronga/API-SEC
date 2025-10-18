#!/usr/bin/env python3
"""
Script de inicio para el servidor proxy

Uso:
    python run_server.py
"""

import sys
import os

# Agregar el directorio actual al path para importar los módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.server.app import run_server

if __name__ == "__main__":
    print("🚀 Iniciando servidor proxy...")
    run_server()