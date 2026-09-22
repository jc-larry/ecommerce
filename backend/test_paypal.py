#!/usr/bin/env python
"""Script de diagnóstico para PayPal"""
import requests
import json

print("🔍 Test de Orden PayPal\n")
print("=" * 80)

url = "http://localhost:8000/api/v1/sales/debug/paypal-test-order"
params = {
    "amount_bob": 50.0,
    "reference_id": "TEST-MARILYN-001"
}

print(f"URL: {url}")
print(f"Parámetros: {json.dumps(params, indent=2)}\n")

try:
    print("📤 Enviando solicitud a PayPal...\n")
    response = requests.post(url, params=params)

    print(f"Status Code: {response.status_code}\n")
    print("Respuesta:")
    print(json.dumps(response.json(), indent=2))

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("Revisa los logs del backend para ver detalles")
