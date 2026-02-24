import React, { useState, useEffect } from 'react';
import { listBrokers, connectBroker, zerodhaLogin, zerodhaCallback, AuthResponse } from '../api';
import { Link2, Loader2, CheckCircle2, ExternalLink } from 'lucide-react';

interface Props {
  onConnected: (auth: AuthResponse) => void;
}

const BROKER_DISPLAY: Record<string, { label: string; color: string }> = {
  zerodha: { label: 'Zerodha (Kite)', color: 'bg-orange-500' },
  fyers: { label: 'Fyers', color: 'bg-blue-500' },
  angelone: { label: 'Angel One', color: 'bg-red-500' },
  groww: { label: 'Groww', color: 'bg-green-500' },
  upstox: { label: 'Upstox', color: 'bg-purple-500' },
  dhan: { label: 'Dhan', color: 'bg-cyan-500' },
};

export default function BrokerSelector({ onConnected }: Props) {
  const [brokers, setBrokers] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [oauthStep, setOauthStep] = useState<'idle' | 'redirecting' | 'callback'>('idle');
  const [loginUrl, setLoginUrl] = useState<string | null>(null);

  useEffect(() => {
    listBrokers().then(setBrokers).catch(() => {
      setBrokers(Object.keys(BROKER_DISPLAY));
    });
  }, []);

  // Check for OAuth callback in URL
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const requestToken = urlParams.get('request_token');
    const broker = urlParams.get('broker');
    
    if (requestToken && broker === 'zerodha') {
      handleZerodhaCallback(requestToken);
    }
  }, []);

  const handleZerodhaCallback = async (requestToken: string) => {
    setOauthStep('callback');
    setLoading(true);
    setError(null);
    
    try {
      const auth = await zerodhaCallback(requestToken);
      if (auth.authenticated) {
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
        onConnected(auth);
      } else {
        setError(auth.message || 'Authentication failed');
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Callback handling failed');
    } finally {
      setLoading(false);
      setOauthStep('idle');
    }
  };

  const handleConnect = async () => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    
    try {
      if (selected === 'zerodha') {
        // Handle Zerodha OAuth flow
        const auth = await zerodhaLogin();
        
        if (auth.authenticated) {
          // Already authenticated
          onConnected(auth);
        } else if (auth.login_url) {
          // Need to redirect to OAuth
          setLoginUrl(auth.login_url);
          setOauthStep('redirecting');
          
          // Redirect to Zerodha login
          window.location.href = auth.login_url;
        } else {
          setError(auth.message || 'Failed to initiate OAuth flow');
        }
      } else {
        // Handle other brokers with existing flow
        const auth = await connectBroker({
          broker: selected,
          api_key: 'demo_key',
          api_secret: 'demo_secret',
        });
        onConnected(auth);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Connection failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-1 flex items-center gap-2">
        <Link2 className="w-5 h-5 text-emerald-400" />
        Connect Your Broker
      </h2>
      <p className="text-sm text-gray-400 mb-5">Select a broker to authenticate and begin trading.</p>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5">
        {brokers.map((b) => {
          const info = BROKER_DISPLAY[b] || { label: b, color: 'bg-gray-500' };
          const isSelected = selected === b;
          return (
            <button
              key={b}
              onClick={() => setSelected(b)}
              className={`relative flex items-center gap-3 px-4 py-3 rounded-lg border transition-all text-left ${
                isSelected
                  ? 'border-emerald-500 bg-emerald-500/10 ring-1 ring-emerald-500/30'
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-600 hover:bg-gray-800'
              }`}
            >
              <span className={`w-3 h-3 rounded-full ${info.color}`} />
              <span className="text-sm font-medium text-gray-200">{info.label}</span>
              {isSelected && (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 absolute top-2 right-2" />
              )}
            </button>
          );
        })}
      </div>

      {error && (
        <div className="mb-4 px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
          {error}
        </div>
      )}

      {/* OAuth Redirect Notice */}
      {oauthStep === 'redirecting' && loginUrl && (
        <div className="mb-4 px-4 py-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <div className="flex items-start gap-3">
            <ExternalLink className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="text-blue-300 font-medium mb-1">Redirecting to Zerodha...</p>
              <p className="text-blue-400/70 text-xs">
                You'll be redirected to Kite login page to authenticate your account.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* OAuth Callback Processing */}
      {oauthStep === 'callback' && (
        <div className="mb-4 px-4 py-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
          <div className="flex items-center gap-3">
            <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
            <div className="text-sm">
              <p className="text-emerald-300 font-medium">Processing authentication...</p>
              <p className="text-emerald-400/70 text-xs">
                Exchanging request token for access token.
              </p>
            </div>
          </div>
        </div>
      )}

      <button
        onClick={handleConnect}
        disabled={!selected || loading || oauthStep !== 'idle'}
        className="w-full py-3 rounded-lg font-medium text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-emerald-600 hover:bg-emerald-500 text-white"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            {oauthStep === 'callback' ? 'Processing...' : 'Connecting...'}
          </span>
        ) : selected === 'zerodha' ? (
          'Connect with Zerodha OAuth'
        ) : (
          'Connect & Authenticate'
        )}
      </button>

      {/* Additional info for Zerodha */}
      {selected === 'zerodha' && oauthStep === 'idle' && (
        <div className="mt-3 text-xs text-gray-500 text-center">
          <p>Zerodha uses secure OAuth authentication.</p>
          <p>You'll be redirected to Kite login page.</p>
        </div>
      )}
    </div>
  );
}
