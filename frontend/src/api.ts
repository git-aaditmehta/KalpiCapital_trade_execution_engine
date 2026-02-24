import axios from 'axios';

const API_BASE = import.meta.env.PROD ? '' : '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

export interface BrokerCredentials {
  broker: string;
  api_key?: string;
  api_secret?: string;
  access_token?: string;
  client_id?: string;
}

export interface AuthResponse {
  broker: string;
  authenticated: boolean;
  session_token: string | null;
  user_id: string | null;
  login_url?: string | null;
  message: string;
}

export interface Holding {
  symbol: string;
  quantity: number;
  average_price: number;
  current_price: number | null;
  pnl: number | null;
  exchange: string;
}

export interface TradeInstruction {
  action: 'BUY' | 'SELL' | 'REBALANCE';
  symbol: string;
  quantity: number;
  exchange?: string;
  order_type?: string;
  price?: number | null;
}

export interface ExecutionRequest {
  broker: string;
  mode: 'first_time' | 'rebalance';
  instructions: TradeInstruction[];
  session_token?: string | null;
}

export interface OrderResult {
  symbol: string;
  action: string;
  quantity: number;
  status: 'PENDING' | 'EXECUTED' | 'FAILED' | 'PARTIALLY_FILLED';
  order_id: string | null;
  executed_price: number | null;
  message: string | null;
  timestamp: string;
}

export interface ExecutionSummary {
  broker: string;
  mode: string;
  total_orders: number;
  successful: number;
  failed: number;
  results: OrderResult[];
  timestamp: string;
}

export async function listBrokers(): Promise<string[]> {
  const res = await api.get('/auth/brokers');
  return res.data;
}

export async function connectBroker(creds: BrokerCredentials): Promise<AuthResponse> {
  const res = await api.post('/auth/connect', creds);
  return res.data;
}

export async function getHoldings(broker: string, sessionToken?: string): Promise<Holding[]> {
  const params: Record<string, string> = { broker };
  if (sessionToken) params.session_token = sessionToken;
  const res = await api.get('/portfolio/holdings', { params });
  return res.data;
}

export async function executePortfolio(request: ExecutionRequest): Promise<ExecutionSummary> {
  const response = await api.post('/portfolio/execute', request);
  return response.data;
}

export async function getSymbols(broker: string, sessionToken?: string, query?: string): Promise<{ symbols: string[] }> {
  const params = new URLSearchParams();
  if (sessionToken) params.append('session_token', sessionToken);
  if (query) params.append('query', query);
  
  const response = await api.get(`/portfolio/symbols/${broker}?${params}`);
  return response.data;
}

// Zerodha-specific OAuth functions
export async function zerodhaLogin(): Promise<AuthResponse> {
  const response = await api.get('/broker/zerodha/login');
  return response.data;
}

export async function zerodhaCallback(requestToken: string): Promise<AuthResponse> {
  const response = await api.post('/broker/zerodha/callback', { request_token: requestToken });
  return response.data;
}

export async function getSupportedBrokers(): Promise<{ brokers: string[] }> {
  const response = await api.get('/broker/supported');
  return response.data;
}

export async function getBrokerHoldings(broker: string, accessToken: string): Promise<Holding[]> {
  const response = await api.get(`/broker/${broker}/holdings?access_token=${accessToken}`);
  return response.data;
}

export async function placeBrokerOrder(broker: string, accessToken: string, instruction: TradeInstruction): Promise<OrderResult> {
  const response = await api.post(`/broker/${broker}/order?access_token=${accessToken}`, instruction);
  return response.data;
}

export async function executeBrokerTrades(broker: string, accessToken: string, trades: TradeInstruction[]): Promise<ExecutionSummary> {
  const response = await api.post(`/broker/${broker}/execute`, {
    broker: broker,
    access_token: accessToken,
    trades: trades
  });
  return response.data;
}

export async function getBrokerOrderStatus(broker: string, accessToken: string, orderId: string): Promise<OrderResult> {
  const response = await api.post(`/broker/${broker}/order-status`, {
    broker: broker,
    access_token: accessToken,
    order_id: orderId
  });
  return response.data;
}
