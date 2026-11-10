import requests
import json
import time

payload = {
    "script": "At 12:15 AM on September 26, 1983, a red siren illuminated a top-secret Soviet bunker outside Moscow. The radar screens confirmed what every officer dreaded: five American nuclear warheads were already in the air.",
    "emotion": "Speak with controlled urgency and mounting dread, deep authoritative baritone documentary tone, crisp articulation, ominous cadence, slightly slower pace.",
    "speed": 0.98
}

print("🚀 Enviando requisição REST para http://localhost:8501/api/v1/narrate...")
start = time.time()
try:
    resp = requests.post("http://localhost:8501/api/v1/narrate", json=payload, timeout=600)
    dur = time.time() - start
    print(f"Status: {resp.status_code} ({dur:.1f}s)")
    try:
        print("Resposta:", json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception:
        print("Resposta texto:", resp.text)
except Exception as e:
    print(f"Erro na requisição: {e}")
