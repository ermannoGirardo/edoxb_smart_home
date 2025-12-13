import { useState, useEffect, lazy, Suspense } from 'react'
import type { ComponentType } from 'react'
import './App.css'
import PinModal from './pinmodal/PinModal'
import AddSensor from './addSensor/AddSensor'

// Interfaccia comune per i componenti sensori
interface SensorControlProps {
  sensorName: string
}

// Componenti sensori caricati dinamicamente
const sensorComponents: Record<string, React.LazyExoticComponent<ComponentType<SensorControlProps>>> = {}

interface SensorStatus {
  name: string
  type: string
  ip: string
  port: number | null
  connected: boolean
  last_update: string | null
  enabled: boolean
  actions: Record<string, string> | null
  template_id?: string | null
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [sensors, setSensors] = useState<SensorStatus[]>([])
  const [isLoadingSensors, setIsLoadingSensors] = useState(false)
  const [sensorsError, setSensorsError] = useState<string | null>(null)
  const [deletingSensor, setDeletingSensor] = useState<string | null>(null)
  const [sensorsConfigLoaded, setSensorsConfigLoaded] = useState(false)
  const [fullscreenSensor, setFullscreenSensor] = useState<string | null>(null)

  // Carica configurazione sensori all'avvio
  useEffect(() => {
    fetch('/sensors.config.json')
      .then(res => res.json())
      .then(config => {
        console.log('📋 Configurazione sensori caricata:', config)
        
        // Usa import.meta.glob per pre-caricare tutti i componenti disponibili (Vite lo risolve a build time)
        const componentModules = import.meta.glob('./sensorCard/*.tsx', { eager: false }) as Record<string, () => Promise<{ default: ComponentType<SensorControlProps> }>>
        
        // Lazy load solo i componenti abilitati - OTTIMIZZATO: carica solo il componente necessario
        config.enabled_sensors?.forEach((sensorId: string) => {
          const componentName = config.sensors?.[sensorId]?.component
          if (componentName) {
            console.log(`📥 Registrazione componente ${componentName} per sensore ${sensorId}`)
            
            // Trova il path del componente nel glob
            const componentPath = `./sensorCard/${componentName}.tsx`
            const moduleLoader = componentModules[componentPath]
            
            if (moduleLoader) {
              // Carica solo il componente specifico quando serve (code splitting ottimizzato)
              sensorComponents[sensorId] = lazy(() => 
                moduleLoader()
                  .then(module => {
                    console.log(`✓ Componente ${componentName} caricato con successo`)
                    return module as { default: ComponentType<SensorControlProps> }
                  })
                  .catch((error) => {
                    console.error(`✗ Errore caricamento componente ${componentName}:`, error)
                    // Restituisce un componente che mostra un messaggio di errore
                    const ErrorComponent: ComponentType<SensorControlProps> = ({ sensorName }: SensorControlProps) => (
                      <div style={{ 
                        padding: '2rem', 
                        textAlign: 'center', 
                        color: '#F4B342' 
                      }}>
                        <h2>Errore caricamento componente</h2>
                        <p>Il componente {componentName} non è stato trovato o ha un errore.</p>
                        <p style={{ fontSize: '0.9rem', marginTop: '1rem' }}>
                          Sensore: {sensorName}
                        </p>
                        <p style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: '#999' }}>
                          Verifica che il file esista in frontend/src/sensorCard/
                        </p>
                      </div>
                    )
                    return { 
                      default: ErrorComponent
                    }
                  })
              )
            } else {
              console.warn(`⚠ Componente ${componentName} non trovato nel glob (path: ${componentPath})`)
            }
          } else {
            console.warn(`⚠ Sensore ${sensorId} senza componente specificato`)
          }
        })
        console.log('📦 Componenti registrati:', Object.keys(sensorComponents))
        setSensorsConfigLoaded(true)
      })
      .catch((error) => {
        console.error('❌ Errore caricamento configurazione sensori:', error)
        console.warn('Configurazione sensori non trovata, nessun sensore custom caricato')
        setSensorsConfigLoaded(true)
      })
  }, [])

  useEffect(() => {
    if (isAuthenticated && sensorsConfigLoaded) {
      fetchSensors()
    }
  }, [isAuthenticated, sensorsConfigLoaded])

  const fetchSensors = async () => {
    setIsLoadingSensors(true)
    setSensorsError(null)
    
    try {
      // Prima richiesta: ottieni subito lo stato cached (veloce, non bloccante)
      const response = await fetch('http://localhost:8000/sensors/?check_connection=false')
      if (!response.ok) {
        throw new Error(`Errore HTTP! status: ${response.status}`)
      }
      const data = await response.json()
      setSensors(data)  // Mostra subito i dati cached
      setIsLoadingSensors(false)  // L'interfaccia è già reattiva
      
      // Seconda richiesta in background: verifica le connessioni (non blocca l'interfaccia)
      // Usa una Promise senza await per eseguire in background
      fetch('http://localhost:8000/sensors/?check_connection=true')
        .then(connectionResponse => {
          if (connectionResponse.ok) {
            return connectionResponse.json()
          }
          throw new Error(`HTTP ${connectionResponse.status}`)
        })
        .then(updatedData => {
          console.log('Connessioni verificate, aggiornamento dati:', updatedData)
          setSensors(updatedData)  // Aggiorna quando arrivano i nuovi dati
        })
        .catch(connectionError => {
          // Ignora errori nella verifica delle connessioni (non critico)
          console.warn('Errore durante la verifica delle connessioni (non critico):', connectionError)
        })
    } catch (error) {
      if (error instanceof Error) {
        setSensorsError(error.message)
      } else {
        setSensorsError('Errore sconosciuto nel caricamento dei sensori')
      }
      console.error('Errore durante il caricamento dei sensori:', error)
      setIsLoadingSensors(false)
    }
  }

  if (!isAuthenticated) {
    return <PinModal onAuthenticated={() => setIsAuthenticated(true)} />
  }

  const handleDeleteSensor = async (sensorName: string) => {
    // Conferma prima di eliminare
    if (!confirm(`Sei sicuro di voler eliminare il sensore "${sensorName}"?`)) {
      return
    }

    setDeletingSensor(sensorName)
    try {
      // Encoda il nome del sensore per l'URL
      const encodedSensorName = encodeURIComponent(sensorName)
      const response = await fetch(`http://localhost:8000/sensors/${encodedSensorName}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `Errore HTTP: ${response.status}` }))
        throw new Error(errorData.detail || errorData.message || `Errore HTTP: ${response.status}`)
      }
      
      // Ricarica la lista dei sensori
      await fetchSensors()
    } catch (error) {
      if (error instanceof Error) {
        setSensorsError(error.message)
      } else {
        setSensorsError('Errore sconosciuto durante l\'eliminazione del sensore')
      }
      console.error('Errore durante l\'eliminazione del sensore:', error)
    } finally {
      setDeletingSensor(null)
    }
  }


  return (
    <div className="fixed inset-0 min-h-screen">
      <div className="smart-background">
        <div className="floating-orb orb-1"></div>
        <div className="floating-orb orb-2"></div>
        <div className="floating-orb orb-3"></div>
        <div className="floating-orb orb-4"></div>
      </div>
      <div className="w-full h-full overflow-auto p-4 relative z-10">
        <div className="max-w-7xl mx-auto">
          {/* Header con titolo e bottoni */}
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold drop-shadow-2xl" style={{ color: '#F4B342', textShadow: '0 2px 10px rgba(0, 0, 0, 0.3)' }}>
              Dashboard Sensori
            </h1>
            <div className="flex gap-3 items-center">
              <button
                onClick={fetchSensors}
                disabled={isLoadingSensors}
                className="inline-flex items-center gap-2 bg-white/95 hover:bg-white disabled:bg-white/50 disabled:cursor-not-allowed text-[#360185] font-semibold py-2.5 px-5 rounded-lg transition-colors duration-150 shadow-lg hover:shadow-md disabled:shadow-md text-sm"
              >
                {isLoadingSensors ? (
                  <>
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Caricamento...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Aggiorna</span>
                  </>
                )}
              </button>
              <AddSensor onCancel={fetchSensors} onSuccess={fetchSensors} />
            </div>
          </div>

          {/* Sezione Sensori */}
          <div className="mb-8">

            {sensorsError && (
              <div className="mb-4 p-4 bg-white/95 backdrop-blur-sm border-l-4 rounded-lg shadow-lg" style={{ borderLeftColor: '#DE1A58' }}>
                <div className="flex items-start">
                  <svg className="h-5 w-5 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20" style={{ color: '#DE1A58' }}>
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <p className="font-semibold mb-1" style={{ color: '#DE1A58' }}>Errore</p>
                    <p className="text-sm" style={{ color: '#8F0177' }}>{sensorsError}</p>
                  </div>
                </div>
              </div>
            )}

            {isLoadingSensors && sensors.length === 0 ? (
              <div className="bg-white/95 backdrop-blur-md rounded-xl shadow-2xl p-8 text-center border" style={{ borderColor: '#8F0177', boxShadow: '0 10px 40px rgba(54, 1, 133, 0.3)' }}>
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 mb-4" style={{ borderBottomColor: '#360185' }}></div>
                <p className="font-medium" style={{ color: '#360185' }}>Caricamento sensori...</p>
              </div>
            ) : sensors.length === 0 ? (
              <div className="bg-white/95 backdrop-blur-md rounded-xl shadow-2xl p-8 text-center border" style={{ borderColor: '#8F0177', boxShadow: '0 10px 40px rgba(54, 1, 133, 0.3)' }}>
                <svg className="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ color: '#8F0177' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="font-medium" style={{ color: '#360185' }}>Nessun sensore trovato</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 gap-3">
                {sensors.map((sensor, index) => (
                  <div
                    key={sensor.name}
                    onClick={() => {
                      // Se il sensore ha un template_id, apri fullscreen
                      if (sensor.template_id && sensorComponents[sensor.template_id]) {
                        setFullscreenSensor(sensor.name)
                      }
                    }}
                    className="backdrop-blur-lg rounded-lg shadow-xl p-4 hover:shadow-lg transition-all duration-150 border-2"
                    style={{ 
                      background: 'linear-gradient(135deg, rgba(54, 1, 133, 0.85), rgba(143, 1, 119, 0.8))',
                      borderColor: '#F4B342',
                      boxShadow: '0 10px 40px rgba(0, 0, 0, 0.4)',
                      animation: `fadeInUp 0.5s ease-out ${index * 0.1}s both`,
                      cursor: sensor.template_id && sensorComponents[sensor.template_id] ? 'pointer' : 'default'
                    }}
                  >
                    {/* Nome */}
                    <h3 className="text-lg font-bold mb-3" style={{ color: '#FFFFFF', textShadow: '0 2px 4px rgba(0, 0, 0, 0.3)' }}>
                      {sensor.name}
                    </h3>

                    {/* Tipo - mostra template_id se disponibile, altrimenti type */}
                    <div className="mb-2">
                      <span className="text-xs" style={{ color: '#F4B342' }}>Tipo:</span>
                      <span className="ml-2 font-semibold" style={{ color: '#FFFFFF' }}>
                        {sensor.template_id 
                          ? sensor.template_id
                              .split('_')
                              .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                              .join(' ')
                          : sensor.type.toUpperCase()}
                      </span>
                    </div>

                    {/* IP */}
                    <div className="mb-2">
                      <span className="text-xs" style={{ color: '#F4B342' }}>IP:</span>
                      <span className="ml-2 font-mono text-xs" style={{ color: '#FFFFFF' }}>
                        {sensor.ip}
                      </span>
                    </div>

                    {/* Stato Connessione */}
                    <div className="flex items-center justify-between mt-3 pt-2 border-t" style={{ borderColor: 'rgba(244, 179, 66, 0.3)' }}>
                      <span className="text-xs font-medium" style={{ color: '#F4B342' }}>Stato:</span>
                      <span 
                        className="px-2 py-1 rounded text-xs font-bold"
                        style={{ 
                          color: sensor.connected ? '#22c55e' : '#ef4444',
                          backgroundColor: sensor.connected ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        }}
                      >
                        {sensor.connected ? '✓ CONNESSO' : '✗ DISCONNESSO'}
                      </span>
                    </div>

                    {/* Pulsante Elimina (non cliccabile per aprire fullscreen) */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation() // Evita che apra fullscreen
                        handleDeleteSensor(sensor.name)
                      }}
                      disabled={deletingSensor === sensor.name}
                      className="w-full mt-3 px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 disabled:opacity-50 border-2"
                      style={{
                        background: deletingSensor === sensor.name
                          ? 'linear-gradient(135deg, #8F0177, #360185)'
                          : 'linear-gradient(135deg, #DE1A58, #8F0177)',
                        borderColor: '#DE1A58',
                        color: '#FFFFFF'
                      }}
                      onMouseEnter={(e) => {
                        if (deletingSensor !== sensor.name) {
                          e.currentTarget.style.background = 'linear-gradient(135deg, #8F0177, #DE1A58)'
                          e.currentTarget.style.boxShadow = '0 2px 8px rgba(222, 26, 88, 0.4)'
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (deletingSensor !== sensor.name) {
                          e.currentTarget.style.background = 'linear-gradient(135deg, #DE1A58, #8F0177)'
                          e.currentTarget.style.boxShadow = 'none'
                        }
                      }}
                    >
                      {deletingSensor === sensor.name ? (
                        <span className="flex items-center justify-center gap-1">
                          <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Eliminazione...
                        </span>
                      ) : (
                        <span className="flex items-center justify-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Elimina
                        </span>
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal Fullscreen per componente sensore */}
      {fullscreenSensor && (() => {
        const sensor = sensors.find(s => s.name === fullscreenSensor)
        console.log('🔍 Fullscreen sensor:', sensor)
        console.log('📋 Template ID:', sensor?.template_id)
        console.log('📦 Componenti disponibili:', Object.keys(sensorComponents))
        console.log('🔗 Componente per template_id:', sensor?.template_id ? sensorComponents[sensor.template_id] : 'N/A')
        
        if (!sensor) {
          console.warn('⚠ Sensore non trovato:', fullscreenSensor)
          return (
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 10000,
              backgroundColor: '#360185',
              padding: '2rem',
              color: '#F4B342',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column'
            }}>
              <h1>Sensore non trovato</h1>
              <p>Il sensore "{fullscreenSensor}" non esiste.</p>
              <button
                onClick={() => setFullscreenSensor(null)}
                style={{
                  marginTop: '1rem',
                  padding: '0.5rem 1rem',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                ✕ Chiudi
              </button>
            </div>
          )
        }
        
        if (!sensor.template_id) {
          console.warn('⚠ Sensore senza template_id:', sensor.name)
          return (
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 10000,
              backgroundColor: '#360185',
              padding: '2rem',
              color: '#F4B342',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column'
            }}>
              <h1>Sensore senza template</h1>
              <p>Il sensore "{sensor.name}" non ha un template_id associato.</p>
              <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
                Questo sensore è stato creato come "custom" e non ha un'interfaccia dedicata.
              </p>
              <button
                onClick={() => setFullscreenSensor(null)}
                style={{
                  marginTop: '1rem',
                  padding: '0.5rem 1rem',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                ✕ Chiudi
              </button>
            </div>
          )
        }
        
        if (!sensorComponents[sensor.template_id]) {
          console.warn(`⚠ Componente non trovato per template_id: ${sensor.template_id}`)
          console.warn('Componenti disponibili:', Object.keys(sensorComponents))
          return (
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 10000,
              backgroundColor: '#360185',
              padding: '2rem',
              color: '#F4B342',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column'
            }}>
              <h1>Componente non disponibile</h1>
              <p>Il componente per il template "{sensor.template_id}" non è stato trovato.</p>
              <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
                Verifica che il sensore sia abilitato in sensors.config.json
              </p>
              <p style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: '#999' }}>
                Template ID: {sensor.template_id}
              </p>
              <button
                onClick={() => setFullscreenSensor(null)}
                style={{
                  marginTop: '1rem',
                  padding: '0.5rem 1rem',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                ✕ Chiudi
              </button>
            </div>
          )
        }
        
        return (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 10000,
              backgroundColor: '#360185',
              overflow: 'auto'
            }}
          >
            {/* Header */}
            <div style={{
              position: 'sticky',
              top: 0,
              padding: '1rem',
              backgroundColor: 'rgba(54, 1, 133, 0.95)',
              borderBottom: '2px solid #F4B342',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              zIndex: 10001
            }}>
              <h1 style={{ color: '#F4B342', margin: 0, fontSize: '1.5rem' }}>
                {sensor.name}
              </h1>
              <button
                onClick={() => setFullscreenSensor(null)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                ✕ Chiudi
              </button>
            </div>

            {/* Componente del plugin in fullscreen */}
            <div style={{ padding: '2rem' }}>
              <Suspense fallback={
                <div style={{ textAlign: 'center', padding: '2rem', color: '#F4B342' }}>
                  Caricamento interfaccia...
                </div>
              }>
                {(() => {
                  const Component = sensorComponents[sensor.template_id!]
                  console.log('🎨 Render componente per template_id:', sensor.template_id)
                  if (!Component) {
                    console.error('❌ Component è undefined!')
                    return (
                      <div style={{ padding: '2rem', textAlign: 'center', color: '#F4B342' }}>
                        <h2>Errore: Componente non definito</h2>
                        <p>Template ID: {sensor.template_id}</p>
                      </div>
                    )
                  }
                  return <Component sensorName={sensor.name} />
                })()}
              </Suspense>
            </div>
          </div>
        )
      })()}
    </div>
  )
}

export default App
