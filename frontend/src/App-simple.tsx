import React, { useState } from 'react';
import BrokerSelector from './components/BrokerSelector';
import { AuthResponse } from './api';

function App() {
  const [authData, setAuthData] = useState<AuthResponse | null>(null);

  const handleBrokerConnected = (auth: AuthResponse) => {
    setAuthData(auth);
    console.log('Connected to broker:', auth.broker);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-emerald-400 mb-2">Kalpi Capital</h1>
          <p className="text-gray-400">Portfolio Trade Execution Engine</p>
        </header>
        
        <BrokerSelector onConnected={handleBrokerConnected} />
        
        {authData && (
          <div className="mt-8 p-4 bg-gray-800 rounded-lg">
            <h2 className="text-xl font-semibold text-white mb-2">Connected!</h2>
            <p className="text-gray-300">Broker: {authData.broker}</p>
            <p className="text-gray-300">User: {authData.user_id}</p>
            <p className="text-gray-300">Message: {authData.message}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
