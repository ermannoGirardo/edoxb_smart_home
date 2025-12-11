import { useState } from 'react'
import './App.css'
import PinModal from './pinmodal/PinModal'
import AddSensor from './addSensor/AddSensor'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  if (!isAuthenticated) {
    return <PinModal onAuthenticated={() => setIsAuthenticated(true)} />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 p-8">
      <div className="max-w-4xl mx-auto">
        <AddSensor />
      </div>
    </div>
  )
}

export default App
