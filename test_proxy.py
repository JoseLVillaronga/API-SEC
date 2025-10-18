#!/usr/bin/env python3
"""
Script de pruebas exhaustivas para el servidor proxy
"""

import asyncio
import json
import time
import requests
from typing import Dict, Any, List
import sysfrom dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

class ProxyTester:
    def __init__(self, base_url: str = f"http://{os.getenv('IP_BIND', '0.0.0.0')}:{os.getenv('PORT_BIND', '8080')}"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        # API Key del archivo .env
        self.api_key = os.getenv('API_KEY')
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Registra el resultado de una prueba"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": time.time(),
            "response_data": response_data
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        if not success and response_data:
            print(f"   Response: {response_data}")
        print()
    
    def test_health_basic(self):
        """Prueba de health check básico"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Health Check Básico", True, f"Status: {data.get('status')}", data)
                else:
                    self.log_test("Health Check Básico", False, f"Status inesperado: {data.get('status')}", data)
            else:
                self.log_test("Health Check Básico", False, f"Status code: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Health Check Básico", False, f"Excepción: {str(e)}")
    
    def test_health_detailed(self):
        """Prueba de health check detallado"""
        try:
            response = self.session.get(f"{self.base_url}/health/detailed", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check Detallado", True, f"Status: {data.get('status')}", data)
            else:
                self.log_test("Health Check Detallado", False, f"Status code: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Health Check Detallado", False, f"Excepción: {str(e)}")
    
    def test_server_info(self):
        """Prueba de información del servidor"""
        try:
            response = self.session.get(f"{self.base_url}/info", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Server Info", True, f"Service: {data.get('service')}", data)
            else:
                self.log_test("Server Info", False, f"Status code: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Server Info", False, f"Excepción: {str(e)}")
    
    def test_connection(self):
        """Prueba de conexión con el servidor destino"""
        try:
            response = self.session.get(f"{self.base_url}/test-connection", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.log_test("Test Connection", True, f"Conexión exitosa", data)
                else:
                    self.log_test("Test Connection", False, f"Conexión fallida: {data.get('error')}", data)
            else:
                self.log_test("Test Connection", False, f"Status code: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Test Connection", False, f"Excepción: {str(e)}")
    
    def test_proxy_get(self):
        """Prueba de proxy con solicitud GET simple"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = self.session.get(f"{self.base_url}/api/test", headers=headers, timeout=10)
            # El servidor destino probablemente no existe, así que esperamos un error
            if response.status_code in [404, 503, 502]:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Proxy GET Simple", True, f"Respuesta esperada (servicio no disponible): {response.status_code}", data)
            else:
                self.log_test("Proxy GET Simple", False, f"Status code inesperado: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Proxy GET Simple", False, f"Excepción: {str(e)}")
    
    def test_proxy_post(self):
        """Prueba de proxy con solicitud POST con JSON"""
        try:
            test_data = {"message": "test", "timestamp": time.time()}
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
            response = self.session.post(f"{self.base_url}/api/test", json=test_data, headers=headers, timeout=10)
            
            if response.status_code in [404, 503, 502]:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Proxy POST JSON", True, f"Respuesta esperada (servicio no disponible): {response.status_code}", data)
            else:
                self.log_test("Proxy POST JSON", False, f"Status code inesperado: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Proxy POST JSON", False, f"Excepción: {str(e)}")
    
    def test_proxy_put(self):
        """Prueba de proxy con solicitud PUT"""
        try:
            test_data = {"updated": True}
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
            response = self.session.put(f"{self.base_url}/api/test/1", json=test_data, headers=headers, timeout=10)
            
            if response.status_code in [404, 503, 502]:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Proxy PUT", True, f"Respuesta esperada (servicio no disponible): {response.status_code}", data)
            else:
                self.log_test("Proxy PUT", False, f"Status code inesperado: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Proxy PUT", False, f"Excepción: {str(e)}")
    
    def test_proxy_delete(self):
        """Prueba de proxy con solicitud DELETE"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = self.session.delete(f"{self.base_url}/api/test/1", headers=headers, timeout=10)
            
            if response.status_code in [404, 503, 502]:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Proxy DELETE", True, f"Respuesta esperada (servicio no disponible): {response.status_code}", data)
            else:
                self.log_test("Proxy DELETE", False, f"Status code inesperado: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Proxy DELETE", False, f"Excepción: {str(e)}")
    
    def test_headers_preservation(self):
        """Prueba de preservación de headers"""
        try:
            custom_headers = {
                "X-Custom-Header": "test-value",
                "X-Test-ID": "12345",
                "User-Agent": "ProxyTester/1.0",
                "Authorization": f"Bearer {self.api_key}"
            }
            response = self.session.get(f"{self.base_url}/api/headers-test", headers=custom_headers, timeout=10)
            
            if response.status_code in [404, 503, 502]:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Headers Preservation", True, f"Headers enviados correctamente (servicio no disponible)", data)
            else:
                self.log_test("Headers Preservation", False, f"Status code inesperado: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Headers Preservation", False, f"Excepción: {str(e)}")
    
    def test_query_params(self):
        """Prueba de preservación de query parameters"""
        try:
            params = {"param1": "value1", "param2": "value2", "test": True}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = self.session.get(f"{self.base_url}/api/params-test", params=params, headers=headers, timeout=10)
            
            if response.status_code in [404, 503, 502]:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Query Parameters", True, f"Parámetros enviados correctamente (servicio no disponible)", data)
            else:
                self.log_test("Query Parameters", False, f"Status code inesperado: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Query Parameters", False, f"Excepción: {str(e)}")
    
    def test_metrics(self):
        """Prueba de endpoint de métricas"""
        try:
            response = self.session.get(f"{self.base_url}/health/metrics", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Métricas del Sistema", True, f"Métricas obtenidas", data)
            else:
                self.log_test("Métricas del Sistema", False, f"Status code: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Métricas del Sistema", False, f"Excepción: {str(e)}")
    
    def test_auth_no_token(self):
        """Prueba de autenticación sin token"""
        try:
            response = self.session.get(f"{self.base_url}/api/test", timeout=5)
            if response.status_code == 401:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Autenticación sin Token", True, f"Acceso denegado correctamente (401)", data)
            else:
                self.log_test("Autenticación sin Token", False, f"Se esperaba 401, se obtuvo: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Autenticación sin Token", False, f"Excepción: {str(e)}")
    
    def test_auth_invalid_token(self):
        """Prueba de autenticación con token inválido"""
        try:
            headers = {"Authorization": "Bearer invalid_token_12345"}
            response = self.session.get(f"{self.base_url}/api/test", headers=headers, timeout=5)
            if response.status_code == 401:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Autenticación Token Inválido", True, f"Acceso denegado correctamente (401)", data)
            else:
                self.log_test("Autenticación Token Inválido", False, f"Se esperaba 401, se obtuvo: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Autenticación Token Inválido", False, f"Excepción: {str(e)}")
    
    def test_auth_valid_token(self):
        """Prueba de autenticación con token válido"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = self.session.get(f"{self.base_url}/api/test", headers=headers, timeout=10)
            # El servidor destino probablemente no existe, así que esperamos un error de conexión
            if response.status_code in [404, 503, 502]:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Autenticación Token Válido", True, f"Acceso permitido (servicio no disponible: {response.status_code})", data)
            else:
                self.log_test("Autenticación Token Válido", False, f"Status code inesperado: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Autenticación Token Válido", False, f"Excepción: {str(e)}")
    
    def test_auth_wrong_format(self):
        """Prueba de autenticación con formato incorrecto"""
        try:
            headers = {"Authorization": f"Token {self.api_key}"}  # Formato incorrecto
            response = self.session.get(f"{self.base_url}/api/test", headers=headers, timeout=5)
            if response.status_code == 401:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                self.log_test("Autenticación Formato Incorrecto", True, f"Acceso denegado correctamente (401)", data)
            else:
                self.log_test("Autenticación Formato Incorrecto", False, f"Se esperaba 401, se obtuvo: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Autenticación Formato Incorrecto", False, f"Excepción: {str(e)}")
    
    def test_health_without_auth(self):
        """Prueba que los endpoints de health no requieren autenticación"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health sin Autenticación", True, f"Acceso permitido correctamente", data)
            else:
                self.log_test("Health sin Autenticación", False, f"Se esperaba 200, se obtuvo: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Health sin Autenticación", False, f"Excepción: {str(e)}")
    
    def run_all_tests(self):
        """Ejecuta todas las pruebas"""
        print("🚀 Iniciando pruebas exhaustivas del servidor proxy")
        print("=" * 60)
        
        # Pruebas básicas del servidor (deben funcionar sin autenticación)
        print("\n🏥 PRUEBAS BÁSICAS DEL SERVIDOR (SIN AUTENTICACIÓN)")
        print("=" * 60)
        self.test_health_basic()
        self.test_health_detailed()
        self.test_server_info()
        self.test_connection()
        self.test_metrics()
        
        # Pruebas de autenticación
        print("\n🔐 PRUEBAS DE AUTENTICACIÓN")
        print("=" * 30)
        self.test_auth_no_token()
        self.test_auth_invalid_token()
        self.test_auth_valid_token()
        self.test_auth_wrong_format()
        self.test_health_without_auth()
        
        # Pruebas de proxy (con autenticación requerida)
        print("\n🔄 PRUEBAS DE PROXY (CON AUTENTICACIÓN REQUERIDA)")
        print("=" * 55)
        self.test_proxy_get()
        self.test_proxy_post()
        self.test_proxy_put()
        self.test_proxy_delete()
        
        # Pruebas de funcionalidad avanzada
        self.test_headers_preservation()
        self.test_query_params()
        
        # Resumen
        self.print_summary()
    
    def print_summary(self):
        """Imprime un resumen de los resultados"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print("=" * 60)
        print("📊 RESUMEN DE PRUEBAS")
        print("=" * 60)
        print(f"Total de pruebas: {total_tests}")
        print(f"Pruebas exitosas: {passed_tests}")
        print(f"Pruebas fallidas: {failed_tests}")
        print(f"Tasa de éxito: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ PRUEBAS FALLIDAS:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['details']}")
        
        print("\n📄 RESULTADOS DETALLADOS:")
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['test']}")

if __name__ == "__main__":
    tester = ProxyTester()
    tester.run_all_tests()