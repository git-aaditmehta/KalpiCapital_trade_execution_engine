import React, { useState } from 'react';
import { zerodhaLogin, zerodhaCallback, AuthResponse } from '../api';
import { ExternalLink, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

export default function ZerodhaOAuthDemo() {
  const [step, setStep] = useState<'idle' | 'login' | 'callback' | 'success' | 'error'>('idle');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [authData, setAuthData] = useState<AuthResponse | null>(null);

  const handleLogin = async () => {
    setStep('login');
    setLoading(true);
    setMessage('');
    
    try {
      const response = await zerodhaLogin();
      
      if (response.authenticated) {
        setAuthData(response);
        setStep('success');
        setMessage('Already authenticated with Zerodha!');
      } else if (response.login_url) {
        // Store current state for callback
        sessionStorage.setItem('zerodha_oauth_state', 'in_progress');
        
        // Redirect to Zerodha
        setMessage('Redirecting to Zerodha login...');
        setTimeout(() => {
          if (response.login_url) {
            window.location.href = response.login_url;
          }
        }, 1500);
      } else {
        setStep('error');
        setMessage(response.message || 'Failed to initiate OAuth flow');
      }
    } catch (error: any) {
      setStep('error');
      setMessage(error?.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCallback = async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const requestToken = urlParams.get('request_token');
    
    if (!requestToken) {
      setStep('error');
      setMessage('No request token found in URL');
      return;
    }
    
    setStep('callback');
    setLoading(true);
    setMessage('Exchanging request token for access token...');
    
    try {
      const response = await zerodhaCallback(requestToken);
      
      if (response.authenticated) {
        setAuthData(response);
        setStep('success');
        setMessage('Successfully authenticated with Zerodha!');
        
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
        sessionStorage.removeItem('zerodha_oauth_state');
      } else {
        setStep('error');
        setMessage(response.message || 'Authentication failed');
      }
    } catch (error: any) {
      setStep('error');
      setMessage(error?.response?.data?.detail || 'Callback failed');
    } finally {
      setLoading(false);
    }
  };

  // Check for callback on mount
  React.useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const requestToken = urlParams.get('request_token');
    const oauthState = sessionStorage.getItem('zerodha_oauth_state');
    
    if (requestToken && oauthState === 'in_progress') {
      handleCallback();
    }
  }, []);

  const reset = () => {
    setStep('idle');
    setLoading(false);
    setMessage('');
    setAuthData(null);
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md mx-auto">
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <ExternalLink className="w-5 h-5 text-orange-400" />
        Zerodha OAuth Demo
      </h2>
      
      {/* Status Display */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm">
          <div className={`w-2 h-2 rounded-full ${
            step === 'idle' ? 'bg-gray-500' :
            step === 'success' ? 'bg-emerald-500' :
            step === 'error' ? 'bg-red-500' :
            'bg-blue-500'
          }`} />
          <span className="text-gray-400">
            {step === 'idle' ? 'Ready to connect' :
             step === 'login' ? 'Initiating OAuth' :
             step === 'callback' ? 'Processing callback' :
             step === 'success' ? 'Connected' :
             'Error'}
          </span>
        </div>
      </div>

      {/* Message Display */}
      {message && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${
          step === 'success' ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300' :
          step === 'error' ? 'bg-red-500/10 border border-red-500/30 text-red-300' :
          'bg-blue-500/10 border border-blue-500/30 text-blue-300'
        }`}>
          {message}
        </div>
      )}

      {/* Auth Data Display */}
      {authData && (
        <div className="mb-4 p-3 bg-gray-800 rounded-lg">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Authentication Data:</h4>
          <div className="space-y-1 text-xs text-gray-400">
            <p><span className="text-gray-500">Broker:</span> {authData.broker}</p>
            <p><span className="text-gray-500">User ID:</span> {authData.user_id}</p>
            <p><span className="text-gray-500">Session Token:</span> {authData.session_token?.substring(0, 20)}...</p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="space-y-3">
        {step === 'idle' && (
          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full py-3 rounded-lg font-medium text-sm bg-orange-600 hover:bg-orange-500 text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Connecting...
              </span>
            ) : (
              'Connect with Zerodha'
            )}
          </button>
        )}

        {(step === 'success' || step === 'error') && (
          <button
            onClick={reset}
            className="w-full py-3 rounded-lg font-medium text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 transition-all"
          >
            Reset
          </button>
        )}

        {loading && (
          <div className="flex items-center justify-center gap-2 text-gray-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">
              {step === 'callback' ? 'Processing authentication...' : 'Connecting...'}
            </span>
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="mt-4 text-xs text-gray-500">
        <p className="mb-1">This demo shows the Zerodha OAuth flow:</p>
        <ol className="list-decimal list-inside space-y-1">
          <li>Click "Connect with Zerodha"</li>
          <li>Redirect to Kite login page</li>
          <li>Login and authorize the app</li>
          <li>Return with request token</li>
          <li>Exchange for access token</li>
        </ol>
      </div>
    </div>
  );
}
