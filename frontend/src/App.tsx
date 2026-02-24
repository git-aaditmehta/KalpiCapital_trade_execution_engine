import React, { useState, useEffect, useRef } from 'react';
import BrokerSelector from './components/BrokerSelector';
import PortfolioUpload from './components/PortfolioUpload';
import ExecutionPanel from './components/ExecutionPanel';
import ResultsView from './components/ResultsView';
import ZerodhaOAuthDemo from './components/ZerodhaOAuthDemo';
import { AuthResponse, ExecutionSummary, TradeInstruction } from './api';
import { Activity, Code } from 'lucide-react';

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
    setSummary(null);
    setWsMessages([]);
  };

  const steps: { key: Step; label: string }[] = [
    { key: 'broker', label: '1. Connect Broker' },
    { key: 'portfolio', label: '2. Upload Portfolio' },
    { key: 'execute', label: '3. Execute Trades' },
    { key: 'results', label: '4. View Results' },
  ];

  const stepOrder: Step[] = ['broker', 'portfolio', 'execute', 'results'];
  const currentIdx = stepOrder.indexOf(step);

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-3">
          <Activity className="w-7 h-7 text-emerald-400" />
          <div>
            <h1 className="text-xl font-bold text-white">Kalpi Capital</h1>
            <p className="text-xs text-gray-400">Portfolio Trade Execution Engine</p>
          </div>
        </div>
      </header>

      {/* Progress Steps */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="flex items-center gap-2 mb-8">
          {steps.map((s, i) => (
            <React.Fragment key={s.key}>
              <div
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  i <= currentIdx
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-gray-800/50 text-gray-500 border border-gray-700/50'
                }`}
              >
                {s.label}
              </div>
              {i < steps.length - 1 && (
                <div className={`h-px flex-1 ${i < currentIdx ? 'bg-emerald-500/40' : 'bg-gray-700/50'}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            {demoMode ? (
              <ZerodhaOAuthDemo />
            ) : (
              <>
                {step === 'broker' && <BrokerSelector onConnected={handleBrokerConnected} />}
                {step === 'portfolio' && authData && (
                  <PortfolioUpload 
                    broker={authData.broker} 
                    sessionToken={authData.session_token}
                    onReady={handlePortfolioReady} 
                  />
                )}
                {step === 'execute' && authData && (
                  <ExecutionPanel
                    broker={authData.broker}
                    sessionToken={authData.session_token}
                    instructions={instructions}
                    mode={mode}
                    onComplete={handleExecutionComplete}
                  />
                )}
                {step === 'results' && summary && (
                  <ResultsView summary={summary} onReset={handleReset} />
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
                <p className="text-xs text-gray-500">Waiting for trade execution events...</p>
              ) : (
                wsMessages.map((msg, i) => (
                  <div key={i} className="bg-gray-800/50 rounded-lg p-3 text-xs border border-gray-700/50">
                    <div className="text-emerald-400 font-medium">{msg.event}</div>
                    <div className="text-gray-400 mt-1">
                      {msg.broker} &middot; {msg.successful}/{msg.total_orders} orders
                    </div>
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
