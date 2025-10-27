import { useState } from 'react'

function App() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Neurosurgery Knowledge Base
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          AI-Powered Alive Chapter Generation System
        </p>
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-2xl">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">
            Phase 0: Infrastructure Setup Complete
          </h2>
          <p className="text-gray-600 mb-6">
            The foundation is ready. Next phases will add:
          </p>
          <ul className="text-left space-y-2 text-gray-700">
            <li>✅ Phase 0: Foundation & Infrastructure</li>
            <li>⏳ Phase 1: Database Layer & Models</li>
            <li>⏳ Phase 2: Authentication System</li>
            <li>⏳ Phase 3: PDF Processing</li>
            <li>⏳ Phase 4-17: Advanced Features</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default App
