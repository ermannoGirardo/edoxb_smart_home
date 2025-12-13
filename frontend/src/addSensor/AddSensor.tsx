import { useState } from 'react'
import type { FieldDefinition, SensorTemplate } from './types'

interface AddSensorProps {
  onCancel?: () => void
  onSuccess?: () => void
}

interface ActionItem {
  id: string
  name: string
  url: string
}

interface SensorTemplateType {
  id: string
  name: string
  description: string
  protocol: string
  required_fields: string[]
  optional_fields: string[]
  default_config: Record<string, any>
  control_interface: string
}

export default function AddSensor({ onCancel, onSuccess }: AddSensorProps) {
  const [showForm, setShowForm] = useState(false)
  const [showTemplateSelection, setShowTemplateSelection] = useState(false)
  const [selectedMode, setSelectedMode] = useState<'custom' | 'template' | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<SensorTemplateType | null>(null)
  const [availableTemplates, setAvailableTemplates] = useState<SensorTemplateType[]>([])
  const [template, setTemplate] = useState<SensorTemplate | null>(null)
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [actionsList, setActionsList] = useState<ActionItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)
  const [enablePolling, setEnablePolling] = useState(false)

  const fetchSensorTemplates = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await fetch('http://localhost:8000/frontend/sensor-templates')
      if (!response.ok) {
        throw new Error(`Errore HTTP! status: ${response.status}`)
      }
      const data = await response.json()
      setAvailableTemplates(data.templates || [])
      setShowTemplateSelection(true)
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message)
      } else {
        setError('Errore sconosciuto')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const fetchTemplate = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await fetch('http://localhost:8000/frontend/sensor-template')
      if (!response.ok) {
        throw new Error(`Errore HTTP! status: ${response.status}`)
      }
      const data = await response.json()
      setTemplate(data)
      setShowForm(true)
      
      // Inizializza i valori di default
      const initialData: Record<string, any> = {
        template_id: 'custom'  // Imposta template_id a 'custom' per sensori custom
      }
      const allFields = [...data.common_fields, ...data.http_fields, ...data.websocket_fields, ...data.custom_fields]
      allFields.forEach(field => {
        if (field.default !== null && field.default !== undefined) {
          initialData[field.name] = field.default
        }
      })
      setFormData(initialData)
      
      // Inizializza la lista delle actions se presente
      if (initialData.actions && typeof initialData.actions === 'object') {
        const actionsArray: ActionItem[] = Object.entries(initialData.actions).map(([name, url], index) => ({
          id: `action_${index}_${Date.now()}`,
          name,
          url: url as string
        }))
        setActionsList(actionsArray)
      } else {
        setActionsList([])
      }
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message)
      } else {
        setError('Errore sconosciuto')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleTemplateSelect = async (templateId: string) => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`http://localhost:8000/frontend/sensor-templates/${templateId}/config`)
      if (!response.ok) {
        throw new Error(`Errore HTTP! status: ${response.status}`)
      }
      const templateConfig = await response.json()
      setSelectedTemplate(templateConfig)
      setSelectedMode('template')
      setShowTemplateSelection(false)
      
      // Inizializza formData con i default del template, includendo template_id
      const initialData: Record<string, any> = {
        ...templateConfig.default_config,
        type: templateConfig.protocol,
        template_id: templateId  // Salva l'ID del template
      }
      setFormData(initialData)
      setShowForm(true)
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message)
      } else {
        setError('Errore sconosciuto')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleCustomSelect = async () => {
    setSelectedMode('custom')
    // Imposta template_id a "custom" quando si seleziona custom
    setFormData(prev => ({ ...prev, template_id: 'custom' }))
    await fetchTemplate()
  }

  const handleFieldChange = (name: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleActionChange = (id: string, field: 'name' | 'url', value: string) => {
    setActionsList(prev => 
      prev.map(action => 
        action.id === id 
          ? { ...action, [field]: value }
          : action
      )
    )
  }

  const syncActionsToFormData = () => {
    // Converte la lista delle actions in un oggetto per formData
    const actionsObj: Record<string, string> = {}
    actionsList.forEach(action => {
      if (action.name.trim() !== '') {
        actionsObj[action.name.trim()] = action.url
      }
    })
    handleFieldChange('actions', Object.keys(actionsObj).length > 0 ? actionsObj : undefined)
  }

  const addAction = () => {
    const newAction: ActionItem = {
      id: `action_${Date.now()}_${Math.random()}`,
      name: '',
      url: ''
    }
    setActionsList(prev => [...prev, newAction])
  }

  const removeAction = (id: string) => {
    setActionsList(prev => prev.filter(action => action.id !== id))
  }

  const renderField = (field: FieldDefinition) => {
    const value = formData[field.name] ?? field.default ?? ''
    
    if (field.type === 'enum' && field.values) {
      return (
        <select
          id={field.name}
          value={value}
          onChange={(e) => handleFieldChange(field.name, e.target.value)}
          required={field.required}
          className="text-sm rounded-lg block w-full px-3 py-2.5 shadow-sm transition-colors border-2"
          style={{ 
            borderColor: '#8F0177',
            backgroundColor: 'rgba(54, 1, 133, 0.4)',
            color: '#FFFFFF',
            outline: 'none'
          }}
          onFocus={(e) => {
            e.target.style.borderColor = '#F4B342'
            e.target.style.boxShadow = '0 0 0 3px rgba(244, 179, 66, 0.3)'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.6)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = '#8F0177'
            e.target.style.boxShadow = 'none'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.4)'
          }}
        >
          <option value="">Seleziona...</option>
          {field.values.map(val => (
            <option key={val} value={val}>{val}</option>
          ))}
        </select>
      )
    }
    
    if (field.type === 'boolean') {
      return (
        <select
          id={field.name}
          value={value === true ? 'true' : value === false ? 'false' : ''}
          onChange={(e) => handleFieldChange(field.name, e.target.value === 'true')}
          required={field.required}
          className="text-sm rounded-lg block w-full px-3 py-2.5 shadow-sm transition-colors border-2"
          style={{ 
            borderColor: '#8F0177',
            backgroundColor: 'rgba(54, 1, 133, 0.4)',
            color: '#FFFFFF',
            outline: 'none'
          }}
          onFocus={(e) => {
            e.target.style.borderColor = '#F4B342'
            e.target.style.boxShadow = '0 0 0 3px rgba(244, 179, 66, 0.3)'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.6)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = '#8F0177'
            e.target.style.boxShadow = 'none'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.4)'
          }}
        >
          <option value="">Seleziona...</option>
          <option value="true">Sì</option>
          <option value="false">No</option>
        </select>
      )
    }
    
    if (field.type === 'integer') {
      return (
        <input
          id={field.name}
          type="number"
          value={value}
          onChange={(e) => handleFieldChange(field.name, e.target.value ? parseInt(e.target.value) : '')}
          required={field.required}
          placeholder={field.example ? String(field.example) : ''}
          className="text-sm rounded-lg block w-full px-3 py-2.5 shadow-sm transition-colors border-2"
          style={{ 
            borderColor: '#8F0177',
            backgroundColor: 'rgba(54, 1, 133, 0.4)',
            color: '#FFFFFF',
            outline: 'none'
          }}
          onFocus={(e) => {
            e.target.style.borderColor = '#F4B342'
            e.target.style.boxShadow = '0 0 0 3px rgba(244, 179, 66, 0.3)'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.6)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = '#8F0177'
            e.target.style.boxShadow = 'none'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.4)'
          }}
        />
      )
    }
    
    if (field.type === 'object' && field.name === 'actions') {
      // Rendering speciale per il campo actions usando actionsList
      return (
        <div className="space-y-3">
          {actionsList.map((action) => (
            <div key={action.id} className="flex gap-2 items-start">
              <div className="flex-1">
                <input
                  type="text"
                  value={action.name}
                  onChange={(e) => {
                    handleActionChange(action.id, 'name', e.target.value)
                    // Sincronizza dopo un breve delay per evitare troppi aggiornamenti
                    setTimeout(syncActionsToFormData, 100)
                  }}
                  placeholder="Nome azione (es: accendi)"
                  className="text-sm rounded-lg block w-full px-3 py-2.5 shadow-sm transition-colors border-2"
          style={{ 
            borderColor: '#8F0177',
            backgroundColor: 'rgba(54, 1, 133, 0.4)',
            color: '#FFFFFF',
            outline: 'none'
          }}
          onFocus={(e) => {
            e.target.style.borderColor = '#F4B342'
            e.target.style.boxShadow = '0 0 0 3px rgba(244, 179, 66, 0.3)'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.6)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = '#8F0177'
            e.target.style.boxShadow = 'none'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.4)'
          }}
                />
              </div>
              <div className="flex-1">
                <input
                  type="text"
                  value={action.url}
                  onChange={(e) => {
                    handleActionChange(action.id, 'url', e.target.value)
                    // Sincronizza dopo un breve delay per evitare troppi aggiornamenti
                    setTimeout(syncActionsToFormData, 100)
                  }}
                  placeholder="URL (es: /color/0?turn=on)"
                  className="text-sm rounded-lg block w-full px-3 py-2.5 shadow-sm transition-colors border-2"
          style={{ 
            borderColor: '#8F0177',
            backgroundColor: 'rgba(54, 1, 133, 0.4)',
            color: '#FFFFFF',
            outline: 'none'
          }}
          onFocus={(e) => {
            e.target.style.borderColor = '#F4B342'
            e.target.style.boxShadow = '0 0 0 3px rgba(244, 179, 66, 0.3)'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.6)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = '#8F0177'
            e.target.style.boxShadow = 'none'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.4)'
          }}
                />
              </div>
              <button
                type="button"
                onClick={() => {
                  removeAction(action.id)
                  syncActionsToFormData()
                }}
                className="px-3 py-2.5 text-white rounded-lg text-sm font-medium transition-all duration-200 shadow-md hover:shadow-lg"
                style={{
                  background: 'linear-gradient(135deg, #DE1A58, #8F0177)'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'linear-gradient(135deg, #8F0177, #DE1A58)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'linear-gradient(135deg, #DE1A58, #8F0177)'}
              >
                Rimuovi
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addAction}
            className="w-full px-4 py-2.5 text-white rounded-lg text-sm font-medium transition-colors duration-150 shadow-md border"
            style={{
              background: 'linear-gradient(135deg, #360185, #8F0177)',
              borderColor: '#8F0177'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'linear-gradient(135deg, #8F0177, #360185)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'linear-gradient(135deg, #360185, #8F0177)'}
          >
            + Aggiungi Azione
          </button>
        </div>
      )
    }
    
    if (field.type === 'object') {
      return (
        <textarea
          id={field.name}
          value={typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value)
              handleFieldChange(field.name, parsed)
            } catch {
              handleFieldChange(field.name, e.target.value)
            }
          }}
          required={field.required}
          placeholder={field.example ? JSON.stringify(field.example, null, 2) : '{}'}
          rows={4}
          className="text-sm rounded-lg block w-full px-3 py-2.5 shadow-sm font-mono transition-colors border-2"
          style={{ 
            borderColor: '#8F0177',
            backgroundColor: 'rgba(54, 1, 133, 0.4)',
            color: '#FFFFFF',
            outline: 'none'
          }}
          onFocus={(e) => {
            e.target.style.borderColor = '#F4B342'
            e.target.style.boxShadow = '0 0 0 3px rgba(244, 179, 66, 0.3)'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.6)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = '#8F0177'
            e.target.style.boxShadow = 'none'
            e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.4)'
          }}
        />
      )
    }
    
    // Default: string
    return (
      <input
        id={field.name}
        type="text"
        value={value}
        onChange={(e) => handleFieldChange(field.name, e.target.value)}
        required={field.required}
        placeholder={field.example || ''}
        className="text-sm rounded-lg block w-full px-3 py-2.5 shadow-sm transition-colors border-2"
        style={{ 
          borderColor: '#8F0177',
          backgroundColor: 'rgba(54, 1, 133, 0.4)',
          color: '#FFFFFF',
          outline: 'none'
        }}
        onFocus={(e) => {
          e.target.style.borderColor = '#F4B342'
          e.target.style.boxShadow = '0 0 0 3px rgba(244, 179, 66, 0.3)'
          e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.6)'
        }}
        onBlur={(e) => {
          e.target.style.borderColor = '#8F0177'
          e.target.style.boxShadow = 'none'
          e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.4)'
        }}
      />
    )
  }

  const renderFields = (fields: FieldDefinition[], title: string) => {
    if (!template) return null
    
    const sensorType = formData.type
    const shouldShow = 
      title === 'Campi Comuni' ||
      (title === 'Campi HTTP' && sensorType === 'http') ||
      (title === 'Campi WebSocket' && sensorType === 'websocket') ||
      (title === 'Campi Custom' && sensorType === 'custom')
    
    if (!shouldShow || fields.length === 0) return null
    
    // Filtra i campi poll_interval e timeout se polling non è abilitato
    const filteredFields = fields.filter(field => {
      if (field.name === 'poll_interval' || field.name === 'timeout') {
        return enablePolling
      }
      return true
    })
    
    return (
      <div className="mb-8">
        <div className="mb-4 pb-3 border-b-2" style={{ borderBottomColor: '#F4B342' }}>
          <h3 className="text-lg font-bold" style={{ color: '#F4B342' }}>{title}</h3>
        </div>
        <div className="space-y-5">
          {filteredFields.map(field => (
            <div key={field.name} className="p-4 rounded-lg border-2" style={{ 
              borderColor: '#8F0177',
              background: 'linear-gradient(135deg, rgba(143, 1, 119, 0.3), rgba(54, 1, 133, 0.2))'
            }}>
              <label htmlFor={field.name} className="block mb-2 text-sm font-semibold" style={{ color: '#F4B342' }}>
                {field.name}
                {field.required && <span className="ml-1" style={{ color: '#DE1A58' }}>*</span>}
              </label>
              {renderField(field)}
              {field.description && (
                <p className="text-xs mt-2 italic" style={{ color: '#FFFFFF', opacity: 0.8 }}>{field.description}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    )
  }

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    setIsSubmitting(true)
    setError(null)
    setSubmitSuccess(false)
    
    try {
      // Sincronizza le actions prima di inviare
      syncActionsToFormData()
      
      // Prepara i dati da inviare, rimuovendo poll_interval e timeout se polling non è abilitato
      const dataToSubmit = { ...formData }
      if (!enablePolling) {
        delete dataToSubmit.poll_interval
        delete dataToSubmit.timeout
      }
      
      // Pulisci le actions: rimuovi quelle con nomi vuoti
      if (dataToSubmit.actions) {
        const cleanedActions: Record<string, string> = {}
        Object.entries(dataToSubmit.actions).forEach(([name, url]) => {
          if (name && name.trim() !== '') {
            cleanedActions[name.trim()] = url as string
          }
        })
        dataToSubmit.actions = Object.keys(cleanedActions).length > 0 ? cleanedActions : undefined
      }
      
      // Rimuovi campi undefined o vuoti
      Object.keys(dataToSubmit).forEach(key => {
        if (dataToSubmit[key] === undefined || dataToSubmit[key] === '' || dataToSubmit[key] === null) {
          delete dataToSubmit[key]
        }
      })
      
      console.log('Invio dati:', dataToSubmit)
      
      // Invia la richiesta POST
      const response = await fetch('http://localhost:8000/sensors/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(dataToSubmit),
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `Errore HTTP: ${response.status}` }))
        throw new Error(errorData.detail || errorData.message || `Errore HTTP: ${response.status}`)
      }
      
      const result = await response.json()
      console.log('Sensore creato con successo:', result)
      setSubmitSuccess(true)
      
      // Chiama la callback onSuccess se presente
      if (onSuccess) {
        onSuccess()
      }
      
      // Reset del form dopo il successo
      setTimeout(() => {
        setShowForm(false)
        setShowTemplateSelection(false)
        setSelectedMode(null)
        setSelectedTemplate(null)
        setTemplate(null)
        setFormData({})
        setActionsList([])
        setEnablePolling(false)
        setSubmitSuccess(false)
      }, 2000)
      
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message)
      } else {
        setError('Errore sconosciuto durante l\'invio del form')
      }
      console.error('Errore durante l\'invio:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setShowTemplateSelection(false)
    setSelectedMode(null)
    setSelectedTemplate(null)
    setTemplate(null)
    setFormData({})
    setActionsList([])
    setError(null)
    setEnablePolling(false)
    if (onCancel) {
      onCancel()
    }
  }

  const renderTemplateForm = () => {
    if (!selectedTemplate) return null

    return (
      <div className="space-y-5">
        {/* Campo Nome */}
        <div className="p-4 rounded-lg border-2" style={{ 
          borderColor: '#8F0177',
          background: 'linear-gradient(135deg, rgba(143, 1, 119, 0.3), rgba(54, 1, 133, 0.2))'
        }}>
          <label htmlFor="name" className="block mb-2 text-sm font-semibold" style={{ color: '#F4B342' }}>
            Nome Sensore <span className="ml-1" style={{ color: '#DE1A58' }}>*</span>
          </label>
          <input
            id="name"
            type="text"
            value={formData.name || ''}
            onChange={(e) => handleFieldChange('name', e.target.value)}
            required
            placeholder="es: shelly_rgbw2_01"
            className="text-sm rounded-lg block w-full px-3 py-2.5 shadow-sm transition-colors border-2"
            style={{ 
              borderColor: '#8F0177',
              backgroundColor: 'rgba(54, 1, 133, 0.4)',
              color: '#FFFFFF',
              outline: 'none'
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#F4B342'
              e.target.style.boxShadow = '0 0 0 3px rgba(244, 179, 66, 0.3)'
              e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.6)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#8F0177'
              e.target.style.boxShadow = 'none'
              e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.4)'
            }}
          />
        </div>

        {/* Campo IP */}
        <div className="p-4 rounded-lg border-2" style={{ 
          borderColor: '#8F0177',
          background: 'linear-gradient(135deg, rgba(143, 1, 119, 0.3), rgba(54, 1, 133, 0.2))'
        }}>
          <label htmlFor="ip" className="block mb-2 text-sm font-semibold" style={{ color: '#F4B342' }}>
            Indirizzo IP <span className="ml-1" style={{ color: '#DE1A58' }}>*</span>
          </label>
          <input
            id="ip"
            type="text"
            value={formData.ip || ''}
            onChange={(e) => handleFieldChange('ip', e.target.value)}
            required
            placeholder="es: 192.168.1.50"
            className="text-sm rounded-lg block w-full px-3 py-2.5 shadow-sm transition-colors border-2"
            style={{ 
              borderColor: '#8F0177',
              backgroundColor: 'rgba(54, 1, 133, 0.4)',
              color: '#FFFFFF',
              outline: 'none'
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#F4B342'
              e.target.style.boxShadow = '0 0 0 3px rgba(244, 179, 66, 0.3)'
              e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.6)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#8F0177'
              e.target.style.boxShadow = 'none'
              e.target.style.backgroundColor = 'rgba(54, 1, 133, 0.4)'
            }}
          />
        </div>

      </div>
    )
  }

  return (
    <>
      {!showForm && !showTemplateSelection && (
        <button
          onClick={fetchSensorTemplates}
          disabled={isLoading}
          className="inline-flex items-center gap-2 disabled:cursor-not-allowed text-white font-semibold py-2.5 px-5 rounded-lg transition-colors duration-150 shadow-lg hover:shadow-md disabled:shadow-md text-sm"
          style={{
            background: isLoading 
              ? 'linear-gradient(135deg, #8F0177, #360185)' 
              : 'linear-gradient(135deg, #360185, #8F0177)',
            opacity: isLoading ? 0.7 : 1
          }}
        >
          {isLoading ? (
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>Aggiungi Sensore</span>
            </>
          )}
        </button>
      )}
      
      {error && (
        <div className="fixed top-20 right-4 z-50 max-w-md animate-slide-in">
          <div className="backdrop-blur-md rounded-lg shadow-2xl p-4 border-l-4 border-2" style={{ 
            borderLeftColor: '#DE1A58',
            borderColor: '#DE1A58',
            background: 'linear-gradient(135deg, rgba(54, 1, 133, 0.95), rgba(143, 1, 119, 0.95))',
            boxShadow: '0 10px 40px rgba(222, 26, 88, 0.5)'
          }}>
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20" style={{ color: '#DE1A58' }}>
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm font-semibold" style={{ color: '#DE1A58' }}>Errore</p>
                <p className="text-sm mt-1" style={{ color: '#FFFFFF' }}>{error}</p>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {showTemplateSelection && !showForm && (
        <div className="fixed inset-0 flex items-center justify-center p-4 z-40" style={{ backgroundColor: 'rgba(54, 1, 133, 0.7)', backdropFilter: 'blur(4px)' }}>
          <div className="backdrop-blur-md rounded-xl shadow-2xl max-w-2xl w-full border-2" style={{ 
            borderColor: '#F4B342',
            background: 'linear-gradient(135deg, #360185, #8F0177)',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.6)'
          }}>
            <div className="sticky top-0 backdrop-blur-md border-b px-6 py-5 flex justify-between items-center" style={{ 
              borderBottomColor: '#8F0177',
              background: 'linear-gradient(135deg, rgba(54, 1, 133, 0.95), rgba(143, 1, 119, 0.95))'
            }}>
              <div>
                <h2 className="text-xl font-bold" style={{ color: '#F4B342' }}>Seleziona Tipo Sensore</h2>
                <p className="text-sm mt-1" style={{ color: '#F4B342', opacity: 0.9 }}>Scegli tra un template predefinito o configurazione custom</p>
              </div>
              <button
                type="button"
                onClick={handleCancel}
                className="transition-colors p-2 rounded-lg"
                style={{ color: '#F4B342' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(244, 179, 66, 0.2)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                aria-label="Chiudi"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {/* Opzione Custom */}
                <button
                  onClick={handleCustomSelect}
                  className="w-full p-5 rounded-lg border-2 text-left transition-all duration-200 hover:scale-105"
                  style={{
                    borderColor: '#8F0177',
                    background: 'linear-gradient(135deg, rgba(143, 1, 119, 0.4), rgba(54, 1, 133, 0.3))'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#F4B342'
                    e.currentTarget.style.background = 'linear-gradient(135deg, rgba(143, 1, 119, 0.6), rgba(54, 1, 133, 0.5))'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#8F0177'
                    e.currentTarget.style.background = 'linear-gradient(135deg, rgba(143, 1, 119, 0.4), rgba(54, 1, 133, 0.3))'
                  }}
                >
                  <h3 className="text-lg font-bold mb-2" style={{ color: '#F4B342' }}>Custom</h3>
                  <p className="text-sm" style={{ color: '#FFFFFF', opacity: 0.9 }}>
                    Configurazione completa con tutti i parametri personalizzabili
                  </p>
                </button>

                {/* Template disponibili */}
                {availableTemplates.map((tmpl) => (
                  <button
                    key={tmpl.id}
                    onClick={() => handleTemplateSelect(tmpl.id)}
                    className="w-full p-5 rounded-lg border-2 text-left transition-all duration-200 hover:scale-105"
                    style={{
                      borderColor: '#8F0177',
                      background: 'linear-gradient(135deg, rgba(143, 1, 119, 0.4), rgba(54, 1, 133, 0.3))'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = '#F4B342'
                      e.currentTarget.style.background = 'linear-gradient(135deg, rgba(143, 1, 119, 0.6), rgba(54, 1, 133, 0.5))'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = '#8F0177'
                      e.currentTarget.style.background = 'linear-gradient(135deg, rgba(143, 1, 119, 0.4), rgba(54, 1, 133, 0.3))'
                    }}
                  >
                    <h3 className="text-lg font-bold mb-2" style={{ color: '#F4B342' }}>{tmpl.name}</h3>
                    <p className="text-sm mb-2" style={{ color: '#FFFFFF', opacity: 0.9 }}>
                      {tmpl.description}
                    </p>
                    <p className="text-xs" style={{ color: '#F4B342', opacity: 0.8 }}>
                      Protocollo: {tmpl.protocol.toUpperCase()} • Configurazione semplificata
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {submitSuccess && (
        <div className="fixed top-20 right-4 z-50 max-w-md animate-slide-in">
          <div className="backdrop-blur-md rounded-lg shadow-2xl p-4 border-l-4 border-2" style={{ 
            borderLeftColor: '#F4B342',
            borderColor: '#F4B342',
            background: 'linear-gradient(135deg, rgba(54, 1, 133, 0.95), rgba(143, 1, 119, 0.95))',
            boxShadow: '0 10px 40px rgba(244, 179, 66, 0.5)'
          }}>
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20" style={{ color: '#F4B342' }}>
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm font-semibold" style={{ color: '#F4B342' }}>Successo!</p>
                <p className="text-sm mt-1" style={{ color: '#FFFFFF' }}>Sensore creato con successo!</p>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {showForm && (template || selectedTemplate) && !isLoading && (
        <div className="fixed inset-0 flex items-center justify-center p-4 z-40" style={{ backgroundColor: 'rgba(54, 1, 133, 0.7)', backdropFilter: 'blur(4px)' }}>
          <div className="backdrop-blur-md rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border-2" style={{ 
            borderColor: '#F4B342',
            background: 'linear-gradient(135deg, #360185, #8F0177)',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.6)'
          }}>
            <div className="sticky top-0 backdrop-blur-md border-b px-6 py-5 flex justify-between items-center" style={{ 
              borderBottomColor: '#8F0177',
              background: 'linear-gradient(135deg, rgba(54, 1, 133, 0.95), rgba(143, 1, 119, 0.95))'
            }}>
              <div>
                <h2 className="text-xl font-bold" style={{ color: '#F4B342' }}>Aggiungi Nuovo Sensore</h2>
                <p className="text-sm mt-1" style={{ color: '#F4B342', opacity: 0.9 }}>Compila i campi richiesti per aggiungere un nuovo sensore</p>
              </div>
              <button
                type="button"
                onClick={handleCancel}
                className="transition-colors p-2 rounded-lg"
                style={{ color: '#F4B342' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(244, 179, 66, 0.2)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                aria-label="Chiudi"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6">
              <form onSubmit={handleFormSubmit}>
                {selectedMode === 'template' && selectedTemplate ? (
                  // Form semplificato per template
                  <>
                    <div className="mb-6 p-4 rounded-lg border-2" style={{ 
                      borderColor: '#F4B342',
                      background: 'linear-gradient(135deg, rgba(244, 179, 66, 0.2), rgba(143, 1, 119, 0.1))'
                    }}>
                      <h3 className="text-lg font-bold mb-2" style={{ color: '#F4B342' }}>{selectedTemplate.name}</h3>
                      <p className="text-sm" style={{ color: '#FFFFFF', opacity: 0.9 }}>{selectedTemplate.description}</p>
                    </div>
                    {renderTemplateForm()}
                  </>
                ) : (
                  // Form completo per custom
                  <>
                {/* Checkbox per abilitare il polling */}
                <div className="mb-8 p-5 rounded-lg border-2" style={{ 
                  background: 'linear-gradient(135deg, rgba(143, 1, 119, 0.4), rgba(54, 1, 133, 0.3))',
                  borderColor: '#F4B342'
                }}>
                  <label className="flex items-start cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enablePolling}
                      onChange={(e) => {
                        setEnablePolling(e.target.checked)
                        // Se disabiliti il polling, rimuovi i valori di poll_interval e timeout
                        if (!e.target.checked) {
                          setFormData(prev => {
                            const newData = { ...prev }
                            delete newData.poll_interval
                            delete newData.timeout
                            return newData
                          })
                        }
                      }}
                      className="w-5 h-5 mt-0.5 rounded focus:ring-2 border-2"
                      style={{ 
                        accentColor: '#F4B342',
                        borderColor: enablePolling ? '#F4B342' : '#8F0177',
                        backgroundColor: enablePolling ? '#F4B342' : 'transparent'
                      }}
                    />
                    <div className="ml-3 flex-1">
                      <span className="block text-sm font-semibold" style={{ color: '#F4B342' }}>
                        Abilita Polling
                      </span>
                      <p className="mt-1 text-xs" style={{ color: '#FFFFFF', opacity: 0.9 }}>
                        Il backend interroga periodicamente il sensore per ottenere dati. Se disabilitato, il sensore funziona solo come dispositivo controllabile (es. luce con actions HTTP).
                      </p>
                    </div>
                  </label>
                </div>
              
                    {template && (
                      <>
              {renderFields(template.common_fields, 'Campi Comuni')}
              {renderFields(template.http_fields, 'Campi HTTP')}
              {renderFields(template.websocket_fields, 'Campi WebSocket')}
              {renderFields(template.custom_fields, 'Campi Custom')}
                      </>
                    )}
                  </>
                )}
              
              <div className="flex gap-3 mt-8 pt-6 border-t-2" style={{ borderTopColor: '#F4B342' }}>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 inline-flex items-center justify-center gap-2 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-150 shadow-lg hover:shadow-md disabled:shadow-md"
                  style={{
                    background: isSubmitting 
                      ? 'linear-gradient(135deg, #8F0177, #360185)' 
                      : 'linear-gradient(135deg, #DE1A58, #8F0177)',
                    opacity: isSubmitting ? 0.7 : 1
                  }}
                >
                  {isSubmitting ? (
                    <>
                      <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>Salvataggio...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Salva Sensore</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={isSubmitting}
                  className="flex-1 inline-flex items-center justify-center gap-2 disabled:cursor-not-allowed font-semibold py-3 px-6 rounded-lg transition-colors duration-150 shadow-md hover:shadow-sm disabled:shadow-sm"
                  style={{
                    backgroundColor: 'rgba(143, 1, 119, 0.3)',
                    color: '#FFFFFF',
                    border: '2px solid #8F0177'
                  }}
                  onMouseEnter={(e) => {
                    if (!isSubmitting) {
                      e.currentTarget.style.backgroundColor = 'rgba(143, 1, 119, 0.5)'
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(143, 1, 119, 0.3)'
                  }}
                >
                  <span>Annulla</span>
                </button>
              </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

