# Sketches - Pattern e Guida

Questa directory contiene gli **sketch** (codice Python) che i sensori fisici devono eseguire per comunicare con il backend.

## Struttura

```
sketches/
├── http/              # Sketch per sensori HTTP
│   ├── temperature_sensor.py
│   ├── basic_sensor.py
│   └── ...
└── websocket/         # Sketch per sensori WebSocket
    ├── temperature_sensor.py
    ├── motion_sensor.py
    ├── basic_sensor.py
    └── ...
```

## Pattern da Seguire

### 1. Struttura Base di uno Sketch

Ogni sketch deve seguire questa struttura:

```python
"""
Docstring: Descrizione dello sketch e del sensore
"""

import ...  # Librerie necessarie
from typing import Dict, Any

# ========== CONFIGURAZIONE ==========
# Definisci tutte le costanti configurabili qui
BACKEND_URL = "http://192.168.1.100:8000"  # Per HTTP
# oppure
BACKEND_HOST = "192.168.1.100"  # Per WebSocket
BACKEND_PORT = 9000
WS_PATH = "/"

SENSOR_NAME = "nome_sensore_01"
POLL_INTERVAL = 5  # secondi

# ========== FUNZIONE PER LEGGERE I DATI ==========
def read_sensor_data() -> Dict[str, Any]:
    """
    PERSONALIZZA QUESTA FUNZIONE per leggere i dati dal tuo sensore.
    
    Returns:
        Dict con i dati del sensore in formato JSON-serializzabile
    """
    # La tua logica qui
    return {
        "value": 42,
        "timestamp": datetime.now().isoformat()
    }

# ========== FUNZIONI DI COMUNICAZIONE ==========
# Funzioni per inviare dati al backend

# ========== LOOP PRINCIPALE ==========
def main():  # Per HTTP (sincrono)
    # oppure
async def main():  # Per WebSocket (asincrono)
    """Loop principale del sensore"""
    # La tua logica qui

if __name__ == "__main__":
    main()  # Per HTTP
    # oppure
    asyncio.run(main())  # Per WebSocket
```

### 2. Pattern per Sketch HTTP

#### Caratteristiche:
- **Sincrono**: Usa `requests` per chiamate HTTP
- **Polling**: Il backend fa polling al sensore (o il sensore invia dati periodicamente)
- **Semplice**: Non richiede connessione persistente

#### Esempio minimo:

```python
import requests
import time
from datetime import datetime

BACKEND_URL = "http://192.168.1.100:8000"
SENSOR_NAME = "my_sensor"
POLL_INTERVAL = 5

def read_sensor_data():
    # Leggi dal sensore fisico
    return {"value": 42, "timestamp": datetime.now().isoformat()}

def main():
    while True:
        data = read_sensor_data()
        # Invia o espone i dati
        print(f"Dati: {data}")
        time.sleep(POLL_INTERVAL)
```

### 3. Pattern per Sketch WebSocket

#### Caratteristiche:
- **Asincrono**: Usa `asyncio` e `websockets`
- **Connessione persistente**: Mantiene una connessione WebSocket aperta
- **Riconnessione automatica**: Gestisce disconnessioni e si riconnette

#### Esempio minimo:

```python
import asyncio
import websockets
import json
from datetime import datetime

BACKEND_HOST = "192.168.1.100"
BACKEND_PORT = 9000
WS_PATH = "/"
SENSOR_NAME = "my_sensor"
SEND_INTERVAL = 5

def read_sensor_data():
    return {"value": 42, "timestamp": datetime.now().isoformat()}

async def connect_and_send_loop():
    uri = f"ws://{BACKEND_HOST}:{BACKEND_PORT}{WS_PATH}"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Connesso!")
                while True:
                    data = read_sensor_data()
                    await websocket.send(json.dumps(data))
                    await asyncio.sleep(SEND_INTERVAL)
        except Exception as e:
            print(f"Errore: {e}. Riconnessione in 5s...")
            await asyncio.sleep(5)

async def main():
    await connect_and_send_loop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

### 1. Gestione Errori
- **Sempre**: Usa try/except per gestire errori di rete e sensore
- **Logging**: Usa `print()` per log (o `logging` per produzione)
- **Riconnessione**: Per WebSocket, implementa riconnessione automatica

### 2. Configurazione
- **Costanti in alto**: Definisci tutte le configurazioni all'inizio
- **Facile personalizzazione**: Rendi facile modificare IP, porte, intervalli
- **Commenti**: Spiega cosa fa ogni sezione

### 3. Dati del Sensore
- **Formato JSON**: I dati devono essere JSON-serializzabili
- **Timestamp**: Includi sempre un timestamp ISO
- **Struttura chiara**: Usa chiavi descrittive (`temperature`, `humidity`, ecc.)

### 4. Naming
- **File**: `{tipo_sensore}_sensor.py` (es: `temperature_sensor.py`)
- **Funzioni**: Nomi descrittivi (`read_sensor_data()`, `send_data_to_backend()`)
- **Variabili**: Uso di MAIUSCOLE per costanti

## Esempi Completi

Vedi i file di esempio nella directory:
- `http/temperature_sensor.py` - Esempio completo HTTP
- `http/basic_sensor.py` - Template base HTTP
- `websocket/temperature_sensor.py` - Esempio completo WebSocket
- `websocket/motion_sensor.py` - Esempio sensore eventi
- `websocket/basic_sensor.py` - Template base WebSocket

## Come Usare uno Sketch

1. **Copia** lo sketch appropriato nella tua directory
2. **Personalizza** la funzione `read_sensor_data()` per il tuo sensore
3. **Configura** le costanti (IP backend, porta, nome sensore)
4. **Installa** le dipendenze necessarie (`requests`, `websockets`, librerie sensore)
5. **Esegui** lo sketch sul dispositivo del sensore

## API Backend

Il backend espone queste API per gestire gli sketch:

- `GET /frontend/sketches` - Lista tutti gli sketch per tutti i protocolli
- `GET /frontend/sketches/{protocol}` - Lista sketch per un protocollo
- `GET /frontend/sketches/{protocol}/{sketch_id}` - Ottieni contenuto di uno sketch

## Note Importanti

- **Nome sensore**: Deve corrispondere a quello configurato nel backend
- **Porta WebSocket**: Verifica la porta assegnata nel backend (può essere auto-assegnata)
- **Formato dati**: I dati devono essere JSON-serializzabili
- **Timestamp**: Usa formato ISO 8601: `datetime.now().isoformat()`













