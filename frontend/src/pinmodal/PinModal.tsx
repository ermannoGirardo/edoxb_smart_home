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
    <div className="min-h-screen flex items-center justify-center p-8 relative">
      <div className="smart-background">
        <div className="floating-orb orb-1"></div>
        <div className="floating-orb orb-2"></div>
        <div className="floating-orb orb-3"></div>
        <div className="floating-orb orb-4"></div>
      </div>
      <div className="bg-white/95 backdrop-blur-md rounded-xl shadow-2xl p-8 max-w-md w-full border relative z-10" style={{ borderColor: '#8F0177', boxShadow: '0 20px 60px rgba(54, 1, 133, 0.4)' }}>
        <h1 className="text-3xl font-bold text-center mb-6" style={{ color: '#360185', textShadow: '0 2px 10px rgba(244, 179, 66, 0.2)' }}>
          Accesso Sistema
        </h1>
        <form onSubmit={handlePinSubmit} className="space-y-4">
          <div>
            <label htmlFor="pin" className="block text-sm font-medium mb-2" style={{ color: '#8F0177' }}>
              Inserisci PIN (4 cifre)
            </label>
            <input
              id="pin"
              type="password"
              value={pin}
              onChange={handlePinChange}
              maxLength={4}
              className="w-full px-4 py-3 text-center text-2xl tracking-widest border-2 rounded-lg focus:outline-none transition-all"
              style={{
                borderColor: '#8F0177',
                color: '#360185'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#360185'
                e.target.style.boxShadow = '0 0 0 3px rgba(54, 1, 133, 0.1)'
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#8F0177'
                e.target.style.boxShadow = 'none'
              }}
              placeholder="••••"
              autoFocus
            />
          </div>
          {error && (
            <div className="p-3 rounded-lg border" style={{ backgroundColor: 'rgba(222, 26, 88, 0.1)', borderColor: '#DE1A58' }}>
              <p className="text-sm text-center" style={{ color: '#DE1A58' }}>{error}</p>
            </div>
          )}
          <button
            type="submit"
            disabled={pin.length !== 4}
              className="w-full text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-150 shadow-lg hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: pin.length === 4 
                ? 'linear-gradient(135deg, #360185, #8F0177)' 
                : 'linear-gradient(135deg, #8F0177, #360185)'
            }}
          >
            Accedi
          </button>
        </form>
      </div>
    </div>
  )
}


