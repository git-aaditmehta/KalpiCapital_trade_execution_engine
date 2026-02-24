# Zerodha Integration Documentation

## Overview

This document describes the complete Zerodha broker integration using the Kite Connect Python SDK, following clean architecture and adapter pattern principles.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Routes    │    │  Service Layer  │
│                 │◄──►│                 │◄──►│                 │
│  React/Vue      │    │ FastAPI Routes  │    │ BrokerService   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Execution      │    │  Broker Registry│    │  ZerodhaAdapter │
│  Engine         │◄──►│                 │◄──►│                 │
│ TradeExecutor   │    │ get_adapter()   │    │ KiteConnect SDK │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Components

### 1. ZerodhaAdapter (`app/brokers/zerodha.py`)

Implements the `BrokerAdapter` interface for Zerodha integration.

**Key Features:**
- OAuth authentication flow
- Holdings fetching
- Order placement and status checking
- Comprehensive error handling and logging

**Methods:**
- `authenticate()` - OAuth login and token exchange
- `get_holdings()` - Fetch portfolio holdings
- `place_order()` - Place buy/sell orders
- `get_order_status()` - Check order status

### 2. BrokerService (`app/services/broker_service.py`)

Service layer that provides a high-level interface for broker operations.

**Methods:**
- `connect_zerodha()` - Initiate OAuth flow
- `zerodha_callback()` - Handle OAuth callback
- `get_holdings()` - Fetch holdings for any broker
- `place_order()` - Place single order
- `execute_trades()` - Execute multiple trades
- `get_order_status()` - Check order status

### 3. Broker Registry (`app/brokers/registry.py`)

Central registry for all broker adapters.

**Features:**
- Dynamic adapter selection
- Auto-registration of built-in adapters
- Extensible for new brokers

### 4. API Routes (`app/api/broker_routes.py`)

FastAPI routes for broker operations.

**Endpoints:**
- `GET /broker/zerodha/login` - Initiate OAuth
- `POST /broker/zerodha/callback` - Handle OAuth callback
- `GET /broker/{broker}/holdings` - Fetch holdings
- `POST /broker/{broker}/order` - Place single order
- `POST /broker/{broker}/execute` - Execute multiple trades
- `POST /broker/{broker}/order-status` - Check order status

## OAuth Flow

### Step 1: Initiate Login
```http
GET /broker/zerodha/login
```

**Response:**
```json
{
  "broker": "zerodha",
  "authenticated": false,
  "login_url": "https://kite.zerodha.com/connect/login?api_key=YOUR_API_KEY&v=3",
  "message": "Please login via Kite to continue"
}
```

### Step 2: User Authentication
1. Redirect user to `login_url`
2. User logs in on Kite
3. Kite redirects back with `request_token`

### Step 3: Handle Callback
```http
POST /broker/zerodha/callback
Content-Type: application/json

{
  "request_token": "abc123xyz"
}
```

**Response:**
```json
{
  "broker": "zerodha",
  "authenticated": true,
  "session_token": "access_token_here",
  "user_id": "USER123",
  "message": "Connected to Zerodha as John Doe"
}
```

## Usage Examples

### 1. Connect to Zerodha
```python
from app.services.broker_service import broker_service

# Initiate OAuth
response = await broker_service.connect_zerodha()
login_url = response.login_url

# Handle callback
response = await broker_service.zerodha_callback(request_token)
access_token = response.session_token
```

### 2. Fetch Holdings
```python
holdings = await broker_service.get_holdings("zerodha", access_token)
for holding in holdings:
    print(f"{holding.symbol}: {holding.quantity} shares")
```

### 3. Place Order
```python
from app.models.portfolio import TradeInstruction, TradeAction

instruction = TradeInstruction(
    action=TradeAction.BUY,
    symbol="RELIANCE",
    quantity=10,
    exchange="NSE",
    order_type="MARKET"
)

result = await broker_service.place_order("zerodha", access_token, instruction)
if result.status.value == "EXECUTED":
    print(f"Order placed: {result.order_id}")
```

### 4. Execute Multiple Trades
```python
trades = [
    TradeInstruction(action=TradeAction.BUY, symbol="RELIANCE", quantity=10),
    TradeInstruction(action=TradeAction.SELL, symbol="TCS", quantity=5),
]

summary = await broker_service.execute_trades("zerodha", access_token, trades)
print(f"Executed: {summary.successful}/{summary.total_orders}")
```

## Configuration

### Environment Variables
```bash
# Zerodha API credentials
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret
ZERODHA_ACCESS_TOKEN=your_access_token  # Optional, for testing
```

### Kite Developer Portal Setup
1. Create app at https://developers.kite.trade
2. Get `api_key` and `api_secret`
3. Set redirect URL to your callback endpoint
4. Enable required permissions (holdings, orders)

## Error Handling

### Common Errors
1. **Missing API Key**: Set `ZERODHA_API_KEY` in environment
2. **Invalid Request Token**: User must re-authenticate
3. **Insufficient Funds**: Check account balance
4. **Market Closed**: Orders only work during market hours
5. **Invalid Symbol**: Use correct trading symbols

### Error Response Format
```json
{
  "detail": "Error message description"
}
```

## Logging

The integration provides comprehensive logging:

```
🔐 Starting Zerodha authentication
🔗 Generated Zerodha login URL: https://kite.zerodha.com/connect/login?...
🔄 Exchanging request_token for access_token
✅ Token exchange successful for user: John Doe
📊 Fetching Zerodha holdings
✅ Retrieved 15 holdings from Zerodha
📈 Placing Zerodha order: BUY 10 RELIANCE
✅ Zerodha order placed successfully: 1234567890
```

## Testing

### Unit Tests
```bash
pytest tests/test_zerodha_integration.py -v
```

### Manual Testing
1. Set up Zerodha API credentials
2. Run the backend server
3. Test OAuth flow via API endpoints
4. Verify holdings and order placement

## Security Considerations

1. **API Secret**: Never expose in frontend
2. **Access Tokens**: Store securely, expire daily
3. **HTTPS**: Use HTTPS for all API calls
4. **Rate Limits**: Respect Kite Connect rate limits
5. **Input Validation**: Validate all user inputs

## Rate Limits

Kite Connect imposes rate limits:
- **Login requests**: 200 requests per minute
- **Orders**: 20 requests per second
- **Holdings**: 60 requests per minute
- **Order status**: 60 requests per minute

## Production Deployment

### Checklist
- [ ] Set up API credentials in production
- [ ] Configure HTTPS
- [ ] Set up logging and monitoring
- [ ] Implement rate limiting
- [ ] Add error alerting
- [ ] Test with real account (small amounts)

### Monitoring
Monitor these metrics:
- Authentication success/failure rates
- Order execution success rates
- API response times
- Error frequencies

## Troubleshooting

### Common Issues
1. **"Invalid session"**: Access token expired, re-authenticate
2. **"Permission denied"**: Check API permissions
3. **"Invalid symbol"**: Use correct trading symbols
4. **"Market closed"**: Check market hours

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

- **Kite Connect Docs**: https://kite.trade/docs/connect/v3/
- **Kite Developer Portal**: https://developers.kite.trade
- **API Support**: support@zerodha.com

## Future Enhancements

1. **WebSocket Integration**: Real-time price updates
2. **Advanced Orders**: Cover orders, bracket orders
3. **Portfolio Analytics**: Holdings analysis
4. **Multi-Broker**: Unified interface across brokers
5. **Backtesting**: Historical order simulation
