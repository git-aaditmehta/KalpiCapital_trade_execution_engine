import logging
from typing import List, Dict

from app.models.broker import Holding
from app.models.portfolio import TradeInstruction, TradeAction

logger = logging.getLogger(__name__)


class PortfolioReconciler:
    """
    Utility class to compute the delta between current holdings and a target portfolio.

    Note: Per the assignment spec, rebalancing does NOT require delta calculation
    (the payload provides explicit instructions). This class is provided as a utility
    for scenarios where automatic delta computation is desired.
    """

    @staticmethod
    def compute_delta(
        current_holdings: List[Holding],
        target_portfolio: Dict[str, int],
    ) -> List[TradeInstruction]:
        """
        Compare current holdings against a target portfolio and generate
        the minimal set of trade instructions to reach the target state.

        Args:
            current_holdings: List of current Holding objects.
            target_portfolio: Dict mapping symbol -> target quantity.

        Returns:
            List of TradeInstruction objects (BUY/SELL).
        """
        current_map: Dict[str, int] = {h.symbol: h.quantity for h in current_holdings}
        instructions: List[TradeInstruction] = []

        all_symbols = set(list(current_map.keys()) + list(target_portfolio.keys()))

        for symbol in sorted(all_symbols):
            current_qty = current_map.get(symbol, 0)
            target_qty = target_portfolio.get(symbol, 0)
            delta = target_qty - current_qty

            if delta > 0:
                instructions.append(
                    TradeInstruction(action=TradeAction.BUY, symbol=symbol, quantity=delta)
                )
                logger.info(f"Delta: BUY {delta} x {symbol}")
            elif delta < 0:
                instructions.append(
                    TradeInstruction(action=TradeAction.SELL, symbol=symbol, quantity=abs(delta))
                )
                logger.info(f"Delta: SELL {abs(delta)} x {symbol}")
            else:
                logger.debug(f"No change needed for {symbol}")

        return instructions
