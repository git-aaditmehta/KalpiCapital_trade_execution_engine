import logging
from typing import List, Optional

from app.brokers.base import BrokerAdapter
from app.brokers.registry import get_broker_adapter
from app.models.portfolio import (
    ExecutionRequest,
    ExecutionMode,
    ExecutionSummary,
    OrderResult,
    OrderStatus,
    TradeAction,
    TradeInstruction,
)

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Core execution engine that processes portfolio trade instructions.

    Supports two modes:
    - FIRST_TIME: All instructions must be BUY orders for a fresh portfolio.
    - REBALANCE: Instructions contain explicit BUY/SELL/REBALANCE actions
      as provided by the upstream system (no delta calculation needed).
    """

    def __init__(self, broker_name: str, session_token: Optional[str] = None):
        self.adapter: BrokerAdapter = get_broker_adapter(broker_name)
        self.session_token = session_token or "mock_session"
        self.broker_name = broker_name

    def _validate_first_time(self, instructions: List[TradeInstruction]) -> None:
        """Ensure all first-time instructions are BUY orders with positive quantities."""
        for inst in instructions:
            if inst.action != TradeAction.BUY:
                raise ValueError(
                    f"First-time portfolio only accepts BUY orders. "
                    f"Got {inst.action.value} for {inst.symbol}"
                )
            if inst.quantity <= 0:
                raise ValueError(
                    f"Quantity must be positive for BUY orders. "
                    f"Got {inst.quantity} for {inst.symbol}"
                )

    def _normalize_rebalance(self, instructions: List[TradeInstruction]) -> List[TradeInstruction]:
        """
        Normalize REBALANCE instructions into concrete BUY/SELL orders.
        REBALANCE with positive quantity → BUY
        REBALANCE with negative quantity → SELL (abs quantity)
        """
        normalized = []
        for inst in instructions:
            if inst.action == TradeAction.REBALANCE:
                if inst.quantity > 0:
                    normalized.append(
                        TradeInstruction(
                            action=TradeAction.BUY,
                            symbol=inst.symbol,
                            quantity=inst.quantity,
                            exchange=inst.exchange,
                            order_type=inst.order_type,
                            price=inst.price,
                        )
                    )
                elif inst.quantity < 0:
                    normalized.append(
                        TradeInstruction(
                            action=TradeAction.SELL,
                            symbol=inst.symbol,
                            quantity=abs(inst.quantity),
                            exchange=inst.exchange,
                            order_type=inst.order_type,
                            price=inst.price,
                        )
                    )
                else:
                    logger.warning(f"Skipping REBALANCE with zero quantity for {inst.symbol}")
            else:
                normalized.append(inst)
        return normalized

    async def execute(self, request: ExecutionRequest) -> ExecutionSummary:
        """
        Execute the full set of trade instructions.

        1. Validate instructions based on mode.
        2. Normalize REBALANCE instructions into BUY/SELL.
        3. Place orders sequentially via the broker adapter.
        4. Collect results and build summary.
        """
        logger.info(
            f"Starting execution: broker={request.broker}, mode={request.mode.value}, "
            f"orders={len(request.instructions)}"
        )

        instructions = request.instructions

        # Validation
        if request.mode == ExecutionMode.FIRST_TIME:
            self._validate_first_time(instructions)

        # Normalize REBALANCE actions into BUY/SELL
        normalized = self._normalize_rebalance(instructions)

        if not normalized:
            return ExecutionSummary(
                broker=request.broker,
                mode=request.mode,
                total_orders=0,
                successful=0,
                failed=0,
                results=[],
            )

        # Execute orders
        results: List[OrderResult] = []
        for instruction in normalized:
            try:
                result = await self.adapter.place_order(self.session_token, instruction)
                results.append(result)
                logger.info(
                    f"Order {result.status.value}: {instruction.action.value} "
                    f"{instruction.quantity} x {instruction.symbol} "
                    f"(order_id={result.order_id})"
                )
            except Exception as e:
                logger.error(f"Order failed for {instruction.symbol}: {e}")
                results.append(
                    OrderResult(
                        symbol=instruction.symbol,
                        action=instruction.action,
                        quantity=instruction.quantity,
                        status=OrderStatus.FAILED,
                        message=f"Exception: {str(e)}",
                    )
                )

        successful = sum(1 for r in results if r.status == OrderStatus.EXECUTED)
        failed = sum(1 for r in results if r.status == OrderStatus.FAILED)

        summary = ExecutionSummary(
            broker=request.broker,
            mode=request.mode,
            total_orders=len(results),
            successful=successful,
            failed=failed,
            results=results,
        )

        logger.info(
            f"Execution complete: {successful}/{len(results)} orders successful, "
            f"{failed} failed"
        )

        return summary
