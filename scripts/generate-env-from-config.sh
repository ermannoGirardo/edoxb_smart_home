#!/bin/bash
# Script che genera .env.sensors da sensors.config.json

CONFIG_FILE="sensors.config.json"
ENV_FILE=".env.sensors"

# Estrai enabled_sensors dal JSON
ENABLED_SENSORS=$(cat $CONFIG_FILE | grep -o '"enabled_sensors":\s*\[.*\]' | sed 's/.*\[\(.*\)\].*/\1/' | sed 's/"//g' | sed 's/,//g' | tr '\n' ',' | sed 's/,$//' | sed 's/ //g')

# URL registry (default o da variabile d'ambiente)
REGISTRY_URL="${SENSOR_REGISTRY_URL:-https://raw.githubusercontent.com/tuonome/smart-home-sensors/main}"

# Genera file .env
cat > $ENV_FILE << EOF
# File generato automaticamente da sensors.config.json
# Non modificare manualmente - modifica sensors.config.json invece

ENABLED_SENSORS=$ENABLED_SENSORS
SENSOR_REGISTRY_URL=$REGISTRY_URL
EOF

echo "✓ File .env.sensors generato"
echo "  Sensori: $ENABLED_SENSORS"

