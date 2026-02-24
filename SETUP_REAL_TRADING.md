# Real Trading Setup — Step-by-Step TODO

This guide covers **everything** you need to do to connect your **Dhan** trading account
and use the platform with real data (real holdings, real order placement).

> **WARNING:** Once configured with real credentials, the platform can place REAL orders
> that involve REAL money. Test thoroughly in paper/sandbox mode first if available.

---

## PHASE 1: Dhan API Credentials

### Step 1 — Register on Dhan Developer Portal

- [ ] Go to **https://api.dhan.co** (Dhan's API portal)
- [ ] Log in using your **Dhan trading account** credentials (same as your trading app login)
- [ ] If you don't have an account yet: sign up at **https://dhan.co** and complete KYC

### Step 2 — Create an API App

- [ ] Once logged into the API portal, navigate to **"My Apps"** or **"Create App"**
- [ ] Fill in the app details:
  - **App Name:** `Kalpi Trade Engine` (or any name you prefer)
  - **Redirect URL:** `http://localhost:3000` (for local development)
  - **Description:** Portfolio trade execution engine
- [ ] Submit and wait for approval (usually instant or within minutes)

### Step 3 — Get Your Credentials

After app approval, you'll get two values:

| Credential | Where to find it | What it looks like |
|---|---|---|
| **Client ID** | Dhan API Portal → My Apps → Your App | Numeric string, e.g., `1100012345` |
| **Access Token** | Dhan API Portal → My Apps → Generate Token | Long alphanumeric string |

- [ ] Copy your **Client ID**
- [ ] Generate and copy your **Access Token**
- [ ] Note: The access token may expire daily — you'll need to regenerate it each trading day (Dhan tokens are typically valid for 1 day)

### Step 4 — Configure Environment Variables

- [ ] In the `backend/` folder, copy `.env.example` to `.env`:
  ```
  cp backend/.env.example backend/.env
  ```
- [ ] Open `backend/.env` and fill in your Dhan credentials:
  ```env
  DHAN_CLIENT_ID=<your_client_id_here>
  DHAN_ACCESS_TOKEN=<your_access_token_here>
  ```
