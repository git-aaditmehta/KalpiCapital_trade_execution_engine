import React, { useState, useEffect, useRef } from 'react';
import { TradeInstruction, getHoldings, getSymbols, getBrokerHoldings } from '../api';
import { Upload, FileJson, Plus, Trash2, Download, Search } from 'lucide-react';

interface Props {
  broker: string;
  sessionToken?: string | null;
  onReady: (instructions: TradeInstruction[], mode: 'first_time' | 'rebalance') => void;
}

const SAMPLE_FIRST_TIME: TradeInstruction[] = [
  { action: 'BUY', symbol: 'RELIANCE', quantity: 10 },
  { action: 'BUY', symbol: 'TCS', quantity: 5 },
  { action: 'BUY', symbol: 'INFY', quantity: 15 },
  { action: 'BUY', symbol: 'HDFCBANK', quantity: 20 },
];

const SAMPLE_REBALANCE: TradeInstruction[] = [
  { action: 'SELL', symbol: 'INFY', quantity: 5 },
  { action: 'BUY', symbol: 'ADANIENT', quantity: 8 },
  { action: 'REBALANCE', symbol: 'RELIANCE', quantity: -3 },
  { action: 'REBALANCE', symbol: 'HDFCBANK', quantity: 5 },
];

export default function PortfolioUpload({ broker, sessionToken, onReady }: Props) {
  const [mode, setMode] = useState<'first_time' | 'rebalance'>('first_time');
  const [instructions, setInstructions] = useState<TradeInstruction[]>(SAMPLE_FIRST_TIME);
  const [jsonInput, setJsonInput] = useState('');
  const [inputMode, setInputMode] = useState<'form' | 'json'>('form');
  const [importing, setImporting] = useState(false);
  const [showHoldings, setShowHoldings] = useState(false);
  const [currentHoldings, setCurrentHoldings] = useState<any[]>([]);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [symbolSuggestions, setSymbolSuggestions] = useState<string[]>([]);
  const [loadingSymbols, setLoadingSymbols] = useState(false);
  const [showDropdown, setShowDropdown] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Load symbols when broker changes or component mounts
  useEffect(() => {
    if (broker === 'dhan' && sessionToken) {
      loadSymbols();
    }
  }, [broker, sessionToken]);

  const loadSymbols = async () => {
    if (!sessionToken || broker !== 'dhan') return;
    
    setLoadingSymbols(true);
    try {
      const response = await getSymbols(broker, sessionToken);
      setAvailableSymbols(response.symbols);
    } catch (err) {
      console.error('Failed to load symbols:', err);
    } finally {
      setLoadingSymbols(false);
    }
  };

  const handleSymbolSearch = async (query: string, rowIndex: number) => {
    setSearchQuery(query);
    setShowDropdown(rowIndex);
    
    if (query.length < 2) {
      setSymbolSuggestions([]);
      return;
    }
    
    // Static symbols as fallback
    const staticSymbols = [
      "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "ITC", "SBIN",
      "TATAMOTORS", "WIPRO", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK",
      "MARUTI", "BAJFINANCE", "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO",
      "ASIANPAINT", "NESTLEIND", "ADANIENT", "ADANIPORTS", "POWERGRID",
      "NTPC", "ONGC", "JSWSTEEL", "TATASTEEL", "HINDALCO", "TECHM",
      "NHPC", "COALINDIA", "BPCL", "DRREDDY", "DIVISLAB", "EICHERMOT",
      "HEROMOTOCO", "M&M", "INDUSINDBK", "CIPLA", "GRASIM", "APOLLOHOSP",
      "BRITANNIA", "TATACONSUM", "SBILIFE", "HDFCLIFE", "BAJAJFINSV",
      "HINDUNILVR", "GROWW", "IOC", "IDBI", "EQUITASBNK", "PFC", "IRCTC",
      "MAHABANK", "NIFTYBEES", "GOLDBEES", "SILVERBEES"
    ];
    
    // Filter static symbols
    const filtered = staticSymbols.filter(symbol => 
      symbol.toUpperCase().includes(query.toUpperCase())
    ).slice(0, 10);
    
    // Try API if available
    if (sessionToken && broker === 'dhan') {
      try {
        const response = await getSymbols(broker, sessionToken, query);
        setSymbolSuggestions(response.symbols.slice(0, 10));
      } catch (err) {
        console.log('API search failed, using static symbols:', err);
        setSymbolSuggestions(filtered);
      }
    } else {
      setSymbolSuggestions(filtered);
    }
  };

  const selectSymbol = (symbol: string, rowIndex: number) => {
    console.log(`🎯 SELECTING SYMBOL: ${symbol} for row ${rowIndex}`);
    const updated = [...instructions];
    updated[rowIndex] = { ...updated[rowIndex], symbol: symbol.toUpperCase() };
    setInstructions(updated);
    setShowDropdown(null);
    setSymbolSuggestions([]);
    setSearchQuery('');
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showDropdown !== null && dropdownRefs.current[showDropdown]) {
        if (!dropdownRefs.current[showDropdown]?.contains(event.target as Node)) {
          setShowDropdown(null);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showDropdown]);

  const handleLoadSample = () => {
    setInstructions(mode === 'first_time' ? SAMPLE_FIRST_TIME : SAMPLE_REBALANCE);
  };

  const handleAddRow = () => {
    setInstructions([...instructions, { action: 'BUY', symbol: '', quantity: 0 }]);
  };

  const handleRemoveRow = (index: number) => {
    setInstructions(instructions.filter((_, i) => i !== index));
  };

  const handleChange = (index: number, field: keyof TradeInstruction, value: string | number) => {
    const updated = [...instructions];
    updated[index] = { ...updated[index], [field]: value };
    setInstructions(updated);
  };

  const handleJsonImport = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      if (Array.isArray(parsed)) {
        setInstructions(parsed);
        setInputMode('form');
      }
    } catch {
      alert('Invalid JSON format');
    }
  };

  const handleImportHoldings = async () => {
    setImporting(true);
    try {
      // Use new broker API for Zerodha, fallback to old API for others
      let holdings;
      if (broker === 'zerodha' && sessionToken) {
        holdings = await getBrokerHoldings(broker, sessionToken);
      } else {
        holdings = await getHoldings(broker, sessionToken || undefined);
      }
      
      setCurrentHoldings(holdings);
      setShowHoldings(true);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to import holdings');
    } finally {
      setImporting(false);
    }
  };

  const handleUseHoldingsForRebalance = () => {
    const imported: TradeInstruction[] = currentHoldings.map(h => ({
      action: 'REBALANCE' as const,
      symbol: h.symbol,
      quantity: h.quantity,
    }));
    setInstructions(imported);
    setMode('rebalance');
    setShowHoldings(false);
  };

  const handleSubmit = () => {
    const valid = instructions.filter((i) => i.symbol && i.quantity !== 0);
    if (valid.length === 0) {
      alert('Please add at least one valid instruction');
      return;
    }
    onReady(valid, mode);
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-1 flex items-center gap-2">
        <Upload className="w-5 h-5 text-emerald-400" />
        Portfolio Instructions
      </h2>
      <p className="text-sm text-gray-400 mb-5">
        Connected to <span className="text-emerald-400 font-medium">{broker}</span>. Define your trade instructions.
      </p>

      {/* Holdings Display Modal */}
      {showHoldings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-white mb-4">Your Current Holdings</h3>
            <div className="space-y-2 mb-6">
              {currentHoldings.map((h, i) => (
                <div key={i} className="bg-gray-800/50 rounded-lg p-3 flex justify-between items-center">
                  <div>
                    <div className="font-medium text-white">{h.symbol}</div>
                    <div className="text-sm text-gray-400">{h.exchange}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium text-white">{h.quantity} shares</div>
                    <div className="text-sm text-gray-400">
                      Avg: ₹{h.average_price} | LTP: ₹{h.current_price}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowHoldings(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleUseHoldingsForRebalance}
                className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg"
              >
                Use for Rebalancing
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mode Toggle */}
      <div className="flex gap-2 mb-5">
        {(['first_time', 'rebalance'] as const).map((m) => (
          <button
            key={m}
            onClick={() => { setMode(m); handleLoadSample(); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              mode === m
                ? 'bg-emerald-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            {m === 'first_time' ? 'First-Time Buy' : 'Rebalance'}
          </button>
        ))}
      </div>

      {/* Input Mode Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setInputMode('form')}
          className={`px-3 py-1.5 rounded text-xs font-medium ${
            inputMode === 'form' ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Form Input
        </button>
        <button
          onClick={() => setInputMode('json')}
          className={`px-3 py-1.5 rounded text-xs font-medium flex items-center gap-1 ${
            inputMode === 'json' ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          <FileJson className="w-3 h-3" /> JSON Import
        </button>
      </div>

      {inputMode === 'json' ? (
        <div className="mb-5">
          <textarea
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            placeholder={`[\n  {"action": "BUY", "symbol": "RELIANCE", "quantity": 10},\n  {"action": "SELL", "symbol": "INFY", "quantity": 5}\n]`}
            className="w-full h-40 bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 font-mono focus:outline-none focus:border-emerald-500"
          />
          <button
            onClick={handleJsonImport}
            className="mt-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg"
          >
            Parse JSON
          </button>
        </div>
      ) : (
        <div className="mb-5 space-y-2">
          {/* Header */}
          <div className="grid grid-cols-12 gap-2 text-xs text-gray-500 font-medium px-1">
            <div className="col-span-3">Action</div>
            <div className="col-span-4">Symbol</div>
            <div className="col-span-3">Quantity</div>
            <div className="col-span-2"></div>
          </div>
          {instructions.map((inst, i) => (
            <div key={i} className="grid grid-cols-12 gap-2">
              <select
                value={inst.action}
                onChange={(e) => handleChange(i, 'action', e.target.value)}
                className="col-span-3 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
                {mode === 'rebalance' && <option value="REBALANCE">REBALANCE</option>}
              </select>
              <div className="col-span-4 relative" ref={(el) => dropdownRefs.current[i] = el}>
                <div className="relative">
                  <input
                    type="text"
                    value={inst.symbol}
                    onChange={(e) => {
                      handleChange(i, 'symbol', e.target.value.toUpperCase());
                      handleSymbolSearch(e.target.value, i);
                    }}
                    onFocus={() => handleSymbolSearch(inst.symbol, i)}
                    placeholder={broker === 'dhan' ? "Search any stock..." : "e.g. RELIANCE"}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 pr-8 text-sm text-gray-200 focus:outline-none focus:border-emerald-500"
                  />
                  {broker === 'dhan' && (
                    <Search className="absolute right-2 top-2.5 w-3 h-3 text-gray-500" />
                  )}
                </div>
                
                {/* Dropdown suggestions */}
                {showDropdown === i && symbolSuggestions.length > 0 && (
                  <div className="absolute top-full mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
                    {symbolSuggestions.map((symbol, idx) => (
                      <div
                        key={idx}
                        onClick={() => selectSymbol(symbol, i)}
                        className="px-3 py-2 text-sm text-gray-200 hover:bg-gray-700 cursor-pointer transition-colors"
                      >
                        {symbol}
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <input
                type="number"
                value={inst.quantity}
                onChange={(e) => handleChange(i, 'quantity', parseInt(e.target.value) || 0)}
                className="col-span-3 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-emerald-500"
              />
              <button
                onClick={() => handleRemoveRow(i)}
                className="col-span-2 flex items-center justify-center text-gray-500 hover:text-red-400 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
          <button
            onClick={handleAddRow}
            className="flex items-center gap-1 text-sm text-emerald-400 hover:text-emerald-300 mt-2"
          >
            <Plus className="w-4 h-4" /> Add Row
          </button>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={handleLoadSample}
          className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded-lg"
        >
          Load Sample Data
        </button>
        {broker !== 'groww' && (
          <button
            onClick={handleImportHoldings}
            disabled={importing}
            className="px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg flex items-center gap-2"
          >
            {importing ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Importing...
              </>
            ) : (
              <>
                <Download className="w-3 h-3" />
                Import Holdings
              </>
            )}
          </button>
        )}
        <button
          onClick={handleSubmit}
          className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg"
        >
          Continue to Execution
        </button>
      </div>
    </div>
  );
}
