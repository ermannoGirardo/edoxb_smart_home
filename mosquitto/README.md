# Mosquitto MQTT Broker

Questo container fornisce un broker MQTT locale per la comunicazione tra sensori e Edge Hub.

## Configurazione

- **Porta MQTT**: `1883` (standard)
- **Porta WebSocket**: `9001` (per client web)
- **Hostname Docker**: `mosquitto` (accessibile da altri container)

## Connessione

### Da altri container Docker:
```
mqtt://mosquitto:1883
```

### Da host locale:
```
mqtt://localhost:1883
```

## Configurazione

Il file `config/mosquitto.conf` contiene la configurazione del broker.

**⚠️ IMPORTANTE**: La configurazione attuale permette connessioni anonime (`allow_anonymous true`). 
Per produzione, configurare autenticazione con `password_file`.

## Volumi

- `mosquitto_data`: Persistenza dati MQTT
- `mosquitto_log`: Log del broker

## Topic consigliati

### Sensori → Edge Hub:
- `sensors/{sensor_name}/status` - Stato del sensore
- `sensors/{sensor_name}/data` - Dati del sensore

### Edge Hub → Sensori:
- `sensors/{sensor_name}/command` - Comandi al sensore

### Edge Hub → AWS IoT Core:
- `edge-hub/sensors/data` - Dati normalizzati da inviare a IoT Core

