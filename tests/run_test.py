import json
import sys
import time
import requests

API_URL = "http://localhost:8000/api/v1/telemetry"
TEST_NAME = sys.argv[1]   # es. ai_distilbert_math
DURATA = 300

print(f"[*] Avvio test: {TEST_NAME}...")
time.sleep(15)

start_ts = time.time()
print("[*] >>> LANCIA ORA LO SCRIPT SULLA VM <<<")
time.sleep(DURATA)
end_ts = time.time()
print(f"start: {start_ts:.2f}, end: {end_ts:.2f}")

print("\n[*] INSERISCI I DATI RESTITUITI DALLO SCRIPT DELLA VM:")
while True:
    try:
        R_tokens = float(input("    -> Token totali masticati (R_tokens) : "))
        tot_queries = float(input("    -> Query elaborate in loop           : "))
        latenza_query = float(input("    -> Latenza Media (s/query)           : "))
        break
    except ValueError:
        print("[!] Errore: Inserisci solo i numeri decimali (usa il punto, es: 4520.0)")

# 1. Download Riepilogo SCI
summary = requests.get(f"{API_URL}/summary", params={
    "start": start_ts, 
    "end": end_ts, 
    "functional_units": R_tokens
}).json()

with open(f"summary_{TEST_NAME}.json", "w") as f:
    json.dump(summary, f, indent=4)

# 2. Download Serie Storica
csv_data = requests.get(f"{API_URL}/timeseries", params={
    "start": start_ts, 
    "end": end_ts, 
    "format": "csv"
}).text

with open(f"timeseries_{TEST_NAME}.csv", "w") as f:
    f.write(csv_data)

# 3. Calcoli richiesti dal professore
# Potenza totale di sistema (Server + Raffreddamento)
sys_energy_wh = summary.get("energy_and_power", {}).get("system_total_energy_wh", 0)
sys_avg_power_w = sys_energy_wh / (DURATA / 3600)
joules_per_query = sys_avg_power_w * latenza_query
joules_per_token = sys_avg_power_w * (latenza_query / (R_tokens / tot_queries))

print(f"\n[+] Salvati: summary_{TEST_NAME}.json e timeseries_{TEST_NAME}.csv")
print(f"[+] SCI Netto (gCO2eq / Token) : {summary.get('sci_framework', {}).get('sci_score_g_co2eq_per_token')}")
print(f"[+] Energia per Query (Joules) : {joules_per_query:.2f} J")
print(f"[+] Energia per Token (Joules) : {joules_per_token:.4f} J")
