import sys
import time
import torch
from transformers import pipeline, AutoTokenizer
from datasets import load_dataset

# 1. PARAMETRI DI AVVIO
# Forza l'uso di 4 thread sulla CPU della VM
torch.set_num_threads(4)

# Legge il modello dalla riga di comando (es. bert-base-uncased, distilbert-base-uncased, roberta-large)
MODEL = sys.argv[1] if len(sys.argv) > 1 else "bert-base-uncased"
# Durata fissa di 300 secondi
DURATION = int(sys.argv[2]) if len(sys.argv) > 2 else 300
# Scelta del dataset: "generico" (Multilingual) o "matematico" (AIME 2025)
TASK_TYPE = sys.argv[3] if len(sys.argv) > 3 else "matematico"

print(f"[*] Inizializzazione Test Green AI...")
print(f"    Modello : {MODEL}")
print(f"    Durata  : {DURATION} secondi")
print(f"    Task    : {TASK_TYPE}")

# 2. CARICAMENTO DEL DATASET DA HUGGING FACE
print(f"[*] Download del dataset in corso...")
if TASK_TYPE == "matematico":
    # Dataset matematico (30 righe)
    dataset_hf = load_dataset("MathArena/aime_2025", split="train")
else:
    # Dataset generico multilingua (180 righe)
    # Assumiamo di usare il subset inglese
    dataset_hf = load_dataset("fedric95/AIME2025-Multilingual", name="english", split="train")

workload = []
for row in dataset_hf:
    # Estraiamo la domanda e la risposta
    problem_text = str(row["problem"]).strip()
    answer_text = str(row["answer"]).strip()
    workload.append({"query": problem_text, "answer": answer_text})

print(f"[*] Caricate {len(workload)} query dal dataset.")

# 3. CARICAMENTO DEL MODELLO E DEL TOKENIZER
print(f"[*] Caricamento di {MODEL} in memoria...")
tokenizer = AutoTokenizer.from_pretrained(MODEL)
# Usiamo la pipeline fill-mask per la famiglia BERT/RoBERTa
clf = pipeline("fill-mask", model=MODEL, tokenizer=tokenizer)

# Identifica il token corretto per il masking ([MASK] per BERT, <mask> per RoBERTa)
mask_token = tokenizer.mask_token

# 4. VARIABILI PER LE METRICHE DEL PROFESSORE
total_tokens_processed = 0
total_queries = 0
correct_answers = 0
total_latency = 0.0

print("[*] Esecuzione del Warm-up hardware...")
with torch.inference_mode():
    clf(f"Hello {mask_token}.")

# Sincronizzazione con il sensore di telemetria
input(">>> PRONTO. Avvia l'API di Grafana e premi INVIO qui per partire... ")

t0 = time.time()
idx = 0

print(f"[*] Esecuzione del workload per {DURATION} secondi. Attendere...")
with torch.inference_mode():
    while time.time() - t0 < DURATION:
        # Peschiamo in modo ciclico dal dataset
        item = workload[idx % len(workload)]
        
        # Adattiamo il problema matematico aggiungendo la frase per il fill-mask
        # Es: "Find the sum of... The answer is [MASK]."
        query_text = f"{item['query']} The answer is {mask_token}."
        expected_answer = item["answer"].lower()
        
        # Inizio misurazione Latenza Query
        q_start = time.time()
        
        # Esecuzione dell'inferenza
        out = clf(query_text)
        
        # Fine Latenza
        q_latency = time.time() - q_start
        total_latency += q_latency
        
        # Estrai la parola predetta con più alta confidenza (il primo risultato della lista)
        predicted_word = out[0]['token_str'].strip().lower()
        
        # --- VERIFICA ACCURATEZZA ---
        if expected_answer == predicted_word:
            correct_answers += 1
            
        # --- CONTEGGIO TOKEN ---
        # Conta quanti token compongono esattamente la stringa passata al modello
        tokens = len(tokenizer.encode(query_text))
        total_tokens_processed += tokens
        
        total_queries += 1
        idx += 1

elapsed = time.time() - t0

# 5. STAMPA DEI RISULTATI PER IL REPORT
print("\n" + "="*55)
print(f" RISULTATI INFERENZA: {MODEL}")
print("="*55)
print(f" - Durata effettiva        : {elapsed:.2f} s")
print(f" - Dataset utilizzato      : {TASK_TYPE} ({len(workload)} problemi unici)")
print(f" - Query elaborate in loop : {total_queries}")
print(f" - Token totali masticati  : {total_tokens_processed}")
print(f" - Risposte Corrette       : {correct_answers} su {total_queries}")
print(f" - Accuratezza Matematica  : {(correct_answers / total_queries) * 100:.2f}%")
print("-" * 55)
print(f" - Latenza Media per Query : {total_latency / total_queries:.4f} s/query")
print(f" - Latenza Media per Token : {total_latency / total_tokens_processed:.5f} s/token")
print(f" - Throughput Token        : {total_tokens_processed / elapsed:.1f} tokens/s")
print("="*55)
