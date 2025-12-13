/**
 * Script che prepara il frontend per il build
 * 1. Copia sensors.config.json nella cartella public del frontend
 * 2. Scarica i componenti frontend dalla repo GitHub e li salva in src/sensorCard/
 */

const fs = require('fs')
const path = require('path')
const https = require('https')
const http = require('http')

const configPath = path.join(__dirname, '..', 'sensors.config.json')
const publicPath = path.join(__dirname, '..', 'frontend', 'public', 'sensors.config.json')
const sensorCardDir = path.join(__dirname, '..', 'frontend', 'src', 'sensorCard')

// URL della repo GitHub (configurabile via env)
const SENSOR_REGISTRY_URL = process.env.SENSOR_REGISTRY_URL || 'https://raw.githubusercontent.com/edoxb/smart-home-sensors/main'

/**
 * Scarica un file da URL
 */
function downloadFile(url, destPath) {
  return new Promise((resolve, reject) => {
    const protocol = url.startsWith('https') ? https : http
    
    const file = fs.createWriteStream(destPath)
    
    protocol.get(url, (response) => {
      if (response.statusCode === 301 || response.statusCode === 302) {
        // Redirect
        return downloadFile(response.headers.location, destPath).then(resolve).catch(reject)
      }
      
      if (response.statusCode !== 200) {
        file.close()
        fs.unlinkSync(destPath)
        reject(new Error(`HTTP ${response.statusCode}: ${url}`))
        return
      }
      
      response.pipe(file)
      
      file.on('finish', () => {
        file.close()
        resolve()
      })
    }).on('error', (err) => {
      file.close()
      if (fs.existsSync(destPath)) {
        fs.unlinkSync(destPath)
      }
      reject(err)
    })
  })
}

/**
 * Scarica i componenti frontend dalla repo GitHub
 */
async function downloadFrontendComponents() {
  try {
    // Leggi sensors.config.json
    if (!fs.existsSync(configPath)) {
      console.warn('⚠ sensors.config.json non trovato, salto download componenti')
      // Crea comunque un index.ts vuoto per evitare errori TypeScript
      if (!fs.existsSync(sensorCardDir)) {
        fs.mkdirSync(sensorCardDir, { recursive: true })
      }
      const indexPath = path.join(sensorCardDir, 'index.ts')
      fs.writeFileSync(indexPath, '// Nessun componente disponibile\n')
      return
    }
    
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'))
    const enabledSensors = config.enabled_sensors || []
    
    // Crea cartella sensorCard se non esiste
    if (!fs.existsSync(sensorCardDir)) {
      fs.mkdirSync(sensorCardDir, { recursive: true })
      console.log('✓ Creata cartella frontend/src/sensorCard/')
    }
    
    if (enabledSensors.length === 0) {
      console.log('ℹ Nessun sensore abilitato, salto download componenti')
      // Crea comunque un index.ts vuoto
      const indexPath = path.join(sensorCardDir, 'index.ts')
      fs.writeFileSync(indexPath, '// Nessun componente disponibile\n')
      return
    }
    
    // Scarica componenti per ogni sensore abilitato
    const downloadedComponents = []
    for (const sensorId of enabledSensors) {
      const sensorConfig = config.sensors?.[sensorId]
      if (!sensorConfig || !sensorConfig.component) {
        console.warn(`⚠ Sensore ${sensorId} senza componente, saltato`)
        continue
      }
      
      const componentName = sensorConfig.component
      const componentPath = path.join(sensorCardDir, `${componentName}.tsx`)
      
      // URL del componente nella repo GitHub
      const componentUrl = `${SENSOR_REGISTRY_URL}/${sensorId}/frontend/${componentName}.tsx`
      
      try {
        console.log(`📥 Download componente ${componentName} per ${sensorId}...`)
        await downloadFile(componentUrl, componentPath)
        console.log(`✓ Componente ${componentName} scaricato`)
        downloadedComponents.push(componentName)
      } catch (error) {
        console.warn(`⚠ Errore download componente ${componentName}: ${error.message}`)
        // Non blocca il build se un componente non si scarica
      }
    }
    
    // Crea file index.ts che esporta tutti i componenti scaricati (necessario per Vite)
    const indexLines = []
    downloadedComponents.forEach(componentName => {
      if (fs.existsSync(path.join(sensorCardDir, `${componentName}.tsx`))) {
        indexLines.push(`export { default as ${componentName} } from './${componentName}'`)
      }
    })
    
    const indexPath = path.join(sensorCardDir, 'index.ts')
    if (indexLines.length > 0) {
      fs.writeFileSync(indexPath, indexLines.join('\n') + '\n')
      console.log(`✓ Creato file index.ts con ${indexLines.length} componenti esportati`)
    } else {
      // Crea comunque un index.ts vuoto per evitare errori
      fs.writeFileSync(indexPath, '// Nessun componente disponibile\n')
      console.log('⚠ Nessun componente scaricato, creato index.ts vuoto')
    }
  } catch (error) {
    console.error('Errore download componenti frontend:', error)
    // Crea comunque un index.ts vuoto per evitare errori TypeScript
    if (!fs.existsSync(sensorCardDir)) {
      fs.mkdirSync(sensorCardDir, { recursive: true })
    }
    const indexPath = path.join(sensorCardDir, 'index.ts')
    fs.writeFileSync(indexPath, '// Errore nel download dei componenti\n')
  }
}

// Esegui preparazione (async)
(async () => {
  try {
    // 1. Copia sensors.config.json nella cartella public
    const publicDir = path.dirname(publicPath)
    if (!fs.existsSync(publicDir)) {
      fs.mkdirSync(publicDir, { recursive: true })
    }

    if (fs.existsSync(configPath)) {
      fs.copyFileSync(configPath, publicPath)
      console.log('✓ sensors.config.json copiato in frontend/public/')
    } else {
      console.warn('⚠ sensors.config.json non trovato nella root')
    }

    // 2. Scarica componenti frontend dalla repo GitHub
    await downloadFrontendComponents()
    console.log('✓ Preparazione frontend completata')
  } catch (error) {
    console.error('Errore preparazione frontend:', error)
    process.exit(1)
  }
})()

