/**
 * Script che genera le variabili d'ambiente da sensors.config.json
 * per docker-compose
 */

const fs = require('fs')
const path = require('path')

const configPath = path.join(__dirname, '..', 'sensors.config.json')
const envPath = path.join(__dirname, '..', '.env.sensors')

try {
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'))
  const enabledSensors = config.enabled_sensors || []
  
  // Genera file .env con le variabili
  const envContent = `# File generato automaticamente da sensors.config.json
# Non modificare manualmente - modifica sensors.config.json invece

ENABLED_SENSORS=${enabledSensors.join(',')}
SENSOR_REGISTRY_URL=${process.env.SENSOR_REGISTRY_URL || 'https://raw.githubusercontent.com/edoxb/smart-home-sensors/main'}
`
  
  fs.writeFileSync(envPath, envContent)
  console.log(`✓ File .env.sensors generato con ${enabledSensors.length} sensori abilitati`)
  console.log(`  Sensori: ${enabledSensors.join(', ')}`)
} catch (error) {
  console.error('Errore generazione .env:', error)
  process.exit(1)
}

