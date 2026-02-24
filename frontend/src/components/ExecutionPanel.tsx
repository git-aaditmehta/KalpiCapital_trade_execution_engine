import React, { useState } from 'react';
import { TradeInstruction, ExecutionSummary, executePortfolio, executeBrokerTrades } from '../api';
import { Play, Loader2, Zap } from 'lucide-react';

interface Props {
  broker: string;
  sessionToken: string | null;
  instructions: TradeInstruction[];
  mode: 'first_time' | 'rebalance';
  onComplete: (summary: ExecutionSummary) => void;
}

export default function ExecutionPanel({ broker, sessionToken, instructions, mode, onComplete }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExecute = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('🚀 EXECUTING TRADES:', { broker, mode, instructions, sessionToken });
      
      let summary: ExecutionSummary;
      
      // Use new broker API for Zerodha, fallback to old API for others
      if (broker === 'zerodha' && sessionToken) {
        summary = await executeBrokerTrades(broker, sessionToken, instructions);
      } else {
        summary = await executePortfolio({
          broker,
          mode,
          instructions,
          session_token: sessionToken,
        });
      }
      
      console.log('📊 EXECUTION SUMMARY:', summary);
      onComplete(summary);
    } catch (err: any) {
      console.error('❌ EXECUTION ERROR:', err);
      setError(err?.response?.data?.detail || 'Execution failed');
    } finally {
      setLoading(false);
    }
  };

  const actionColor = (action: string) => {
    switch (action) {
      case 'BUY': return 'text-emerald-400 bg-emerald-500/10';
      case 'SELL': return 'text-red-400 bg-red-500/10';
      case 'REBALANCE': return 'text-amber-400 bg-amber-500/10';
      default: return 'text-gray-400 bg-gray-500/10';
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-1 flex items-center gap-2">
        <Zap className="w-5 h-5 text-emerald-400" />
        Execute Trades
      </h2>
      <p className="text-sm text-gray-400 mb-5">
        Review your orders below, then click execute to place them on{' '}
        <span className="text-emerald-400 font-medium">{broker}</span>.
      </p>

      {/* Summary Bar */}
      <div className="flex gap-4 mb-5 text-sm">
        <div className="px-3 py-1.5 bg-gray-800 rounded-lg">
          Mode: <span className="text-emerald-400 font-medium">{mode === 'first_time' ? 'First-Time' : 'Rebalance'}</span>
        </div>
        <div className="px-3 py-1.5 bg-gray-800 rounded-lg">
          Orders: <span className="text-white font-medium">{instructions.length}</span>
        </div>
      </div>

      {/* Order Preview Table */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 mb-5 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700/50 text-gray-400">
              <th className="text-left px-4 py-3 font-medium">Action</th>
              <th className="text-left px-4 py-3 font-medium">Symbol</th>
              <th className="text-right px-4 py-3 font-medium">Quantity</th>
              <th className="text-left px-4 py-3 font-medium">Exchange</th>
            </tr>
          </thead>
          <tbody>
            {instructions.map((inst, i) => (
              <tr key={i} className="border-b border-gray-700/20 last:border-0">
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${actionColor(inst.action)}`}>
                    {inst.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-white font-medium">{inst.symbol}</td>
                <td className="px-4 py-3 text-right text-gray-200">{inst.quantity}</td>
                <td className="px-4 py-3 text-gray-400">{inst.exchange || 'NSE'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {error && (
        <div className="mb-4 px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
          {error}
        </div>
      )}

      <button
        onClick={handleExecute}
        disabled={loading}
        className="w-full py-3.5 rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" /> Executing Orders...
          </>
        ) : (
          <>
            <Play className="w-4 h-4" /> Execute All Orders
          </>
        )}
      </button>
    </div>
  );
}
