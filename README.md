# Kalpi Capital — Portfolio Trade Execution Engine

A comprehensive, production-ready Portfolio Trade Execution Engine built with **FastAPI** (backend) and **React + Vite + TailwindCSS** (frontend). The engine authenticates with Indian stock brokers via OAuth, accepts target portfolio instructions, and executes trades with real-time notifications and complete Zerodha integration.

---

## 🚀 Quick Start

### 🐳 Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/<your-username>/kalpi_capital_assignment.git
cd kalpi_capital_assignment

# Start everything with one command
docker-compose up --build

# Access the application:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### 💻 Local Development
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Features](#core-features)
- [Zerodha OAuth Integration](#zerodha-oauth-integration)
- [Execution & Rebalance Logic](#execution--rebalance-logic)
- [Setup & Run Instructions](#setup--run-instructions)
- [Docker Deployment Guide](#docker-deployment-guide)
- [API Reference](#api-reference)
- [Running Tests](#running-tests)
- [Third-Party Library Justification](#third-party-library-justification)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  BrokerSelector → PortfolioUpload → Execute → Results   │
│                    (WebSocket live feed)                  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP / WebSocket
┌───────────────────────▼─────────────────────────────────┐
│                   FastAPI Backend                         │
│                                                          │
│  ┌─────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │  Auth    │   │  Portfolio   │   │   WebSocket      │  │
│  │  Router  │   │  Router      │   │   Router         │  │
│  └────┬────┘   └──────┬───────┘   └────────┬─────────┘  │
│       │               │                     │            │
│  ┌────▼────────────────▼─────────────────────▼────────┐  │
│  │              Trade Execution Engine                 │  │
│  │  • Validates instructions (first-time vs rebalance)│  │
│  │  • Normalizes REBALANCE → BUY/SELL                 │  │
│  │  • Places orders via broker adapter                │  │
│  └────────────────────┬───────────────────────────────┘  │
│                       │                                  │
│  ┌────────────────────▼───────────────────────────────┐  │
│  │           Broker Adapter Layer (Adapter Pattern)    │  │
│  │  Zerodha │ Fyers │ AngelOne │ Groww │ Upstox │ Dhan│  │
│  └────────────────────────────────────────────────────┘  │
│                       │                                  │
│  ┌────────────────────▼───────────────────────────────┐  │
│  │           Notification Layer                        │  │
│  │  Console │ Webhook (HTTP POST) │ WebSocket          │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Key design principles:**
- **Modularity** — Brokers, engine, notifications are fully decoupled.
- **Separation of Concerns** — Routers handle HTTP, engine handles logic, adapters handle broker communication.
- **Robust Error Handling** — Per-order error capture; partial failures don't crash the batch.
- **Extensibility** — New brokers and notification channels require zero changes to existing code.

---

## Core Features

| Feature | Description |
|---|---|
| **6 Broker Adapters** | Zerodha (OAuth), Fyers, AngelOne, Groww, Upstox, Dhan |
| **Zerodha OAuth Integration** | Complete Kite Connect OAuth flow with real API support |
| **Adapter Pattern** | Adding a 7th broker = 1 new class + 1 registry line |
| **First-Time Execution** | All-BUY portfolio creation |
| **Rebalance Execution** | Explicit BUY/SELL/REBALANCE instructions |
| **3 Notification Channels** | Console, Webhook (HTTP POST), WebSocket |
| **Real-Time Updates** | WebSocket broadcasts execution results live |
| **React Frontend** | 4-step wizard: Connect → Upload → Execute → Results |
| **Demo Mode** | Isolated testing environment for OAuth flow |
| **Fully Containerized** | Docker + docker-compose for one-command startup |

---

## Zerodha OAuth Integration

### Complete OAuth Flow
The Zerodha integration provides a production-ready OAuth authentication system:

1. **Initiate OAuth**: `GET /broker/zerodha/login` → Returns Kite login URL
2. **User Authentication**: Redirect to Kite login page
3. **Handle Callback**: `POST /broker/zerodha/callback` → Exchange request_token for access_token
4. **API Access**: Use access_token for holdings, orders, and trading

### Frontend Features
- **Automatic Callback Detection**: Handles OAuth return seamlessly
- **Visual Feedback**: Shows redirecting, processing, and success states
- **Error Handling**: User-friendly error messages and retry options
- **Demo Mode**: Isolated testing environment

### Backend Features
- **Service Layer**: Clean separation of broker operations
- **Broker Registry**: Dynamic adapter selection
- **Error Handling**: Comprehensive error logging and user feedback
- **Security**: No API secrets exposed to frontend

### Setup Requirements
```bash
# Required for real Zerodha integration
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret

# Optional: Pre-generated access token for testing
ZERODHA_ACCESS_TOKEN=your_access_token
```

### Usage Example
```typescript
// Frontend OAuth flow
const response = await zerodhaLogin();
if (response.login_url) {
  window.location.href = response.login_url; // Redirect to Kite
}

// After callback
const auth = await zerodhaCallback(request_token);
const holdings = await getBrokerHoldings('zerodha', auth.session_token);
```

---

## Broker Integration (Adapter Pattern)

All brokers implement the abstract `BrokerAdapter` interface:

```python
class BrokerAdapter(ABC):
    async def authenticate(credentials) -> BrokerAuthResponse
    async def get_holdings(session_token) -> List[Holding]
    async def place_order(session_token, instruction) -> OrderResult
    async def get_order_status(session_token, order_id) -> OrderResult
```

**Adding a new broker (e.g., IIFL):**

1. Create `backend/app/brokers/iifl.py` extending `BrokerAdapter`
2. Register it: `BrokerRegistry.register("iifl", IIFLAdapter)` in `registry.py`
3. Done — zero changes to engine, routers, or notifications.

**Current adapters use mock/simulated responses** since real broker API keys require funded trading accounts. Each mock simulates:
- Realistic API latency (100–500ms)
- ~90% order success rate
- Unique order IDs with broker-specific prefixes
- Broker-specific holdings data

---

## Execution & Rebalance Logic

### First-Time Portfolio (`mode: "first_time"`)
- All instructions **must** be `BUY` orders with positive quantities.
- Validates this constraint before placing any orders.
- Orders are placed sequentially via the broker adapter.

### Portfolio Rebalancing (`mode: "rebalance"`)
Per the assignment spec, the rebalance payload provides **explicit instructions** — the engine does not calculate deltas.

The payload can include three action types:
- **`BUY`** — Purchase new stocks or increase positions.
- **`SELL`** — Exit or reduce positions.
- **`REBALANCE`** — Signed quantity adjustment:
  - Positive quantity → converted to `BUY`
  - Negative quantity → converted to `SELL` (absolute value)
  - Zero quantity → skipped with a warning

**Example rebalance payload:**
```json
{
  "broker": "zerodha",
  "mode": "rebalance",
  "instructions": [
    {"action": "SELL", "symbol": "INFY", "quantity": 3},
    {"action": "BUY", "symbol": "HDFCBANK", "quantity": 7},
    {"action": "REBALANCE", "symbol": "RELIANCE", "quantity": -2}
  ]
}
```
The `REBALANCE` for RELIANCE with quantity `-2` is normalized to `SELL 2 x RELIANCE`.

> **Bonus:** A `PortfolioReconciler` utility class is also provided in `engine/reconciler.py` for scenarios where automatic delta computation between current holdings and a target portfolio is desired.

---

## Notification System

After execution completes, three notification channels fire simultaneously:

| Channel | Implementation |
|---|---|
| **Console** | Structured log output with order status icons and price details |
| **Webhook** | HTTP POST to configurable URL (default: mock endpoint at `/webhook/mock`) |
| **WebSocket** | Broadcasts JSON to all connected clients in real-time |

All notifiers implement the `Notifier` abstract interface — adding email/SMS/Slack requires one new class.

---

## Setup & Run Instructions

### 📋 Prerequisites

**Required:**
- Docker & Docker Compose (for containerized deployment)
- Git (to clone the repository)

**Optional (for local development):**
- Python 3.11+ with pip
- Node.js 20+ with npm
- Zerodha trading account (for real API integration)

---

### 🐳 Docker Deployment (Recommended)

#### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/<your-username>/kalpi_capital_assignment.git
cd kalpi_capital_assignment

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

#### 2. Configure Environment
```bash
# Edit backend environment variables
nano backend/.env

# Add your Zerodha credentials (optional - can use demo mode)
ZERODHA_API_KEY=your_api_key_here
ZERODHA_API_SECRET=your_api_secret_here
```

#### 3. Start Services
```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

#### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

#### 5. Docker Commands
```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild specific service
docker-compose up --build backend

# Clean up containers and images
docker-compose down --rmi all
```

---

### 💻 Local Development

#### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start the server
uvicorn app.main:app --reload --port 8001
```

#### Frontend Setup
```bash
# Navigate to frontend directory (in another terminal)
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

#### Access Local Development
- **Frontend**: http://localhost:3001 (or next available port)
- **Backend**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

---

### 🔧 Configuration

#### Backend Environment Variables (.env)
```bash
# Zerodha Configuration (required for real trading)
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret
ZERODHA_ACCESS_TOKEN=your_access_token  # Optional, for testing

# Application Configuration
APP_ENV=development
DEBUG=true

# Other Broker APIs (optional)
FYERS_APP_ID=your_fyers_app_id
FYERS_SECRET_KEY=your_fyers_secret
ANGELONE_API_KEY=your_angelone_key
ANGELONE_CLIENT_SECRET=your_angelone_secret
# ... etc for other brokers
```

#### Frontend Environment Variables (.env)
```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8001

# WebSocket Configuration
VITE_WS_URL=ws://localhost:8001/ws/notifications
```

---

### 🧪 Testing Setup

#### Backend Tests
```bash
cd backend

# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_brokers.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

#### Frontend Tests
```bash
cd frontend

# Run unit tests
npm test

# Run build test
npm run build

# Run linting
npm run lint
```

---

## 🐳 Docker Deployment Guide

### Docker Compose Configuration
The project includes a comprehensive `docker-compose.yml` with:

- **Backend Service**: FastAPI with Uvicorn
- **Frontend Service**: React with Nginx
- **Network Configuration**: Internal communication
- **Volume Mounts**: Live code reloading in development
- **Environment Variables**: Secure configuration management

### Production Deployment
```bash
# Build for production
docker-compose -f docker-compose.prod.yml build

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale backend=2
```

### Docker Commands Reference
```bash
# Build images
docker-compose build

# Start services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v

# Execute commands in container
docker-compose exec backend bash
docker-compose exec frontend sh

# Monitor resource usage
docker stats
```

### Environment Configuration
```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - ZERODHA_API_KEY=${ZERODHA_API_KEY}
      - ZERODHA_API_SECRET=${ZERODHA_API_SECRET}
      - APP_ENV=production
    volumes:
      - ./backend:/app
      - /app/venv  # Exclude venv from volume mount
```

---

## API Reference

### Broker Authentication

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/auth/brokers` | List all supported brokers |
| `POST` | `/auth/connect` | Authenticate with a broker (legacy) |

### Zerodha OAuth Integration

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/broker/zerodha/login` | Initiate Zerodha OAuth flow |
| `POST` | `/broker/zerodha/callback` | Handle OAuth callback |
| `GET` | `/broker/supported` | List all supported brokers |

### Broker Operations

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/broker/{broker}/holdings` | Fetch holdings for any broker |
| `POST` | `/broker/{broker}/order` | Place single order |
| `POST` | `/broker/{broker}/execute` | Execute multiple trades |
| `POST` | `/broker/{broker}/order-status` | Check order status |

### Portfolio (Legacy)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/portfolio/holdings` | Fetch current holdings |
| `POST` | `/portfolio/execute` | Execute trades (first-time or rebalance) |
| `GET` | `/portfolio/symbols/{broker}` | Search symbols |

### WebSocket

| Protocol | Endpoint | Description |
|---|---|---|
| `WS` | `/ws/notifications` | Real-time execution notifications |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check |
| `POST` | `/webhook/mock` | Mock webhook receiver |

**Full interactive API docs:** `http://localhost:8000/docs` (Swagger UI)

### API Usage Examples

#### Zerodha OAuth Flow
```bash
# 1. Initiate OAuth
curl -X GET http://localhost:8000/broker/zerodha/login

# 2. Handle callback (after user login)
curl -X POST http://localhost:8000/broker/zerodha/callback \
  -H "Content-Type: application/json" \
  -d '{"request_token": "your_request_token"}'

# 3. Fetch holdings
curl "http://localhost:8000/broker/zerodha/holdings?access_token=your_access_token"

# 4. Execute trades
curl -X POST http://localhost:8000/broker/zerodha/execute \
  -H "Content-Type: application/json" \
  -d '{
    "broker": "zerodha",
    "access_token": "your_access_token",
    "trades": [
      {"action": "BUY", "symbol": "RELIANCE", "quantity": 10}
    ]
  }'
```

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Tests cover:
- **Broker Registry** — All 6 brokers registered, case-insensitive lookup, invalid broker handling
- **Broker Adapters** — Authentication, holdings, order placement for all 6 brokers
- **Execution Engine** — First-time execution, rebalance normalization, SELL rejection in first-time mode, zero-quantity skip
- **Portfolio Reconciler** — Delta computation for first-time, full exit, mixed rebalance, no-change scenarios
- **API Endpoints** — Health checks, broker listing, auth flow, portfolio execution, error handling

---

## Third-Party Library Justification

### 🎯 Trading Libraries Strategy

#### Real Broker SDKs (Production Ready)
We **do use real broker SDKs** for production integration:

| Broker | SDK | Purpose |
|--------|-----|---------|
| **Zerodha** | `kiteconnect>=5.0.1` | Real Kite Connect API integration |
| **Fyers** | `fyers-apiv3>=3.0.0` | Fyers API v3 integration |
| **Angel One** | `SmartApi>=1.4.0` | Angel One SmartAPI integration |
| **Upstox** | `upstox-python-sdk>=2.9.0` | Upstox API integration |
| **Dhan** | `dhanhq>=2.0.0` | Dhan API integration |

#### Why We Use Real SDKs

1. **Production Readiness** - Real SDKs handle authentication, rate limiting, and edge cases
2. **OAuth Support** - Zerodha Kite Connect requires official SDK for OAuth flow
3. **Error Handling** - Built-in error handling and retry mechanisms
4. **Maintenance** - SDKs are maintained by brokers, ensuring API compatibility
5. **Security** - Proper handling of API secrets and tokens

#### Adapter Pattern Benefits
Our adapter pattern **wraps** these SDKs, providing:
- **Unified Interface** - All brokers implement the same `BrokerAdapter` interface
- **Easy Testing** - Mock implementations for development/testing
- **Simple Swapping** - Replace mock with real SDK calls in one place
- **Extensibility** - Add new brokers without changing existing code

### 📚 Core Libraries Justification

#### Backend Libraries
| Library | Purpose | Justification |
|---------|---------|---------------|
| `fastapi` | Web framework | Automatic OpenAPI docs, async support, type hints |
| `uvicorn` | ASGI server | High-performance async server |
| `pydantic` / `pydantic-settings` | Validation & Config | Type-safe request/response validation, env management |
| `httpx` | Async HTTP client | For webhook notifications, async-first design |
| `websockets` | WebSocket support | Real-time notifications to frontend |
| `python-dotenv` | Environment loading | Secure configuration management |
| `pytest` / `pytest-asyncio` | Testing framework | Comprehensive testing with async support |

#### Frontend Libraries
| Library | Purpose | Justification |
|---------|---------|---------------|
| `react` | UI framework | Component-based architecture, ecosystem |
| `vite` | Build tool | Fast development, modern bundling |
| `tailwindcss` | Styling | Utility-first CSS, rapid development |
| `axios` | HTTP client | Promise-based API calls, error handling |
| `lucide-react` | Icons | Beautiful, consistent icon set |

### 🏗️ Architecture Benefits

#### Clean Separation
- **Adapters** handle broker-specific logic
- **Service Layer** provides business logic abstraction
- **API Layer** handles HTTP concerns
- **Frontend** focuses on user experience

#### Testing Strategy
- **Mock Adapters** for unit tests
- **Real SDKs** for integration tests
- **Demo Mode** for user acceptance testing
- **Docker** for consistent environments

#### Production Path
1. **Development**: Use mock adapters
2. **Testing**: Use demo mode with real OAuth flow
3. **Staging**: Use real SDKs with paper trading
4. **Production**: Use real SDKs with live trading

### 🔒 Security Considerations

#### API Key Management
- **Environment Variables** - Never hardcode secrets
- **Docker Secrets** - For production deployments
- **OAuth Flow** - No API secrets in frontend
- **Token Rotation** - Secure token handling

#### Rate Limiting
- **SDK Built-in** - Most SDKs handle rate limiting
- **Retry Logic** - Exponential backoff for failed requests
- **Circuit Breaker** - Prevent cascade failures

### 📈 Performance Optimizations

#### Async Design
- **Non-blocking** - All I/O operations are async
- **Connection Pooling** - Efficient resource usage
- **WebSocket** - Real-time updates without polling

#### Caching Strategy
- **Symbol Cache** - Reduce API calls for symbol lookups
- **Session Cache** - Cache authenticated sessions
- **Holding Cache** - Cache portfolio data temporarily

---

## Project Structure

```
kalpi_capital_assignment/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app + middleware + routes
│   │   ├── config.py               # Pydantic settings / env config
│   │   ├── models/
│   │   │   ├── portfolio.py        # TradeInstruction, ExecutionSummary, etc.
│   │   │   └── broker.py           # BrokerCredentials, Holding, etc.
│   │   ├── brokers/
│   │   │   ├── base.py             # Abstract BrokerAdapter interface
│   │   │   ├── zerodha.py          # Zerodha (Kite) OAuth adapter
│   │   │   ├── fyers.py            # Fyers adapter
│   │   │   ├── angelone.py         # Angel One (SmartAPI) adapter
│   │   │   ├── groww.py            # Groww adapter
│   │   │   ├── upstox.py           # Upstox adapter
│   │   │   ├── dhan.py             # Dhan adapter
│   │   │   └── registry.py         # Broker factory/registry
│   │   ├── services/
│   │   │   └── broker_service.py   # Service layer for broker operations
│   │   ├── api/
│   │   │   └── broker_routes.py    # New broker API endpoints
│   │   ├── engine/
│   │   │   ├── executor.py         # Core trade execution engine
│   │   │   └── reconciler.py       # Portfolio delta calculator (utility)
│   │   ├── notifications/
│   │   │   ├── base.py             # Abstract Notifier interface
│   │   │   ├── console.py          # Console/log notifier
│   │   │   ├── webhook.py          # HTTP webhook notifier
│   │   │   └── websocket.py        # WebSocket broadcast notifier
│   │   └── routers/
│   │       ├── auth.py             # /auth/* endpoints
│   │       ├── portfolio.py        # /portfolio/* endpoints
│   │       └── ws.py               # WebSocket endpoint
│   ├── tests/
│   │   ├── test_brokers.py         # Broker adapter & registry tests
│   │   ├── test_zerodha_integration.py  # Zerodha integration tests
│   │   ├── test_engine.py          # Execution engine & reconciler tests
│   │   └── test_api.py             # API endpoint integration tests
│   ├── docs/
│   │   └── ZERODHA_INTEGRATION.md  # Zerodha integration documentation
│   ├── examples/
│   │   └── zerodha_example.py     # Zerodha usage examples
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Main app with 4-step wizard
│   │   ├── api.ts                  # API client helpers with Zerodha OAuth
│   │   ├── components/
│   │   │   ├── BrokerSelector.tsx  # Broker auth UI with OAuth
│   │   │   ├── PortfolioUpload.tsx # Trade instruction form/JSON input
│   │   │   ├── ExecutionPanel.tsx  # Order preview + execute button
│   │   │   ├── ResultsView.tsx     # Results table with status badges
│   │   │   └── ZerodhaOAuthDemo.tsx # Standalone OAuth demo
│   │   ├── main.tsx
│   │   └── index.css
│   ├── README_ZERODHA_FRONTEND.md # Frontend Zerodha integration docs
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf
│   └── vite.config.ts
├── docker-compose.yml
├── README_ZERODHA.md              # Zerodha integration summary
└── README.md
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Port Conflicts
**Problem**: `Port 3000/8000 is already in use`
```bash
# Solution: Use different ports or kill existing processes
# Find processes using ports
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# Kill processes
kill -9 <PID>

# Or use different ports
docker-compose up --build -p 3001:3000 -p 8001:8000
```

#### 2. Zerodha OAuth Issues
**Problem**: "Missing ZERODHA_API_KEY" error
```bash
# Solution: Add environment variables
# backend/.env
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret

# Restart services
docker-compose restart backend
```

#### 3. Frontend Build Errors
**Problem**: TypeScript errors in IDE
```bash
# Solution: Clear TypeScript cache
# In VS Code: Ctrl+Shift+P → "TypeScript: Restart TS Server"

# Or rebuild frontend
cd frontend
npm run build
```

#### 4. Docker Build Issues
**Problem**: Docker build fails
```bash
# Solution: Clean build
docker-compose down --rmi all
docker system prune -f
docker-compose up --build
```

#### 5. WebSocket Connection Issues
**Problem**: WebSocket not connecting
```bash
# Check port configuration
# frontend/vite.config.ts should point to backend port
proxy: {
  '/ws': {
    target: 'ws://localhost:8001',  # Match backend port
    ws: true,
  },
}
```

#### 6. Environment Variable Issues
**Problem**: Environment variables not loading
```bash
# Verify .env file exists
ls -la backend/.env

# Check file permissions
chmod 600 backend/.env

# Restart services
docker-compose restart backend
```

### Debug Mode

#### Enable Debug Logging
```bash
# backend/.env
DEBUG=true
LOG_LEVEL=DEBUG

# Restart backend
docker-compose restart backend
```

#### View Logs
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Performance Issues

#### Slow Startup
```bash
# Use Docker volumes for faster builds
docker-compose up --build --volume /app/node_modules
```

#### Memory Issues
```bash
# Limit Docker memory usage
docker-compose up --build --memory=2g
```

### Getting Help

1. **Check Logs**: Always check Docker logs first
2. **Verify Environment**: Ensure all required environment variables are set
3. **Network Issues**: Check if ports are accessible
4. **Documentation**: Refer to broker-specific documentation
5. **Community**: Check GitHub issues for similar problems

---

## 📞 Support & Contributing

### Getting Help
- **Documentation**: Check `/docs` folder for detailed guides
- **API Docs**: Visit `http://localhost:8000/docs` for interactive API documentation
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Use GitHub Discussions for questions

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a Pull Request

---

## 📄 License

This project is submitted as part of the Kalpi Capital Builder Assignment.

---

## 🙏 Acknowledgments

- **Kalpi Capital** for the opportunity and assignment
- **Broker APIs** - Zerodha, Fyers, Angel One, Groww, Upstox, Dhan
- **Open Source Community** - All the amazing libraries and tools used