- [ ] You can leave all other broker keys empty (they won't be used):
  ```env
  ZERODHA_API_KEY=
  ZERODHA_API_SECRET=
  FYERS_APP_ID=
  FYERS_SECRET_KEY=
  ANGELONE_API_KEY=
  ANGELONE_CLIENT_ID=
  GROWW_API_KEY=
  GROWW_API_SECRET=
  UPSTOX_API_KEY=
  UPSTOX_API_SECRET=
  ```

---

## PHASE 2: Install Dhan SDK

### Step 5 — Install the official Dhan Python package

- [ ] Run from the `backend/` directory:
  ```
  pip install dhanhq
  ```
- [ ] Add `dhanhq` to `backend/requirements.txt`:
  ```
  dhanhq>=2.0
  ```

---

## PHASE 3: Replace Mock Adapter with Real Dhan API

### Step 6 — Update `backend/app/brokers/dhan.py`

This is the **main code change**. Replace the mock adapter with real DhanHQ API calls.

- [ ] Open `backend/app/brokers/dhan.py`
- [ ] Replace the entire file contents with real API integration (see template below)

**Key Dhan API endpoints you'll use:**

| Action | DhanHQ SDK Method | What it does |
|---|---|---|
| Authenticate | `DhanContext(client_id, access_token)` | Initialize authenticated session |
| Get Holdings | `dhan.get_holdings()` | Fetches your current stock holdings |
| Place Order | `dhan.place_order(...)` | Places a BUY/SELL order on NSE/BSE |
| Order Status | `dhan.get_order_by_id(order_id)` | Check if an order was executed |

**Template for the real adapter** (you'll paste this into `dhan.py`):

```python
from dhanhq import dhanhq
from app.brokers.base import BrokerAdapter
from app.models.broker import BrokerCredentials, BrokerAuthResponse, Holding
from app.models.portfolio import TradeInstruction, OrderResult, OrderStatus, TradeAction
from app.config import settings
from typing import List

class DhanAdapter(BrokerAdapter):
    name = "dhan"

    async def authenticate(self, credentials: BrokerCredentials) -> BrokerAuthResponse:
        try:
            # Use credentials from .env or from the request
            client_id = credentials.api_key or settings.dhan_client_id
            access_token = credentials.api_secret or settings.dhan_access_token
            # Test the connection
            dhan = dhanhq(client_id, access_token)
            return BrokerAuthResponse(
                success=True,
                session_token=access_token,
                broker="dhan",
                message="Connected to Dhan successfully"
            )
        except Exception as e:
            return BrokerAuthResponse(
                success=False, broker="dhan",
                message=f"Dhan auth failed: {str(e)}"
            )

    async def get_holdings(self, session_token: str) -> List[Holding]:
        client_id = settings.dhan_client_id
        dhan = dhanhq(client_id, session_token)
        response = dhan.get_holdings()
        holdings = []
        if response and response.get("data"):
            for item in response["data"]:
                holdings.append(Holding(
                    symbol=item.get("tradingSymbol", ""),
                    quantity=item.get("totalQty", 0),
                    average_price=item.get("avgCostPrice", 0.0),
                    current_price=item.get("lastTradedPrice", 0.0),
                ))
        return holdings

    async def place_order(self, session_token: str, instruction: TradeInstruction) -> OrderResult:
        client_id = settings.dhan_client_id
        dhan = dhanhq(client_id, session_token)
        try:
            transaction_type = (
                dhan.BUY if instruction.action in [TradeAction.BUY, TradeAction.REBALANCE]
                else dhan.SELL
            )
            # Dhan requires security_id (numeric) — see Phase 4 below
            order = dhan.place_order(
                security_id="",           # <-- FILL: see Phase 4
                exchange_segment=dhan.NSE,
                transaction_type=transaction_type,
                quantity=instruction.quantity,
                order_type=dhan.MARKET,
                product_type=dhan.CNC,    # CNC = delivery, INTRA = intraday
                price=0,
            )
            if order and order.get("orderId"):
                return OrderResult(
                    symbol=instruction.symbol,
                    action=instruction.action,
                    quantity=instruction.quantity,
                    status=OrderStatus.EXECUTED,
                    order_id=order["orderId"],
                    message="Order placed successfully"
                )
            else:
                return OrderResult(
                    symbol=instruction.symbol,
                    action=instruction.action,
                    quantity=instruction.quantity,
                    status=OrderStatus.FAILED,
                    message=f"Order rejected: {order}"
                )
        except Exception as e:
            return OrderResult(
                symbol=instruction.symbol,
                action=instruction.action,
                quantity=instruction.quantity,
                status=OrderStatus.FAILED,
                message=str(e)
            )
```

---

## PHASE 4: Symbol-to-Security-ID Mapping

### Step 7 — Understand Dhan's Security ID system

Dhan doesn't use trading symbols directly (like "RELIANCE", "INFY"). Instead, it uses **numeric security IDs**.

- [ ] Download the **Dhan instrument master file**: 
  - Visit **https://images.dhan.co/api-data/api-scrip-master.csv**
  - This CSV contains the mapping: `SEM_TRADING_SYMBOL` → `SEM_SMST_SECURITY_ID`
- [ ] You have two approaches:
  - **Option A (Simple):** Create a small JSON lookup file mapping common symbols to security IDs
  - **Option B (Better):** Load the CSV at startup and create an in-memory lookup

**Example mappings (NSE Equity):**

| Symbol | Security ID |
|---|---|
| RELIANCE | 2885 |
| TCS | 11536 |
| INFY | 1594 |
| HDFCBANK | 1333 |
| ICICIBANK | 4963 |
| ITC | 1660 |
| SBIN | 3045 |
| WIPRO | 14977 |

> You'll need to add a lookup function in `dhan.py` that converts the symbol from
> the trade instruction to the Dhan security ID before placing the order.

---

## PHASE 5: Docker Configuration

### Step 8 — Update docker-compose for real usage

- [ ] Open `docker-compose.yml`
- [ ] Add your environment variables to the backend service:
  ```yaml
  backend:
    environment:
      - DHAN_CLIENT_ID=<your_client_id>
      - DHAN_ACCESS_TOKEN=<your_access_token>
  ```
- [ ] **OR** (more secure) use a `.env` file with Docker:
  ```yaml
  backend:
    env_file:
      - ./backend/.env
  ```

### Step 9 — Build and run with Docker

- [ ] Make sure Docker Desktop is installed and running
- [ ] From the project root, run:
  ```
  docker-compose up --build
  ```
- [ ] Backend: http://localhost:8000
- [ ] Frontend: http://localhost:3000
- [ ] API Docs: http://localhost:8000/docs

---

## PHASE 6: Frontend Configuration

### Step 10 — Default to Dhan broker in the UI

No code change required — just select **Dhan** from the broker dropdown in the frontend.
But if you want to simplify:

- [ ] Optionally hardcode Dhan as the default broker in `frontend/src/App.tsx`
- [ ] When connecting, the UI will use the credentials from your `.env` — you can
      leave the API Key / Secret fields empty in the UI if the backend reads from env.

---

## PHASE 7: Testing Checklist

### Step 11 — Verify the complete flow

- [ ] **Start the app** (Docker or local)
- [ ] **Select Dhan** → Click Connect → Should say "Connected to Dhan successfully"
- [ ] **View Holdings** → Should display your real stock portfolio from Dhan
- [ ] **Test with a small order first:**
  - Use `first_time` mode
  - Pick a cheap, liquid stock (e.g., ITC, NHPC)
  - Quantity: **1 share only**
  - Execute and verify the order appears in your Dhan trading app

### Step 12 — Safety checks before using for real

- [ ] Always test during **market hours** (9:15 AM — 3:30 PM IST, Mon-Fri)
- [ ] Start with **1 share** of a low-price stock to verify end-to-end
- [ ] Check your Dhan app/web portal to confirm the order was placed
- [ ] Verify the order status matches what the engine reports
- [ ] Only scale up after successful small-order testing

---

## Quick Reference: Websites You Need to Visit

| # | URL | Purpose |
|---|---|---|
| 1 | https://dhan.co | Your Dhan trading account (login/signup) |
| 2 | https://api.dhan.co | Dhan API Developer Portal (create app, get keys) |
| 3 | https://dhanhq.co/docs | Dhan API documentation |
| 4 | https://images.dhan.co/api-data/api-scrip-master.csv | Instrument master (symbol → security ID mapping) |
| 5 | https://www.docker.com/products/docker-desktop | Docker Desktop (if not installed) |

---

## Quick Reference: Values You Need to Fill

| File | Variable | Where to Get It |
|---|---|---|
| `backend/.env` | `DHAN_CLIENT_ID` | Dhan API Portal → My Apps |
| `backend/.env` | `DHAN_ACCESS_TOKEN` | Dhan API Portal → Generate Token |
| `backend/app/brokers/dhan.py` | Security ID mapping | `api-scrip-master.csv` from Dhan |
| `docker-compose.yml` | `env_file` path or inline vars | Same as `.env` above |

---

## Summary of Changes Needed

| What | Effort | File(s) |
|---|---|---|
| Get Dhan API credentials | 10 min | `backend/.env` |
| Install `dhanhq` package | 1 min | `backend/requirements.txt` |
| Replace mock Dhan adapter | 30 min | `backend/app/brokers/dhan.py` |
| Add symbol→securityID lookup | 20 min | `backend/app/brokers/dhan.py` |
| Update docker-compose env | 2 min | `docker-compose.yml` |
| **Total estimated time** | **~1 hour** | |

---

**Once done, you'll have a fully functional trading platform that shows your real Dhan holdings and can execute real trades!**
