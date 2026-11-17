import json
import requests
import time
import sys

API_URL = "http://localhost:8000/api/v1/telemetry"
TEST_NAME = "idle"
DURATA = 300

print(f"[*] Avvio test Baseline: {TEST_NAME}...")
time.sleep(15)  # Margine di stabilizzazione

start_ts = time.time()
print(f"[*] Esecuzione in idle per {DURATA} secondi...")
time.sleep(DURATA)  # Simulazione durata test (5 min)

end_ts = time.time()
print(f"start: {start_ts:.2f}, end: {end_ts:.2f}")

# 1. Download Riepilogo SCI (JSON) 
# Per l'idle inseriamo 1 Token in modo puramente figurativo per non rompere l'API
summary = requests.get(f"{API_URL}/summary", params={
    "start": start_ts,
    "end": end_ts,
    "functional_units": 1.0
}).json()

with open(f"summary_{TEST_NAME}.json", "w") as f:
    json.dump(summary, f, indent=4)

# 2. Download Serie Storica allineata (CSV)
csv_data = requests.get(f"{API_URL}/timeseries", params={
    "start": start_ts,
    "end": end_ts,
    "format": "csv"
}).text

with open(f"timeseries_{TEST_NAME}.csv", "w") as f:
    f.write(csv_data)

print(f"[+] Test completati. Salvati: summary_{TEST_NAME}.json e timeseries_{TEST_NAME}.csv")
print(f"[+] Potenza Totale di Sistema in Idle: {summary.get('energy_and_power', {}).get('system_total_energy_wh', 0) / (DURATA / 3600):.1f} W")
