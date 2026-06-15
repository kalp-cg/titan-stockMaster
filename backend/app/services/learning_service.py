"""Self-learning feedback loop service.

Monitors old forecasts, compares expected outcomes against actual price movements,
and calculates precision analytics.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.interfaces.market_data import IMarketDataProvider
from app.domain.interfaces.repository import IPredictionRepository
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class LearningService:
    """Evaluates prediction accuracy once horizons elapse."""

    def __init__(
        self,
        prediction_repo: IPredictionRepository,
        market_provider: IMarketDataProvider,
    ) -> None:
        self._prediction_repo = prediction_repo
        self._market_provider = market_provider

    @timed
    async def evaluate_past_predictions(self) -> None:
        logger.info("Starting prediction evaluation cycle")
        preds = await self._prediction_repo.get_unevaluated()
        evaluated_count = 0
        now = datetime.utcnow()

        for pred in preds:
            elapsed = pred.timestamp + timedelta(days=pred.horizon_days)
            if elapsed > now:
                continue

            try:
                history = await self._market_provider.get_history(pred.ticker, period="3mo")
                if not history:
                    continue

                start_price = None
                end_price = None

                sorted_bars = sorted(history, key=lambda x: x.timestamp)

                for bar in sorted_bars:
                    if bar.timestamp.date() >= pred.timestamp.date():
                        start_price = bar.close
                        break

                for bar in sorted_bars:
                    if bar.timestamp.date() >= elapsed.date():
                        end_price = bar.close
                        break

                if not start_price or not end_price:
                    try:
                        price_data = await self._market_provider.get_price(pred.ticker)
                        end_price = price_data.price
                        start_price = start_price or end_price
                    except Exception:
                        continue

                actual_move = ((end_price - start_price) / start_price) * 100
                await self._prediction_repo.update_outcome(pred.id, actual_move)
                evaluated_count += 1
                logger.debug(
                    "Evaluated prediction outcome",
                    ticker=pred.ticker,
                    expected=pred.distribution.expected_move_pct,
                    actual=actual_move,
                )

            except Exception as e:
                logger.error("Failed to evaluate prediction", prediction_id=pred.id, error=str(e))

        logger.info("Completed prediction evaluation cycle", evaluated=evaluated_count)
