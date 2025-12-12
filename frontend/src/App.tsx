import { useState, useEffect } from 'react'
import './App.css'
import PinModal from './pinmodal/PinModal'
import AddSensor from './addSensor/AddSensor'

interface SensorStatus {
  name: string
  type: string
  ip: string
  port: number | null
  connected: boolean
  last_update: string | null
  enabled: boolean
  actions: Record<string, string> | null
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [sensors, setSensors] = useState<SensorStatus[]>([])
  const [isLoadingSensors, setIsLoadingSensors] = useState(false)
  const [sensorsError, setSensorsError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (isAuthenticated) {
      fetchSensors()
    }
  }, [isAuthenticated])

  const fetchSensors = async () => {
    setIsLoadingSensors(true)
    setSensorsError(null)
    
    try {
      const response = await fetch('http://localhost:8000/sensors/')
      if (!response.ok) {
        throw new Error(`Errore HTTP! status: ${response.status}`)
      }
      const data = await response.json()
      setSensors(data)
    } catch (error) {
      if (error instanceof Error) {
        setSensorsError(error.message)
      } else {
        setSensorsError('Errore sconosciuto nel caricamento dei sensori')
      }
      console.error('Errore durante il caricamento dei sensori:', error)
    } finally {
      setIsLoadingSensors(false)
    }
  }

  if (!isAuthenticated) {
    return <PinModal onAuthenticated={() => setIsAuthenticated(true)} />
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Mai'
    try {
      const date = new Date(dateString)
      return new Intl.DateTimeFormat('it-IT', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }).format(date)
    } catch {
      return dateString
    }
  }

  const handleActionClick = async (sensorName: string, actionName: string) => {
    const actionKey = `${sensorName}-${actionName}`
    setActionLoading(prev => ({ ...prev, [actionKey]: true }))
    
    try {
      const response = await fetch(`http://localhost:8000/sensors/${sensorName}/actions/${actionName}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `Errore HTTP: ${response.status}` }))
        throw new Error(errorData.detail || errorData.message || `Errore HTTP: ${response.status}`)
      }
      
      const result = await response.json()
      console.log('Azione eseguita con successo:', result)
      
      // Mostra notifica di successo
      const successNotification = document.createElement('div')
      successNotification.className = 'fixed top-20 right-4 z-50 max-w-md animate-slide-in'
      successNotification.innerHTML = `
        <div class="bg-white/95 backdrop-blur-md rounded-lg shadow-2xl p-4 border-l-4" style="border-left-color: #F4B342; box-shadow: 0 10px 40px rgba(244, 179, 66, 0.3);">
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20" style="color: #F4B342;">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <p class="text-sm font-semibold" style="color: #F4B342;">Azione eseguita!</p>
              <p class="text-sm mt-1" style="color: #360185;">${actionName} su ${sensorName}</p>
            </div>
          </div>
        </div>
      `
      document.body.appendChild(successNotification)
      
      setTimeout(() => {
        successNotification.remove()
      }, 3000)
      
    } catch (error) {
      console.error('Errore durante l\'esecuzione dell\'azione:', error)
      
      // Mostra notifica di errore
      const errorNotification = document.createElement('div')
      errorNotification.className = 'fixed top-20 right-4 z-50 max-w-md animate-slide-in'
      errorNotification.innerHTML = `
        <div class="bg-white/95 backdrop-blur-md rounded-lg shadow-2xl p-4 border-l-4" style="border-left-color: #DE1A58; box-shadow: 0 10px 40px rgba(222, 26, 88, 0.3);">
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20" style="color: #DE1A58;">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <p class="text-sm font-semibold" style="color: #DE1A58;">Errore</p>
              <p class="text-sm mt-1" style="color: #8F0177;">${error instanceof Error ? error.message : 'Errore sconosciuto'}</p>
            </div>
          </div>
        </div>
      `
      document.body.appendChild(errorNotification)
      
      setTimeout(() => {
        errorNotification.remove()
      }, 3000)
    } finally {
      setActionLoading(prev => ({ ...prev, [actionKey]: false }))
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
                    className="backdrop-blur-lg rounded-lg shadow-xl p-3 hover:shadow-lg transition-shadow duration-150 border-2"
                    style={{ 
                      background: 'linear-gradient(135deg, rgba(54, 1, 133, 0.85), rgba(143, 1, 119, 0.8))',
                      borderColor: '#F4B342',
                      boxShadow: '0 10px 40px rgba(0, 0, 0, 0.4), 0 0 20px rgba(244, 179, 66, 0.2)',
                      animation: `fadeInUp 0.5s ease-out ${index * 0.1}s both`
                    }}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="text-lg font-bold leading-tight" style={{ color: '#FFFFFF', textShadow: '0 2px 4px rgba(0, 0, 0, 0.3)' }}>{sensor.name}</h3>
                      <div className="flex flex-col gap-1">
                        <span
                          className="px-1.5 py-0.5 rounded-full text-[9px] font-semibold border"
                          style={{
                            backgroundColor: sensor.enabled ? 'rgba(244, 179, 66, 0.3)' : 'rgba(143, 1, 119, 0.3)',
                            color: sensor.enabled ? '#F4B342' : '#FFFFFF',
                            borderColor: sensor.enabled ? '#F4B342' : '#8F0177'
                          }}
                        >
                          {sensor.enabled ? 'ON' : 'OFF'}
                        </span>
                        <span
                          className="px-1.5 py-0.5 rounded-full text-[9px] font-semibold border"
                          style={{
                            backgroundColor: sensor.connected ? 'rgba(222, 26, 88, 0.3)' : 'rgba(143, 1, 119, 0.3)',
                            color: sensor.connected ? '#DE1A58' : '#FFFFFF',
                            borderColor: sensor.connected ? '#DE1A58' : '#8F0177'
                          }}
                        >
                          {sensor.connected ? '✓' : '✗'}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-1.5 text-sm mb-2">
                      {/* Campo Connected - Evidente */}
                      <div className="flex justify-between items-center py-2 px-2 rounded border-2 mb-2" style={{ 
                        borderColor: sensor.connected ? '#22c55e' : '#ef4444',
                        backgroundColor: sensor.connected ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)'
                      }}>
                        <span className="font-bold text-sm" style={{ color: '#F4B342' }}>Connected:</span>
                        <span 
                          className="font-bold text-sm px-2 py-1 rounded"
                          style={{ 
                            color: sensor.connected ? '#22c55e' : '#ef4444',
                            backgroundColor: sensor.connected ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)',
                            textShadow: '0 1px 2px rgba(0, 0, 0, 0.3)'
                          }}
                        >
                          {sensor.connected ? '✓ CONNESSO' : '✗ DISCONNESSO'}
                        </span>
                      </div>
                      
                      <div className="flex justify-between items-center py-1 border-b" style={{ borderColor: 'rgba(244, 179, 66, 0.3)' }}>
                        <span className="font-medium" style={{ color: '#F4B342' }}>Tipo:</span>
                        <span className="font-semibold" style={{ color: '#FFFFFF' }}>{sensor.type.toUpperCase()}</span>
                      </div>
                      <div className="flex justify-between items-center py-1 border-b" style={{ borderColor: 'rgba(244, 179, 66, 0.3)' }}>
                        <span className="font-medium" style={{ color: '#F4B342' }}>IP:</span>
                        <span className="font-mono text-xs" style={{ color: '#FFFFFF' }}>{sensor.ip}</span>
                      </div>
                      {sensor.port && (
                        <div className="flex justify-between items-center py-1 border-b" style={{ borderColor: 'rgba(244, 179, 66, 0.3)' }}>
                          <span className="font-medium" style={{ color: '#F4B342' }}>Porta:</span>
                          <span className="font-semibold" style={{ color: '#FFFFFF' }}>{sensor.port}</span>
                        </div>
                      )}
                      <div className="flex justify-between items-center py-1">
                        <span className="font-medium" style={{ color: '#F4B342' }}>Agg:</span>
                        <span className="text-xs" style={{ color: '#FFFFFF' }}>{formatDate(sensor.last_update)}</span>
                      </div>
                    </div>

                    {sensor.actions && Object.keys(sensor.actions).length > 0 && (
                      <div className="mt-2 pt-2 border-t" style={{ borderColor: 'rgba(244, 179, 66, 0.3)' }}>
                        <p className="text-xs font-semibold mb-1.5" style={{ color: '#F4B342' }}>Azioni:</p>
                        <div className="flex flex-wrap gap-1">
                          {Object.keys(sensor.actions).map((actionName) => {
                            const actionKey = `${sensor.name}-${actionName}`
                            const isLoading = actionLoading[actionKey]
                            return (
                              <button
                                key={actionName}
                                onClick={() => handleActionClick(sensor.name, actionName)}
                                disabled={isLoading}
                                className="px-2 py-1 rounded text-[10px] font-medium border transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                                style={{
                                  background: isLoading 
                                    ? 'linear-gradient(135deg, rgba(143, 1, 119, 0.2), rgba(54, 1, 133, 0.15))'
                                    : 'linear-gradient(135deg, rgba(244, 179, 66, 0.2), rgba(244, 179, 66, 0.15))',
                                  color: isLoading ? '#8F0177' : '#F4B342',
                                  borderColor: isLoading ? '#8F0177' : '#F4B342',
                                  cursor: isLoading ? 'wait' : 'pointer'
                                }}
                                onMouseEnter={(e) => {
                                  if (!isLoading) {
                                    e.currentTarget.style.background = 'linear-gradient(135deg, rgba(244, 179, 66, 0.3), rgba(244, 179, 66, 0.2))'
                                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(244, 179, 66, 0.3)'
                                  }
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.background = isLoading 
                                    ? 'linear-gradient(135deg, rgba(143, 1, 119, 0.2), rgba(54, 1, 133, 0.15))'
                                    : 'linear-gradient(135deg, rgba(244, 179, 66, 0.2), rgba(244, 179, 66, 0.15))'
                                  e.currentTarget.style.boxShadow = 'none'
                                }}
                              >
                                {isLoading ? '...' : actionName}
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
