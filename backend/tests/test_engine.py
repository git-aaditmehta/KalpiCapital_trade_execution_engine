import pytest

from app.engine.executor import TradeExecutor
from app.engine.reconciler import PortfolioReconciler
from app.models.portfolio import (
    ExecutionRequest,
    ExecutionMode,
    ExecutionSummary,
    TradeInstruction,
    TradeAction,
    OrderStatus,
)
from app.models.broker import Holding


class TestPortfolioReconciler:
    def test_first_time_portfolio(self):
        """No current holdings — should generate all BUY instructions."""
        target = {"RELIANCE": 10, "TCS": 5, "INFY": 15}
        instructions = PortfolioReconciler.compute_delta([], target)

        assert len(instructions) == 3
        for inst in instructions:
            assert inst.action == TradeAction.BUY
            assert inst.quantity > 0

    def test_full_exit(self):
        """Target is empty — should generate all SELL instructions."""
        current = [
            Holding(symbol="RELIANCE", quantity=10, average_price=2450.0),
            Holding(symbol="TCS", quantity=5, average_price=3400.0),
        ]
        instructions = PortfolioReconciler.compute_delta(current, {})

        assert len(instructions) == 2
        for inst in instructions:
            assert inst.action == TradeAction.SELL

    def test_rebalance_delta(self):
        """Mixed changes: increase, decrease, new stock, exit stock."""
        current = [
            Holding(symbol="RELIANCE", quantity=10, average_price=2450.0),
            Holding(symbol="TCS", quantity=5, average_price=3400.0),
            Holding(symbol="INFY", quantity=15, average_price=1450.0),
        ]
        target = {"RELIANCE": 15, "TCS": 5, "HDFCBANK": 20}
        # RELIANCE: +5 BUY, TCS: no change, INFY: -15 SELL, HDFCBANK: +20 BUY

        instructions = PortfolioReconciler.compute_delta(current, target)

        symbols = {inst.symbol: inst for inst in instructions}
        assert "TCS" not in symbols  # no change
        assert symbols["RELIANCE"].action == TradeAction.BUY
        assert symbols["RELIANCE"].quantity == 5
        assert symbols["INFY"].action == TradeAction.SELL
        assert symbols["INFY"].quantity == 15
        assert symbols["HDFCBANK"].action == TradeAction.BUY
        assert symbols["HDFCBANK"].quantity == 20

    def test_no_changes(self):
        """Current matches target — should return empty list."""
        current = [Holding(symbol="RELIANCE", quantity=10, average_price=2450.0)]
        target = {"RELIANCE": 10}
        instructions = PortfolioReconciler.compute_delta(current, target)
        assert len(instructions) == 0


@pytest.mark.asyncio
class TestTradeExecutor:
    """
    Engine logic tests use 'groww' broker (simulated, no credentials needed).
    The execution engine logic is broker-agnostic — it validates instructions,
    normalizes REBALANCE actions, and delegates to the adapter.
    """

    async def test_first_time_execution(self):
        executor = TradeExecutor(broker_name="groww")
        request = ExecutionRequest(
            broker="groww",
            mode=ExecutionMode.FIRST_TIME,
            instructions=[
                TradeInstruction(action=TradeAction.BUY, symbol="RELIANCE", quantity=10),
                TradeInstruction(action=TradeAction.BUY, symbol="TCS", quantity=5),
            ],
        )
        summary = await executor.execute(request)

        assert isinstance(summary, ExecutionSummary)
        assert summary.broker == "groww"
        assert summary.mode == ExecutionMode.FIRST_TIME
        assert summary.total_orders == 2
        assert summary.successful + summary.failed == 2

    async def test_first_time_rejects_sell(self):
        executor = TradeExecutor(broker_name="groww")
        request = ExecutionRequest(
            broker="groww",
            mode=ExecutionMode.FIRST_TIME,
            instructions=[
                TradeInstruction(action=TradeAction.SELL, symbol="RELIANCE", quantity=10),
            ],
        )
        with pytest.raises(ValueError, match="First-time portfolio only accepts BUY"):
            await executor.execute(request)

    async def test_rebalance_execution(self):
        executor = TradeExecutor(broker_name="groww")
        request = ExecutionRequest(
            broker="groww",
            mode=ExecutionMode.REBALANCE,
            instructions=[
                TradeInstruction(action=TradeAction.SELL, symbol="INFY", quantity=3),
                TradeInstruction(action=TradeAction.BUY, symbol="HDFCBANK", quantity=7),
                TradeInstruction(action=TradeAction.REBALANCE, symbol="RELIANCE", quantity=-2),
            ],
        )
        summary = await executor.execute(request)

        assert summary.total_orders == 3
        # REBALANCE with -2 should become SELL
        actions = [r.action for r in summary.results]
        assert TradeAction.SELL in actions
        assert TradeAction.BUY in actions

    async def test_rebalance_skips_zero_quantity(self):
        executor = TradeExecutor(broker_name="groww")
        request = ExecutionRequest(
            broker="groww",
            mode=ExecutionMode.REBALANCE,
            instructions=[
                TradeInstruction(action=TradeAction.REBALANCE, symbol="RELIANCE", quantity=0),
                TradeInstruction(action=TradeAction.BUY, symbol="TCS", quantity=5),
            ],
        )
        summary = await executor.execute(request)
        # Zero-quantity REBALANCE should be skipped
        assert summary.total_orders == 1

    async def test_groww_simulated_execute(self):
        """Verify execution works for Groww (simulated broker)."""
        executor = TradeExecutor(broker_name="groww")
        request = ExecutionRequest(
            broker="groww",
            mode=ExecutionMode.FIRST_TIME,
            instructions=[
                TradeInstruction(action=TradeAction.BUY, symbol="RELIANCE", quantity=1),
            ],
        )
        summary = await executor.execute(request)
        assert summary.total_orders == 1
        assert summary.successful + summary.failed == 1
