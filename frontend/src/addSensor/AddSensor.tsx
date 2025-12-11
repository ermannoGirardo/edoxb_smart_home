import { useState } from 'react'
import type { FieldDefinition, SensorTemplate } from './types'

interface AddSensorProps {
  onCancel?: () => void
}

export default function AddSensor({ onCancel }: AddSensorProps) {
  const [showForm, setShowForm] = useState(false)
  const [template, setTemplate] = useState<SensorTemplate | null>(null)
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

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
      const initialData: Record<string, any> = {}
      const allFields = [...data.common_fields, ...data.http_fields, ...data.websocket_fields, ...data.custom_fields]
      allFields.forEach(field => {
        if (field.default !== null && field.default !== undefined) {
          initialData[field.name] = field.default
        }
      })
      setFormData(initialData)
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

  const handleFieldChange = (name: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
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
          className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
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
          className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
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
          className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
        />
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
          className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none font-mono text-sm"
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
        className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
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
    
    return (
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-gray-700 mb-4">{title}</h3>
        <div className="space-y-4">
          {fields.map(field => (
            <div key={field.name}>
              <label htmlFor={field.name} className="block text-sm font-medium text-gray-700 mb-1">
                {field.name}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              {renderField(field)}
              {field.description && (
                <p className="text-xs text-gray-500 mt-1">{field.description}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    )
  }

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Dati del form:', formData)
    // Qui puoi aggiungere la logica per inviare i dati al backend
    alert('Form inviato! Controlla la console per i dati.')
  }

  const handleCancel = () => {
    setShowForm(false)
    setTemplate(null)
    setFormData({})
    setError(null)
    if (onCancel) {
      onCancel()
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-2xl p-8">
      <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">
        Gestione Sensori
      </h1>
      
      {!showForm && (
        <div className="text-center">
          <button
            onClick={fetchTemplate}
            disabled={isLoading}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-8 rounded-lg transition-colors shadow-md hover:shadow-lg text-lg"
          >
            {isLoading ? 'Caricamento...' : 'Add Sensor'}
          </button>
        </div>
      )}
      
      {isLoading && (
        <div className="text-center py-8">
          <p className="text-gray-600">Caricamento template...</p>
        </div>
      )}
      
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-4">
          <p className="text-red-800 font-semibold mb-2">✗ Errore:</p>
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}
      
      {showForm && template && !isLoading && (
        <form onSubmit={handleFormSubmit} className="mt-6">
          {renderFields(template.common_fields, 'Campi Comuni')}
          {renderFields(template.http_fields, 'Campi HTTP')}
          {renderFields(template.websocket_fields, 'Campi WebSocket')}
          {renderFields(template.custom_fields, 'Campi Custom')}
          
          <div className="flex gap-4 mt-6">
            <button
              type="submit"
              className="flex-1 bg-green-500 hover:bg-green-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-md hover:shadow-lg"
            >
              Salva Sensore
            </button>
            <button
              type="button"
              onClick={handleCancel}
              className="flex-1 bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-md hover:shadow-lg"
            >
              Annulla
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

