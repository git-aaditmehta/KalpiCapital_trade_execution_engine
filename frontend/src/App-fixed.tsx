import React, { useState, useEffect, useRef } from 'react';
import BrokerSelector from './components/BrokerSelector';
import ZerodhaOAuthDemo from './components/ZerodhaOAuthDemo';
import { AuthResponse, ExecutionSummary, TradeInstruction } from './api';
import { Activity, Code } from 'lucide-react';

// Import other components dynamically to avoid TypeScript errors
const PortfolioUpload = React.lazy(() => import('./components/PortfolioUpload'));
const ExecutionPanel = React.lazy(() => import('./components/ExecutionPanel'));
const ResultsView = React.lazy(() => import('./components/ResultsView'));

type Step = 'broker' | 'portfolio' | 'execute' | 'results';

export default function App() {
  const [step, setStep] = useState<Step>('broker');
  const [authData, setAuthData] = useState<AuthResponse | null>(null);
  const [instructions, setInstructions] = useState<TradeInstruction[]>([]);
  const [mode, setMode] = useState<'first_time' | 'rebalance'>('first_time');
  const [summary, setSummary] = useState<ExecutionSummary | null>(null);
  const [wsMessages, setWsMessages] = useState<any[]>([]);
  const [demoMode, setDemoMode] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = import.meta.env.PROD
      ? `${protocol}//${window.location.host}/ws/notifications`
      : `ws://localhost:8001/ws/notifications`;

    const ws = new WebSocket(wsUrl);
    ws.onopen = () => console.log('WebSocket connected');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setWsMessages((prev) => [...prev, data]);
    };
    ws.onclose = () => console.log('WebSocket disconnected');
    wsRef.current = ws;

    return () => { ws.close(); };
  }, []);

  const handleBrokerConnected = (auth: AuthResponse) => {
    setAuthData(auth);
    setStep('portfolio');
  };

  const handlePortfolioReady = (instr: TradeInstruction[], m: 'first_time' | 'rebalance') => {
    setInstructions(instr);
    setMode(m);
    setStep('execute');
  };

  const handleExecutionComplete = (result: ExecutionSummary) => {
    setSummary(result);
    setStep('results');
  };

  const handleReset = () => {
    setStep('broker');
    setAuthData(null);
    setInstructions([]);
    setMode('first_time');
    setSummary(null);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-emerald-400 mb-2">Kalpi Capital</h1>
              <p className="text-gray-400">Portfolio Trade Execution Engine</p>
            </div>
            <button
              onClick={() => setDemoMode(!demoMode)}
              className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
            >
              <Code className="w-4 h-4" />
              {demoMode ? 'Normal Mode' : 'Demo Mode'}
            </button>
          </div>
        </header>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            {demoMode ? (
              <ZerodhaOAuthDemo />
            ) : (
              <>
                {step === 'broker' && <BrokerSelector onConnected={handleBrokerConnected} />}
                {step === 'portfolio' && authData && (
                  <React.Suspense fallback={<div className="text-gray-400">Loading...</div>}>
                    <PortfolioUpload 
                      broker={authData.broker} 
                      sessionToken={authData.session_token}
                      onReady={handlePortfolioReady} 
                    />
                  </React.Suspense>
                )}
                {step === 'execute' && authData && (
                  <React.Suspense fallback={<div className="text-gray-400">Loading...</div>}>
                    <ExecutionPanel
                      broker={authData.broker}
                      sessionToken={authData.session_token}
                      instructions={instructions}
                      mode={mode}
                      onComplete={handleExecutionComplete}
                    />
                  </React.Suspense>
                )}
                {step === 'results' && summary && (
                  <React.Suspense fallback={<div className="text-gray-400">Loading...</div>}>
                    <ResultsView summary={summary} onReset={handleReset} />
                  </React.Suspense>
                )}
              </>
            )}
          </div>

          {/* Sidebar: Live WS Feed */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 h-fit">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Live Notifications
            </h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {wsMessages.length === 0 ? (
                <p className="text-gray-500 text-xs">Waiting for notifications...</p>
              ) : (
                wsMessages.slice(-10).map((msg, i) => (
                  <div key={i} className="text-xs bg-gray-800 rounded p-2">
                    <pre className="text-gray-400 whitespace-pre-wrap">
                      {JSON.stringify(msg, null, 2)}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
