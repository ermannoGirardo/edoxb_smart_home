import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

function App() {
  const [backendResponse, setBackendResponse] = useState<string | null>(null)
  const [backendError, setBackendError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-8">
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-2xl w-full">
        <div className="flex justify-center gap-8 mb-8">
          <a href="https://vite.dev" target="_blank">
            <img src={viteLogo} className="logo h-24 w-24 hover:scale-110 transition-transform" alt="Vite logo" />
          </a>
          <a href="https://react.dev" target="_blank">
            <img src={reactLogo} className="logo react h-24 w-24 hover:scale-110 transition-transform" alt="React logo" />
          </a>
        </div>
        <h1 className="text-4xl font-bold text-center mb-8 text-gray-800">Vite + React</h1>
        <div className="card bg-gray-50 rounded-lg p-6 mb-6">
          <button 
            disabled={isLoading}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-md hover:shadow-lg w-full"
          >
            {isLoading ? 'Testando connessione...' : 'Test Backend Connection'}
          </button>
          
          {backendResponse && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-green-800 font-semibold mb-2">✓ Risposta dal backend:</p>
              <pre className="text-sm text-green-700 bg-white p-3 rounded overflow-auto">
                {backendResponse}
              </pre>
            </div>
          )}
          
          {backendError && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800 font-semibold mb-2">✗ Errore:</p>
              <p className="text-sm text-red-700">{backendError}</p>
            </div>
          )}
          
          <p className="mt-4 text-gray-600">
            Edit <code className="bg-gray-200 px-2 py-1 rounded text-sm">src/App.tsx</code> and save to test HMR
          </p>
        </div>
        <p className="text-center text-gray-500">
          Click on the Vite and React logos to learn more
        </p>
      </div>
    </div>
  )
}

export default App
