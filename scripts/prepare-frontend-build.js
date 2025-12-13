/**
 * Script che prepara il frontend per il build
 * Copia sensors.config.json nella cartella public del frontend
 */

const fs = require('fs')
const path = require('path')

const configPath = path.join(__dirname, '..', 'sensors.config.json')
const publicPath = path.join(__dirname, '..', 'frontend', 'public', 'sensors.config.json')

try {
  // Crea la cartella public se non esiste
  const publicDir = path.dirname(publicPath)
  if (!fs.existsSync(publicDir)) {
    fs.mkdirSync(publicDir, { recursive: true })
  }

  // Copia sensors.config.json nella cartella public
  if (fs.existsSync(configPath)) {
    fs.copyFileSync(configPath, publicPath)
    console.log('✓ sensors.config.json copiato in frontend/public/')
  } else {
    console.warn('⚠ sensors.config.json non trovato nella root')
  }
} catch (error) {
  console.error('Errore preparazione frontend:', error)
  process.exit(1)
}

