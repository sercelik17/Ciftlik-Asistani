import sys
import json
import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8001"

# Kullanıcıdan soru al
question = input("\nSorunuzu yazın: ").strip()

# LOGIN
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "eposta": "teztest@example.com",
        "sifre": "Test12345!"
    }
)

login_response.raise_for_status()
token = login_response.json()["access_token"]

# TEZ ASİSTANINA SOR
response = requests.post(
    f"{BASE_URL}/query/thesis/",
    headers={
        "Authorization": f"Bearer {token}"
    },
    json={
        "question": question
    }
)

response.raise_for_status()

result = response.json()

print("\n============================")
print("ROTA")
print("============================")
print(result["route"])

print("\n============================")
print("CEVAP")
print("============================")
print(result["answer"])

print("\n============================")
print("KAYNAKLAR")
print("============================")
print(
    json.dumps(
        result["sources"],
        ensure_ascii=False,
        indent=2
    )
)