import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "Kalpi Capital" in data["service"]

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthEndpoints:
    def test_list_brokers(self):
        response = client.get("/auth/brokers")
        assert response.status_code == 200
        brokers = response.json()
        assert len(brokers) == 6
        assert "zerodha" in brokers
        assert "dhan" in brokers

    def test_connect_groww(self):
        """Groww (simulated) always authenticates successfully."""
        response = client.post(
            "/auth/connect",
            json={"broker": "groww", "api_key": "test_key", "api_secret": "test_secret"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["session_token"] is not None

    def test_connect_real_broker_without_creds(self):
        """Real brokers should fail gracefully without credentials."""
        response = client.post(
            "/auth/connect",
            json={"broker": "zerodha"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["message"]  # Contains helpful error

    def test_connect_invalid_broker(self):
        response = client.post(
            "/auth/connect",
            json={"broker": "invalid_broker"},
        )
        assert response.status_code == 422  # Pydantic validation error


class TestPortfolioEndpoints:
    """
    Portfolio tests use 'groww' (simulated) since it doesn't need real credentials.
    """

    def test_get_holdings_groww(self):
        response = client.get("/portfolio/holdings?broker=groww")
        assert response.status_code == 200
        holdings = response.json()
        assert isinstance(holdings, list)
        assert len(holdings) > 0
        assert "symbol" in holdings[0]
        assert "quantity" in holdings[0]

    def test_get_holdings_invalid_broker(self):
        response = client.get("/portfolio/holdings?broker=nonexistent")
        assert response.status_code == 400

    def test_execute_first_time(self):
        response = client.post(
            "/portfolio/execute",
            json={
                "broker": "groww",
                "mode": "first_time",
                "instructions": [
                    {"action": "BUY", "symbol": "RELIANCE", "quantity": 10},
                    {"action": "BUY", "symbol": "TCS", "quantity": 5},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["broker"] == "groww"
        assert data["mode"] == "first_time"
        assert data["total_orders"] == 2
        assert len(data["results"]) == 2

    def test_execute_rebalance(self):
        response = client.post(
            "/portfolio/execute",
            json={
                "broker": "groww",
                "mode": "rebalance",
                "instructions": [
                    {"action": "SELL", "symbol": "INFY", "quantity": 3},
                    {"action": "BUY", "symbol": "HDFCBANK", "quantity": 7},
                    {"action": "REBALANCE", "symbol": "RELIANCE", "quantity": -2},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "rebalance"
        assert data["total_orders"] == 3

    def test_execute_first_time_rejects_sell(self):
        response = client.post(
            "/portfolio/execute",
            json={
                "broker": "groww",
                "mode": "first_time",
                "instructions": [
                    {"action": "SELL", "symbol": "RELIANCE", "quantity": 10},
                ],
            },
        )
        assert response.status_code == 422

    def test_execute_empty_instructions(self):
        response = client.post(
            "/portfolio/execute",
            json={
                "broker": "groww",
                "mode": "first_time",
                "instructions": [],
            },
        )
        assert response.status_code == 422  # min_length=1

    def test_execute_groww_simulated(self):
        """Verify Groww simulated execution works end-to-end via API."""
        response = client.post(
            "/portfolio/execute",
            json={
                "broker": "groww",
                "mode": "first_time",
                "instructions": [
                    {"action": "BUY", "symbol": "RELIANCE", "quantity": 1},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_orders"] == 1


class TestWebhookMock:
    def test_mock_webhook_receiver(self):
        response = client.post(
            "/webhook/mock",
            json={"event": "test", "data": "hello"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "received"
