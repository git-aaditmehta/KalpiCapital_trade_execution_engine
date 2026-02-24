import React from 'react';
import { ExecutionSummary } from '../api';
import { CheckCircle2, XCircle, RotateCcw, BarChart3 } from 'lucide-react';

interface Props {
  summary: ExecutionSummary;
  onReset: () => void;
}

export default function ResultsView({ summary, onReset }: Props) {
  const successRate = summary.total_orders > 0
    ? Math.round((summary.successful / summary.total_orders) * 100)
    : 0;

  const statusColor = (status: string) => {
    switch (status) {
      case 'EXECUTED': return 'text-emerald-400 bg-emerald-500/10';
      case 'FAILED': return 'text-red-400 bg-red-500/10';
      case 'PARTIALLY_FILLED': return 'text-amber-400 bg-amber-500/10';
      default: return 'text-gray-400 bg-gray-500/10';
    }
  };

  const actionColor = (action: string) => {
    switch (action) {
      case 'BUY': return 'text-emerald-400';
      case 'SELL': return 'text-red-400';
      default: return 'text-amber-400';
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-1 flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-emerald-400" />
        Execution Results
      </h2>
      <p className="text-sm text-gray-400 mb-5">
        Trades executed on <span className="text-emerald-400 font-medium">{summary.broker}</span>
        {' '}({summary.mode === 'first_time' ? 'First-Time' : 'Rebalance'})
      </p>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-white">{summary.total_orders}</div>
          <div className="text-xs text-gray-400 mt-1">Total Orders</div>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-emerald-400">{summary.successful}</div>
          <div className="text-xs text-emerald-400/70 mt-1">Successful</div>
        </div>
        <div className={`${summary.failed > 0 ? 'bg-red-500/10 border-red-500/20' : 'bg-gray-800/50 border-gray-700/50'} border rounded-lg p-4 text-center`}>
          <div className={`text-2xl font-bold ${summary.failed > 0 ? 'text-red-400' : 'text-gray-500'}`}>
            {summary.failed}
          </div>
          <div className={`text-xs mt-1 ${summary.failed > 0 ? 'text-red-400/70' : 'text-gray-500'}`}>Failed</div>
        </div>
      </div>

      {/* Success Rate Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>Success Rate</span>
          <span>{successRate}%</span>
        </div>
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-500"
            style={{ width: `${successRate}%` }}
          />
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 mb-5 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700/50 text-gray-400">
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-left px-4 py-3 font-medium">Action</th>
              <th className="text-left px-4 py-3 font-medium">Symbol</th>
              <th className="text-right px-4 py-3 font-medium">Qty</th>
              <th className="text-right px-4 py-3 font-medium">Price</th>
              <th className="text-left px-4 py-3 font-medium">Order ID</th>
            </tr>
          </thead>
          <tbody>
            {summary.results.map((r, i) => (
              <tr key={i} className="border-b border-gray-700/20 last:border-0">
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${statusColor(r.status)}`}>
                    {r.status === 'EXECUTED' ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {r.status}
                  </span>
                </td>
                <td className={`px-4 py-3 font-medium ${actionColor(r.action)}`}>{r.action}</td>
                <td className="px-4 py-3 text-white font-medium">{r.symbol}</td>
                <td className="px-4 py-3 text-right text-gray-200">{r.quantity}</td>
                <td className="px-4 py-3 text-right text-gray-300">
                  {r.executed_price ? `₹${r.executed_price.toLocaleString()}` : '—'}
                </td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{r.order_id || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Failed Order Messages */}
      {summary.results.some((r) => r.status === 'FAILED') && (
        <div className="mb-5 space-y-2">
          <h4 className="text-sm font-medium text-red-400">Failed Order Details</h4>
          {summary.results
            .filter((r) => r.status === 'FAILED')
            .map((r, i) => (
              <div key={i} className="px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-300">
                <span className="font-medium">{r.symbol}</span>: {r.message}
              </div>
            ))}
        </div>
      )}

      <button
        onClick={onReset}
        className="w-full py-3 rounded-lg font-medium text-sm bg-gray-800 hover:bg-gray-700 text-gray-300 flex items-center justify-center gap-2"
      >
        <RotateCcw className="w-4 h-4" /> Start New Execution
      </button>
    </div>
  );
}
