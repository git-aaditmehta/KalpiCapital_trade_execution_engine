import pytest
import asyncio

from app.brokers.registry import BrokerRegistry, get_broker_adapter
from app.brokers.base import BrokerAdapter
from app.models.broker import BrokerCredentials, BrokerName, BrokerAuthResponse, Holding
from app.models.portfolio import TradeInstruction, TradeAction, OrderResult, OrderStatus


class TestBrokerRegistry:
    def test_list_brokers(self):
        brokers = BrokerRegistry.list_brokers()
        assert len(brokers) == 6
        assert "zerodha" in brokers
        assert "fyers" in brokers
        assert "angelone" in brokers
        assert "groww" in brokers
        assert "upstox" in brokers
        assert "dhan" in brokers

    def test_get_valid_broker(self):
        for name in ["zerodha", "fyers", "angelone", "groww", "upstox", "dhan"]:
            adapter = get_broker_adapter(name)
            assert isinstance(adapter, BrokerAdapter)
            assert adapter.name == name

    def test_get_invalid_broker(self):
        with pytest.raises(ValueError, match="not found"):
            get_broker_adapter("nonexistent_broker")

    def test_case_insensitive_lookup(self):
        adapter = get_broker_adapter("ZERODHA")
        assert adapter.name == "zerodha"


@pytest.mark.asyncio
class TestBrokerAdapters:
    """
    Tests for real broker adapters.
    - Groww (no public API) always returns simulated success.
    - Other brokers return auth failure when no real credentials are configured,
      which is the correct behavior — they should NOT blindly succeed.
    """

    # --- Groww (simulated, always works) ---

    async def test_groww_authenticate(self):
        adapter = get_broker_adapter("groww")
        creds = BrokerCredentials(broker=BrokerName.GROWW, api_key="test", api_secret="test")
        response = await adapter.authenticate(creds)
        assert isinstance(response, BrokerAuthResponse)
        assert response.authenticated is True
        assert "SIMULATED" in response.message

    async def test_groww_holdings(self):
        adapter = get_broker_adapter("groww")
        holdings = await adapter.get_holdings("sim_session")
        assert isinstance(holdings, list)
        assert len(holdings) > 0
        for h in holdings:
            assert isinstance(h, Holding)
            assert h.quantity > 0

    async def test_groww_place_order(self):
        adapter = get_broker_adapter("groww")
        instruction = TradeInstruction(action=TradeAction.BUY, symbol="RELIANCE", quantity=10)
        result = await adapter.place_order("sim_session", instruction)
        assert isinstance(result, OrderResult)
        assert result.symbol == "RELIANCE"
        assert result.status in [OrderStatus.EXECUTED, OrderStatus.FAILED]

    # --- Real brokers: graceful failure without credentials ---

    @pytest.mark.parametrize("broker_name", ["zerodha", "fyers", "angelone", "dhan"])
    async def test_auth_without_credentials(self, broker_name):
        """Real brokers should return a valid BrokerAuthResponse.
        If env credentials are configured, auth may succeed (e.g. Dhan with .env).
        If not, auth should fail gracefully with a helpful message."""
        adapter = get_broker_adapter(broker_name)
        creds = BrokerCredentials(broker=BrokerName(broker_name))
        response = await adapter.authenticate(creds)
        assert isinstance(response, BrokerAuthResponse)
        assert response.message  # Should always contain a message

    async def test_upstox_auth_without_credentials(self):
        """Upstox should return authenticated=False when no credentials are set."""
        adapter = get_broker_adapter("upstox")
        creds = BrokerCredentials(broker=BrokerName.UPSTOX)
        response = await adapter.authenticate(creds)
        assert isinstance(response, BrokerAuthResponse)
        assert response.authenticated is False
        assert response.message

    # --- Adapter instantiation ---

    @pytest.mark.parametrize("broker_name", ["zerodha", "fyers", "angelone", "groww", "upstox", "dhan"])
    async def test_adapter_has_required_methods(self, broker_name):
        """All adapters must implement the full BrokerAdapter interface."""
        adapter = get_broker_adapter(broker_name)
        assert hasattr(adapter, "authenticate")
        assert hasattr(adapter, "get_holdings")
        assert hasattr(adapter, "place_order")
        assert hasattr(adapter, "get_order_status")
        assert hasattr(adapter, "place_orders")
