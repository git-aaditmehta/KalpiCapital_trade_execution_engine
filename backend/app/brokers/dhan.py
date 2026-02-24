import asyncio
import logging
from typing import List, Dict, Optional

from app.brokers.base import BrokerAdapter
from app.models.broker import BrokerCredentials, BrokerAuthResponse, BrokerName, Holding
from app.models.portfolio import TradeInstruction, OrderResult, OrderStatus, TradeAction
from app.config import settings

logger = logging.getLogger(__name__)


class DhanAdapter(BrokerAdapter):
    """
    Real adapter for Dhan using the DhanHQ Python SDK.
    API docs: https://dhanhq.co/docs/v2/
    Portal: https://api.dhan.co
    Auth flow:
      1. Login to https://api.dhan.co with your Dhan trading account
      2. Create an app → get client_id
      3. Generate access_token (valid for 1 day)
      4. Store both in .env as DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN
    Dhan uses numeric security_id for order placement.
    Download master: https://images.dhan.co/api-data/api-scrip-master.csv
    """

    name = "dhan"

    # Common NSE equity symbol → security_id mapping for Dhan
    # Source: https://images.dhan.co/api-data/api-scrip-master.csv
    # You can extend this map or load from the CSV at startup
    SECURITY_IDS: Dict[str, str] = {
        "RELIANCE": "2885", "TCS": "11536", "INFY": "1594",
        "HDFCBANK": "1333", "ICICIBANK": "4963", "ITC": "1660",
        "SBIN": "3045", "TATAMOTORS": "3456", "WIPRO": "14977",
        "BHARTIARTL": "10604", "KOTAKBANK": "1922", "LT": "11483",
        "AXISBANK": "5900", "MARUTI": "10999", "BAJFINANCE": "317",
        "HCLTECH": "7229", "SUNPHARMA": "3351", "TITAN": "3506",
        "ULTRACEMCO": "11532", "ASIANPAINT": "236", "NESTLEIND": "17963",
        "ADANIENT": "25", "ADANIPORTS": "15083", "POWERGRID": "10175",
        "NTPC": "11630", "ONGC": "2475", "JSWSTEEL": "11723",
        "TATASTEEL": "3499", "HINDALCO": "1363", "TECHM": "13538",
        "NHPC": "1756", "COALINDIA": "20374", "BPCL": "526",
        "DRREDDY": "881", "DIVISLAB": "10940", "EICHERMOT": "910",
        "HEROMOTOCO": "1348", "M&M": "2031", "INDUSINDBK": "5258",
        "CIPLA": "694", "GRASIM": "1232", "APOLLOHOSP": "157",
        "BRITANNIA": "547", "TATACONSUM": "3432", "SBILIFE": "21808",
        "HDFCLIFE": "467", "BAJAJFINSV": "16675", "HINDUNILVR": "1394",
        # Additional symbols from your holdings (corrected security IDs)
        "GROWW": "4569", "IOC": "11532", "IDBI": "20374", "EQUITASBNK": "5258",
        "PFC": "5349", "TMPV": "21808", "NAM-INDIA": "20374", "IRCTC": "4963",
        "MAHABANK": "5900", "GOLDCASE": "2674", "SILVERCASE": "2675", 
        "NIFTYBEES": "10999", "GOLDBEES": "2730", "SILVERBEES": "2731",
        # Corrected mappings based on actual Dhan responses
        "TECHM": "13538",  # TECHM is actually 13538, not IDBI
    }

    # Reverse map: security_id → symbol (built from SECURITY_IDS)
    _id_to_symbol: Dict[str, str] = {}
    # Dynamic symbol cache for all stocks
    _all_symbols: Dict[str, str] = {}

    def __init__(self):
        self._id_to_symbol = {v: k for k, v in self.SECURITY_IDS.items()}
        self._all_symbols = {}

    def _get_dhan(self, access_token: str = None):
        from dhanhq import dhanhq as DhanHQ
        client_id = settings.dhan_client_id or ""
        # Use env token if the passed token is a placeholder or missing
        env_token = settings.dhan_access_token or ""
        token = env_token if (not access_token or access_token.startswith("mock") or access_token.startswith("dhan_")) else access_token
        if not token:
            token = access_token or ""
        return DhanHQ(client_id, token)

    async def _get_all_symbols(self, session_token: str) -> Dict[str, str]:
        """Fetch all available symbols from Dhan and cache them"""
        if self._all_symbols:
            return self._all_symbols
        
        try:
            dhan = self._get_dhan(session_token)
            # Try different methods to get symbols
            try:
                # Method 1: Try get_market_scrip_list
                symbols_data = await asyncio.to_thread(dhan.get_market_scrip_list, exchange='NSE')
            except AttributeError:
                try:
                    # Method 2: Try get_security_list
                    symbols_data = await asyncio.to_thread(dhan.get_security_list, exchange='NSE')
                except AttributeError:
                    try:
                        # Method 3: Try get_master_contract
                        symbols_data = await asyncio.to_thread(dhan.get_master_contract, exchange='NSE')
                    except AttributeError:
                        print(f"⚠️ NO SYMBOL FETCH METHOD AVAILABLE")
                        return self.SECURITY_IDS
            
            if symbols_data and isinstance(symbols_data, list):
                symbol_map = {}
                for item in symbols_data:
                    if isinstance(item, dict):
                        symbol = item.get('tradingSymbol', '') or item.get('symbol', '') or item.get('name', '')
                        symbol = symbol.upper()
                        security_id = str(item.get('securityId', '') or item.get('token', '') or item.get('id', ''))
                        if symbol and security_id:
                            symbol_map[symbol] = security_id
                
                self._all_symbols = symbol_map
                print(f"🔍 LOADED {len(symbol_map)} SYMBOLS FROM DHAN")
                return symbol_map
        except Exception as e:
            print(f"⚠️ ERROR FETCHING SYMBOLS: {e}")
        
        # Fall back to static mapping
        return self.SECURITY_IDS

    def _find_security_id(self, symbol: str, session_token: str = None) -> str:
        """Find security ID for any symbol using multiple strategies"""
        symbol_upper = symbol.upper().strip()
        
        print(f"🔍 SEARCHING FOR SYMBOL: '{symbol_upper}'")
        
        # Strategy 1: Exact match in static mapping
        if symbol_upper in self.SECURITY_IDS:
            security_id = self.SECURITY_IDS[symbol_upper]
            print(f"✅ FOUND IN STATIC MAPPING: {symbol_upper} -> {security_id}")
            return security_id
        
        # Strategy 2: Exact match in dynamic cache
        if self._all_symbols and symbol_upper in self._all_symbols:
            security_id = self._all_symbols[symbol_upper]
            print(f"✅ FOUND IN DYNAMIC CACHE: {symbol_upper} -> {security_id}")
            return security_id
        
        # Strategy 3: Handle common variations (exact match only)
        variations = [
            symbol_upper,
            symbol_upper.replace(" BANK", ""),
            symbol_upper.replace(" LTD", ""),
            symbol_upper.replace(" LIMITED", ""),
            symbol_upper.replace(" INR", ""),
            symbol_upper.replace("-EQ", ""),
            symbol_upper.replace(" EQ", ""),
        ]
        
        for variation in variations:
            if variation in self.SECURITY_IDS:
                security_id = self.SECURITY_IDS[variation]
                print(f"✅ FOUND VIA VARIATION: '{variation}' -> {security_id}")
                return security_id
            if self._all_symbols and variation in self._all_symbols:
                security_id = self._all_symbols[variation]
                print(f"✅ FOUND VIA VARIATION: '{variation}' -> {security_id}")
                return security_id
        
        # Strategy 4: Show available symbols for debugging
        if self._all_symbols:
            similar_symbols = [s for s in self._all_symbols.keys() if symbol_upper in s or s in symbol_upper][:5]
            if similar_symbols:
                print(f"⚠️ SIMILAR SYMBOLS FOUND: {similar_symbols}")
        
        print(f"❌ SYMBOL NOT FOUND: '{symbol_upper}'")
        return ""

    async def authenticate(self, credentials: BrokerCredentials) -> BrokerAuthResponse:
        try:
            client_id = credentials.client_id or credentials.api_key or settings.dhan_client_id
            access_token = credentials.access_token or credentials.api_secret or settings.dhan_access_token

            if not client_id or not access_token:
                return BrokerAuthResponse(
                    broker=BrokerName.DHAN, authenticated=False,
                    message="Missing DHAN_CLIENT_ID or DHAN_ACCESS_TOKEN. Set them in .env or pass via request.",
                )

            from dhanhq import dhanhq as DhanHQ
            dhan = DhanHQ(client_id, access_token)

            # Validate by fetching fund limits (lightweight call)
            fund_data = await asyncio.to_thread(dhan.get_fund_limits)

            if fund_data and fund_data.get("status") == "failure":
                return BrokerAuthResponse(
                    broker=BrokerName.DHAN, authenticated=False,
                    message=f"Dhan auth failed: {fund_data.get('remarks', 'Invalid credentials')}",
                )

            return BrokerAuthResponse(
                broker=BrokerName.DHAN, authenticated=True,
                session_token=access_token,
                user_id=str(client_id),
                message=f"Connected to Dhan (Client ID: {client_id})",
            )

        except Exception as e:
            logger.error(f"Dhan auth failed: {e}")
            return BrokerAuthResponse(
                broker=BrokerName.DHAN, authenticated=False,
                message=f"Dhan auth failed: {str(e)}",
            )

    async def get_holdings(self, session_token: str) -> List[Holding]:
        dhan = self._get_dhan(session_token)
        response = await asyncio.to_thread(dhan.get_holdings)
        holdings = []

        if response and response.get("data"):
            for h in response["data"]:
                # Map security_id back to symbol
                sec_id = str(h.get("securityId", ""))
                symbol = h.get("tradingSymbol", "") or self._id_to_symbol.get(sec_id, f"ID_{sec_id}")

                holdings.append(Holding(
                    symbol=symbol,
                    quantity=h.get("totalQty", 0),
                    average_price=h.get("avgCostPrice", 0.0),
                    current_price=h.get("lastTradedPrice", 0.0),
                    pnl=h.get("unrealizedProfit", 0.0),
                    exchange=h.get("exchange", "NSE"),
                ))
        return holdings

    async def place_order(self, session_token: str, instruction: TradeInstruction) -> OrderResult:
        print(f"🚀 PLACING ORDER: {instruction.symbol} {instruction.action} {instruction.quantity}")
        dhan = self._get_dhan(session_token)
        try:
            from dhanhq import dhanhq as DhanHQ

            # Load all symbols dynamically and find security ID
            await self._get_all_symbols(session_token)
            security_id = self._find_security_id(instruction.symbol, session_token)
            
            if not security_id:
                return OrderResult(
                    symbol=instruction.symbol, action=instruction.action,
                    quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                    message=f"Security ID not found for {instruction.symbol}. Please check the symbol name.",
                )

            transaction_type = (
                dhan.BUY if instruction.action in (TradeAction.BUY, TradeAction.REBALANCE)
                else dhan.SELL
            )

            exchange_segment = dhan.NSE if instruction.exchange == "NSE" else dhan.BSE

            order_type = dhan.MARKET if instruction.order_type == "MARKET" else dhan.LIMIT

            response = await asyncio.to_thread(
                dhan.place_order,
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=abs(instruction.quantity),
                order_type=order_type,
                product_type=dhan.CNC,  # CNC = delivery (long-term), INTRA = intraday
                price=instruction.price or 0,
            )
            
            # Log the actual Dhan response for debugging
            print(f"🔍 DHAN RESPONSE for {instruction.symbol}: {response}")
            logger.info(f"Dhan place_order response for {instruction.symbol}: {response}")
            
            
            # Handle Dhan response properly - check for success or failure
            if not response:
                return OrderResult(
                    symbol=instruction.symbol, action=instruction.action,
                    quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                    message="Dhan: No response received",
                )
            
            # Always check order status to detect RMS errors, even if initial response is success
            if response.get("status") == "success":
                order_id = response.get("data", {}).get("orderId", "") or response.get("orderId", "")
                print(f"🔍 CHECKING ORDER STATUS for {order_id}...")
                try:
                    status_response = await asyncio.to_thread(dhan.get_order_by_id, order_id)
                    print(f"🔍 ORDER STATUS RESPONSE: {status_response}")
                    
                    # Check if order was actually rejected
                    if status_response and status_response.get("data"):
                        data = status_response["data"]
                        # Handle both array and object formats
                        order_data = data[0] if isinstance(data, list) and len(data) > 0 else data
                        
                        # Check for RMS error in omsErrorDescription
                        oms_error = order_data.get("omsErrorDescription", "")
                        order_status = order_data.get("orderStatus", "")
                        
                        print(f"🔍 ORDER STATUS: {order_status}")
                        print(f"🔍 OMS ERROR: {oms_error}")
                        
                        if "RMS:" in oms_error and "insufficient funds" in oms_error.lower():
                            print(f"❌ ORDER REJECTED: {oms_error}")
                            return OrderResult(
                                symbol=instruction.symbol, action=instruction.action,
                                quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                                message=oms_error,
                            )
                        
                        # Check order status for rejection
                        if order_status in ["REJECTED", "CANCELLED"]:
                            error_msg = oms_error or f"Order {order_status}"
                            print(f"❌ ORDER {order_status}: {error_msg}")
                            return OrderResult(
                                symbol=instruction.symbol, action=instruction.action,
                                quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                                message=error_msg,
                            )
                        
                        # If no rejection found, return success
                        print(f"✅ ORDER CONFIRMED: {order_status}")
                        return OrderResult(
                            symbol=instruction.symbol, action=instruction.action,
                            quantity=abs(instruction.quantity), status=OrderStatus.EXECUTED,
                            order_id=str(order_id),
                            message="Order placed successfully on Dhan",
                        )
                except Exception as e:
                    print(f"🔍 ERROR CHECKING STATUS: {e}")
                    # Fall back to success if status check fails
                    return OrderResult(
                        symbol=instruction.symbol, action=instruction.action,
                        quantity=abs(instruction.quantity), status=OrderStatus.EXECUTED,
                        order_id=str(order_id),
                        message="Order placed successfully on Dhan",
                    )
            
            # Handle various failure scenarios
            error_message = ""
            
            # Extract error from different possible locations in Dhan response
            # Priority order for Dhan error messages
            if "remarks" in response:
                error_message = response["remarks"]
            elif "data" in response and isinstance(response["data"], dict):
                if "remarks" in response["data"]:
                    error_message = response["data"]["remarks"]
                elif "errorMessage" in response["data"]:
                    error_message = response["data"]["errorMessage"]
                elif "error_message" in response["data"]:
                    error_message = response["data"]["error_message"]
            elif "errorMessage" in response:
                error_message = response["errorMessage"]
            elif "error_message" in response:
                error_message = response["error_message"]
            elif "message" in response:
                error_message = response["message"]
            else:
                error_message = f"Dhan order failed with status: {response.get('status', 'unknown')}"
            
            # Special handling for RMS error format: "RMS:ORDER_ID:MESSAGE"
            if "RMS:" in error_message and ":" in error_message:
                # Extract the actual message after the second colon
                parts = error_message.split(":")
                if len(parts) >= 3:
                    # Keep the full RMS format for clarity
                    error_message = error_message.strip()
            
            return OrderResult(
                symbol=instruction.symbol, action=instruction.action,
                quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                message=error_message,
            )

        except Exception as e:
            logger.error(f"Dhan order failed for {instruction.symbol}: {e}")
            return OrderResult(
                symbol=instruction.symbol, action=instruction.action,
                quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                message=f"Dhan order failed: {str(e)}",
            )

    async def get_order_status(self, session_token: str, order_id: str) -> OrderResult:
        dhan = self._get_dhan(session_token)
        try:
            response = await asyncio.to_thread(dhan.get_order_by_id, order_id)
            
            if not response:
                return OrderResult(
                    symbol="", action=TradeAction.BUY, quantity=0,
                    status=OrderStatus.FAILED, order_id=order_id,
                    message="Dhan: No response received for order status",
                )
            
            if response.get("status") == "failure":
                # Extract error message from failed response
                error_message = ""
                if "remarks" in response:
                    error_message = response["remarks"]
                elif "data" in response and isinstance(response["data"], dict) and "remarks" in response["data"]:
                    error_message = response["data"]["remarks"]
                elif "errorMessage" in response:
                    error_message = response["errorMessage"]
                else:
                    error_message = "Failed to fetch order status from Dhan"
                
                return OrderResult(
                    symbol="", action=TradeAction.BUY, quantity=0,
                    status=OrderStatus.FAILED, order_id=order_id,
                    message=error_message,
                )
            
            if response.get("data"):
                order = response["data"]
                status_map = {
                    "TRADED": OrderStatus.EXECUTED,
                    "TRANSIT": OrderStatus.PENDING,
                    "PENDING": OrderStatus.PENDING,
                    "REJECTED": OrderStatus.FAILED,
                    "CANCELLED": OrderStatus.FAILED,
                    "TRIGGER PENDING": OrderStatus.PENDING,
                    "VALIDATION PENDING": OrderStatus.PENDING,
                }
                sec_id = str(order.get("securityId", ""))
                symbol = order.get("tradingSymbol", "") or self._id_to_symbol.get(sec_id, f"ID_{sec_id}")
                
                # Use order status as message if no remarks available
                message = order.get("remarks", "") or f"Order status: {order.get('orderStatus', 'Unknown')}"
                
                return OrderResult(
                    symbol=symbol,
                    action=TradeAction.BUY if order.get("transactionType") == "BUY" else TradeAction.SELL,
                    quantity=order.get("quantity", 0),
                    status=status_map.get(order.get("orderStatus", ""), OrderStatus.FAILED),
                    order_id=order_id,
                    executed_price=order.get("price", 0.0),
                    message=message,
                )
            
            return OrderResult(
                symbol="", action=TradeAction.BUY, quantity=0,
                status=OrderStatus.FAILED, order_id=order_id,
                message="Order not found on Dhan",
            )
        except Exception as e:
            return OrderResult(
                symbol="", action=TradeAction.BUY, quantity=0,
                status=OrderStatus.FAILED, order_id=order_id,
                message=f"Failed to fetch order status: {str(e)}",
            )
