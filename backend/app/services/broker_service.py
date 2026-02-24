import logging
from typing import List, Dict, Any

from app.brokers.registry import get_broker_adapter
from app.models.broker import BrokerCredentials, BrokerAuthResponse, Holding
from app.models.portfolio import TradeInstruction, OrderResult, ExecutionRequest, ExecutionSummary
from app.engine.executor import TradeExecutor

logger = logging.getLogger(__name__)


class BrokerService:
    """
    Service layer for broker operations.
    Handles authentication, holdings, orders, and execution engine integration.
    """

    @staticmethod
    async def connect_zerodha() -> BrokerAuthResponse:
        """
        Initiate Zerodha OAuth flow.
        Returns login URL for user to authenticate.
        """
        logger.info("🚀 Initiating Zerodha OAuth login flow")
        try:
            adapter = get_broker_adapter("zerodha")
            response = await adapter.authenticate(BrokerCredentials(broker="zerodha"))
            
            if response.authenticated:
                logger.info("✅ Zerodha already authenticated")
            else:
                logger.info(f"🔗 Zerodha login URL generated: {response.message}")
            
            return response
        except Exception as e:
            logger.error(f"❌ Failed to initiate Zerodha login: {e}")
            raise

    @staticmethod
    async def zerodha_callback(request_token: str) -> BrokerAuthResponse:
        """
        Handle Zerodha OAuth callback.
        Exchange request_token for access_token.
        """
        logger.info(f"🔄 Received Zerodha callback with request_token: {request_token[:10]}...")
        try:
            adapter = get_broker_adapter("zerodha")
            credentials = BrokerCredentials(broker="zerodha", extra={"request_token": request_token})
            response = await adapter.authenticate(credentials)
            
            if response.authenticated:
                logger.info(f"✅ Zerodha token exchanged successfully for user: {response.user_id}")
            else:
                logger.error(f"❌ Zerodha token exchange failed: {response.message}")
            
            return response
        except Exception as e:
            logger.error(f"❌ Failed to handle Zerodha callback: {e}")
            raise

    @staticmethod
    async def get_holdings(broker_name: str, access_token: str) -> List[Holding]:
        """
        Fetch holdings for any broker.
        """
        logger.info(f"📊 Fetching holdings for {broker_name}")
        try:
            adapter = get_broker_adapter(broker_name)
            holdings = await adapter.get_holdings(access_token)
            logger.info(f"✅ Retrieved {len(holdings)} holdings for {broker_name}")
            return holdings
        except Exception as e:
            logger.error(f"❌ Failed to fetch holdings for {broker_name}: {e}")
            raise

    @staticmethod
    async def place_order(broker_name: str, access_token: str, instruction: TradeInstruction) -> OrderResult:
        """
        Place a single order for any broker.
        """
        logger.info(f"📈 Placing {instruction.action} order for {instruction.symbol} on {broker_name}")
        try:
            adapter = get_broker_adapter(broker_name)
            result = await adapter.place_order(access_token, instruction)
            
            if result.status.value == "EXECUTED":
                logger.info(f"✅ Order placed successfully: {result.order_id}")
            else:
                logger.error(f"❌ Order failed: {result.message}")
            
            return result
        except Exception as e:
            logger.error(f"❌ Failed to place order for {broker_name}: {e}")
            raise

    @staticmethod
    async def execute_trades(broker_name: str, access_token: str, trades: List[TradeInstruction]) -> ExecutionSummary:
        """
        Execute multiple trades using the execution engine.
        """
        logger.info(f"🚀 Executing {len(trades)} trades for {broker_name}")
        try:
            # Create execution request
            execution_request = ExecutionRequest(
                broker=broker_name,
                mode="rebalance",  # Default to rebalance mode
                instructions=trades,
                session_token=access_token
            )
            
            # Use execution engine
            executor = TradeExecutor(broker_name, access_token)
            summary = await executor.execute(execution_request)
            
            logger.info(f"📊 Execution complete: {summary.successful}/{summary.total_orders} successful")
            return summary
        except Exception as e:
            logger.error(f"❌ Failed to execute trades for {broker_name}: {e}")
            raise

    @staticmethod
    async def get_order_status(broker_name: str, access_token: str, order_id: str) -> OrderResult:
        """
        Get order status for any broker.
        """
        logger.info(f"🔍 Checking order status for {order_id} on {broker_name}")
        try:
            adapter = get_broker_adapter(broker_name)
            result = await adapter.get_order_status(access_token, order_id)
            logger.info(f"📊 Order {order_id} status: {result.status.value}")
            return result
        except Exception as e:
            logger.error(f"❌ Failed to get order status for {broker_name}: {e}")
            raise

    @staticmethod
    def list_supported_brokers() -> List[str]:
        """
        Get list of all supported brokers.
        """
        from app.brokers.registry import BrokerRegistry
        return BrokerRegistry.list_brokers()


# Singleton instance
broker_service = BrokerService()
