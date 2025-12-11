import { useState } from 'react'

const CORRECT_PIN = '1234'

interface PinModalProps {
  onAuthenticated: () => void
}

export default function PinModal({ onAuthenticated }: PinModalProps) {
  const [pin, setPin] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handlePinSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (pin === CORRECT_PIN) {
      onAuthenticated()
    } else {
      setError('PIN errato. Riprova.')
      setPin('')
    }
  }

  const handlePinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 4)
    setPin(value)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-8">
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full">
        <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">
          Accesso Sistema
        </h1>
        <form onSubmit={handlePinSubmit} className="space-y-4">
          <div>
            <label htmlFor="pin" className="block text-sm font-medium text-gray-700 mb-2">
              Inserisci PIN (4 cifre)
            </label>
            <input
              id="pin"
              type="password"
              value={pin}
              onChange={handlePinChange}
              maxLength={4}
              className="w-full px-4 py-3 text-center text-2xl tracking-widest border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none"
              placeholder="••••"
              autoFocus
            />
          </div>
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700 text-center">{error}</p>
            </div>
          )}
          <button
            type="submit"
            disabled={pin.length !== 4}
            className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-md hover:shadow-lg"
          >
            Accedi
          </button>
        </form>
      </div>
    </div>
  )
}

