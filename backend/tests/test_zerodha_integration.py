import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from app.services.broker_service import broker_service
from app.models.broker import BrokerAuthResponse
from app.models.portfolio import TradeInstruction, TradeAction


class TestZerodhaIntegration:
    """Test suite for complete Zerodha integration."""

    @pytest.fixture
    def mock_kite_connect(self):
        """Mock KiteConnect SDK."""
        with patch('app.brokers.zerodha.KiteConnect') as mock_kite:
            mock_instance = Mock()
            mock_kite.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_zerodha_login_flow(self, mock_kite_connect):
        """Test Zerodha OAuth login flow."""
        # Mock login URL generation
        mock_kite_connect.login_url.return_value = "https://kite.zerodha.com/connect/login?api_key=TEST&v=3"
        
        response = await broker_service.connect_zerodha()
        
        assert response.broker == "zerodha"
        assert response.authenticated is False
        assert response.login_url is not None
        assert "Please login via Kite" in response.message

    @pytest.mark.asyncio
    async def test_zerodha_callback_success(self, mock_kite_connect):
        """Test successful Zerodha OAuth callback."""
        # Mock token exchange
        mock_kite_connect.generate_session.return_value = {
            "access_token": "test_access_token",
            "user_id": "TESTUSER",
            "user_name": "Test User"
        }
        
        response = await broker_service.zerodha_callback("test_request_token")
        
        assert response.broker == "zerodha"
        assert response.authenticated is True
        assert response.session_token == "test_access_token"
        assert response.user_id == "TESTUSER"
        assert "Connected to Zerodha" in response.message

    @pytest.mark.asyncio
    async def test_zerodha_callback_failure(self, mock_kite_connect):
        """Test failed Zerodha OAuth callback."""
        # Mock token exchange failure
        mock_kite_connect.generate_session.side_effect = Exception("Invalid request token")
        
        with pytest.raises(Exception):
            await broker_service.zerodha_callback("invalid_request_token")

    @pytest.mark.asyncio
    async def test_get_holdings(self, mock_kite_connect):
        """Test fetching holdings."""
        # Mock holdings response
        mock_holdings = [
            {
                "tradingsymbol": "RELIANCE",
                "quantity": 10,
                "average_price": 2500.0,
                "last_price": 2600.0,
                "pnl": 1000.0,
                "exchange": "NSE"
            },
            {
                "tradingsymbol": "TCS",
                "quantity": 5,
                "average_price": 3500.0,
                "last_price": 3600.0,
                "pnl": 500.0,
                "exchange": "NSE"
            }
        ]
        mock_kite_connect.holdings.return_value = mock_holdings
        
        holdings = await broker_service.get_holdings("zerodha", "test_access_token")
        
        assert len(holdings) == 2
        assert holdings[0].symbol == "RELIANCE"
        assert holdings[0].quantity == 10
        assert holdings[1].symbol == "TCS"
        assert holdings[1].quantity == 5

    @pytest.mark.asyncio
    async def test_place_order_success(self, mock_kite_connect):
        """Test successful order placement."""
        # Mock order placement
        mock_kite_connect.place_order.return_value = "1234567890"
        
        instruction = TradeInstruction(
            action=TradeAction.BUY,
            symbol="RELIANCE",
            quantity=10,
            exchange="NSE",
            order_type="MARKET"
        )
        
        result = await broker_service.place_order("zerodha", "test_access_token", instruction)
        
        assert result.symbol == "RELIANCE"
        assert result.action == TradeAction.BUY
        assert result.quantity == 10
        assert result.status.value == "EXECUTED"
        assert result.order_id == "1234567890"

    @pytest.mark.asyncio
    async def test_place_order_failure(self, mock_kite_connect):
        """Test failed order placement."""
        # Mock order placement failure
        mock_kite_connect.place_order.side_effect = Exception("Insufficient funds")
        
        instruction = TradeInstruction(
            action=TradeAction.BUY,
            symbol="RELIANCE",
            quantity=10,
            exchange="NSE",
            order_type="MARKET"
        )
        
        result = await broker_service.place_order("zerodha", "test_access_token", instruction)
        
        assert result.symbol == "RELIANCE"
        assert result.action == TradeAction.BUY
        assert result.quantity == 10
        assert result.status.value == "FAILED"
        assert "Insufficient funds" in result.message

    @pytest.mark.asyncio
    async def test_execute_trades(self, mock_kite_connect):
        """Test executing multiple trades."""
        # Mock order placement
        mock_kite_connect.place_order.return_value = "1234567890"
        
        trades = [
            TradeInstruction(
                action=TradeAction.BUY,
                symbol="RELIANCE",
                quantity=10,
                exchange="NSE",
                order_type="MARKET"
            ),
            TradeInstruction(
                action=TradeAction.SELL,
                symbol="TCS",
                quantity=5,
                exchange="NSE",
                order_type="MARKET"
            )
        ]
        
        summary = await broker_service.execute_trades("zerodha", "test_access_token", trades)
        
        assert summary.broker == "zerodha"
        assert summary.total_orders == 2
        assert summary.successful == 2
        assert summary.failed == 0
        assert len(summary.results) == 2

    def test_list_supported_brokers(self):
        """Test listing supported brokers."""
        brokers = broker_service.list_supported_brokers()
        
        assert "zerodha" in brokers
        assert "dhan" in brokers
        assert isinstance(brokers, list)

    @pytest.mark.asyncio
    async def test_get_order_status(self, mock_kite_connect):
        """Test getting order status."""
        # Mock order history
        mock_order_history = [
            {
                "tradingsymbol": "RELIANCE",
                "status": "COMPLETE",
                "transaction_type": "BUY",
                "quantity": 10,
                "average_price": 2600.0,
                "status_message": "Order executed successfully"
            }
        ]
        mock_kite_connect.order_history.return_value = mock_order_history
        
        result = await broker_service.get_order_status("zerodha", "test_access_token", "1234567890")
        
        assert result.symbol == "RELIANCE"
        assert result.action == TradeAction.BUY
        assert result.quantity == 10
        assert result.status.value == "EXECUTED"
        assert result.order_id == "1234567890"
        assert result.executed_price == 2600.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
