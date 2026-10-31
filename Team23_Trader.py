"""QuantiFi 2026 trading algorithm.

The strategy combines a known-value anchor for AMETHYST, two small
product-specific price signals, and inventory-aware market making across the
remaining products.  It uses only the current TradingState and the compact
EMA state carried through traderData.
"""

import json
import math
from typing import Dict, List, Tuple

from datamodel import Order, OrderDepth, TradingState


POSITION_LIMITS: Dict[str, int] = {
    "AMETHYST": 50,
    "TOFFEE_CAKE": 50,
    "PAPER_LANTERNS": 50,
    "TELLURIUM": 40,
    "JELLY": 50,
    "PEANUT_BUTTER": 50,
    "DRAGONFRUIT": 40,
    "GRANADILLA": 40,
    "MANGOSTEEN": 40,
    "FRUIT_BASKET": 40,
    "LYCHEE": 200,
    "WHITE_PEARLS": 20,
    "BLACK_PEARLS": 20,
    "GOLDEN_PEARLS": 20,
    "PINK_PEARLS": 20,
    "BLUE_PEARLS": 20,
}

# The supplied data uses VOUCHER_<strike>; the Wiki describes these as
# LYCHEE_VOUCHERS_<strike>. Support either spelling with the same limit.
VOUCHER_STRIKES = (6800, 7000, 7200, 7300, 7400, 7500, 7600, 7750, 7900, 8100)
for _strike in VOUCHER_STRIKES:
    POSITION_LIMITS[f"VOUCHER_{_strike}"] = 50
    POSITION_LIMITS[f"LYCHEE_VOUCHERS_{_strike}"] = 50

BASE_ORDER_SIZE: Dict[str, int] = {
    "TELLURIUM": 2,
    "FRUIT_BASKET": 3,
}


class Trader:
    # This value is exact in all three supplied training files.
    AMETHYST_FAIR_VALUE = 10_000.0

    # EMA parameters are in ticks. PAPER_LANTERNS' price deviation from a
    # 100-tick average predicted continuation in all three training days.
    EMA_ALPHA = 2.0 / 101.0
    PAPER_MOMENTUM = 0.50
    TOFFEE_MEAN_REVERSION = 0.20

    DEFAULT_ORDER_SIZE = 5
    VOUCHER_ORDER_SIZE = 3
    MIN_TAKE_EDGE = 1.0

    @staticmethod
    def _load_memory(raw: str) -> dict:
        if not raw:
            return {"version": 1, "last_timestamp": None, "ema": {}, "count": {}}
        try:
            memory = json.loads(raw)
            if not isinstance(memory, dict) or memory.get("version") != 1:
                raise ValueError("unsupported traderData")
            if not isinstance(memory.get("ema"), dict) or not isinstance(
                memory.get("count"), dict
            ):
                raise ValueError("invalid traderData")
            return memory
        except (TypeError, ValueError, json.JSONDecodeError):
            return {"version": 1, "last_timestamp": None, "ema": {}, "count": {}}

    @staticmethod
    def _best_prices(book: OrderDepth) -> Tuple[int, int]:
        return max(book.buy_orders), min(book.sell_orders)

    @staticmethod
    def _order_size(symbol: str) -> int:
        if symbol.startswith("VOUCHER_") or symbol.startswith("LYCHEE_VOUCHERS_"):
            return Trader.VOUCHER_ORDER_SIZE
        return BASE_ORDER_SIZE.get(symbol, Trader.DEFAULT_ORDER_SIZE)

    def _update_fair_value(
        self, symbol: str, mid: float, memory: dict
    ) -> float:
        if symbol == "AMETHYST":
            fair = self.AMETHYST_FAIR_VALUE
        else:
            fair = mid

        previous_ema = memory["ema"].get(symbol)
        count = int(memory["count"].get(symbol, 0))
        if previous_ema is None:
            ema = mid
            count = 1
        else:
            ema = self.EMA_ALPHA * mid + (1.0 - self.EMA_ALPHA) * float(previous_ema)
            count += 1

        memory["ema"][symbol] = ema
        memory["count"][symbol] = count

        deviation = mid - ema
        warmup = min(1.0, count / 100.0)
        if symbol == "PAPER_LANTERNS":
            fair += self.PAPER_MOMENTUM * deviation * warmup
        elif symbol == "TOFFEE_CAKE":
            fair -= self.TOFFEE_MEAN_REVERSION * deviation * warmup

        return fair

    def _make_orders(
        self, symbol: str, book: OrderDepth, position: int, fair: float
    ) -> List[Order]:
        orders: List[Order] = []
        limit = POSITION_LIMITS.get(symbol)
        if limit is None:
            # Unknown products are left untouched rather than risking an
            # unrecognized position limit.
            return orders

        best_bid, best_ask = self._best_prices(book)
        bid_volume = max(0, int(book.buy_orders[best_bid]))
        ask_volume = max(0, -int(book.sell_orders[best_ask]))
        spread = max(1, best_ask - best_bid)

        # Top-of-book size imbalance gives a small short-horizon fair-value
        # adjustment. The coefficient is intentionally conservative.
        total_top_volume = bid_volume + ask_volume
        if total_top_volume:
            imbalance = (bid_volume - ask_volume) / total_top_volume
            fair += 0.25 * (spread / 2.0) * imbalance

        # Inventory shifts the reservation price toward reducing exposure.
        inventory_skew = (position / float(limit)) * max(2.0, spread * 0.50)
        reservation = fair - inventory_skew

        buy_capacity = max(0, limit - position)
        sell_capacity = max(0, limit + position)

        # Take only when the visible price is clearly favorable to the fair
        # value estimate. For ordinary mid-based products this rarely fires;
        # it is useful for the AMETHYST anchor and the two signal products.
        take_edge = max(self.MIN_TAKE_EDGE, spread * 0.20)
        if book.sell_orders and best_ask <= fair - take_edge and buy_capacity:
            quantity = min(buy_capacity, ask_volume, self._order_size(symbol))
            if quantity > 0:
                orders.append(Order(symbol, best_ask, quantity))
                buy_capacity -= quantity

        if book.buy_orders and best_bid >= fair + take_edge and sell_capacity:
            quantity = min(sell_capacity, bid_volume, self._order_size(symbol))
            if quantity > 0:
                orders.append(Order(symbol, best_bid, -quantity))
                sell_capacity -= quantity

        # Quote around the reservation price while staying behind the
        # opposite best quote, so these orders cannot accidentally cross.
        half_width = max(0.5, spread / 2.0)
        bid_price = min(best_ask - 1, math.floor(reservation - half_width))
        ask_price = max(best_bid + 1, math.ceil(reservation + half_width))

        base_size = self._order_size(symbol)
        inventory_fraction = min(1.0, abs(position) / float(limit))
        if position > 0:
            buy_size = max(1, int(round(base_size * (1.0 - 0.70 * inventory_fraction))))
            sell_size = max(1, int(round(base_size * (1.0 + 0.50 * inventory_fraction))))
        elif position < 0:
            buy_size = max(1, int(round(base_size * (1.0 + 0.50 * inventory_fraction))))
            sell_size = max(1, int(round(base_size * (1.0 - 0.70 * inventory_fraction))))
        else:
            buy_size = sell_size = base_size

        # Keep at least a small positive edge to the unskewed fair value.
        # Inventory skew may bring a quote inside the spread, but not through
        # fair value in a way that would knowingly lock in a loss.
        if buy_capacity > 0:
            bid_price = min(bid_price, math.floor(fair - 0.5))
            quantity = min(buy_capacity, buy_size)
            if quantity > 0:
                orders.append(Order(symbol, bid_price, quantity))

        if sell_capacity > 0:
            ask_price = max(ask_price, math.ceil(fair + 0.5))
            quantity = min(sell_capacity, sell_size)
            if quantity > 0:
                orders.append(Order(symbol, ask_price, -quantity))

        return orders

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        memory = self._load_memory(state.traderData)
        timestamp = int(state.timestamp)

        # The training data resets timestamp at each simulated day. Clear the
        # EMA so the overnight price gap does not become a false signal.
        previous_timestamp = memory.get("last_timestamp")
        if previous_timestamp is not None and timestamp < int(previous_timestamp):
            memory["ema"] = {}
            memory["count"] = {}

        result: Dict[str, List[Order]] = {}
        for symbol, book in state.order_depths.items():
            if not book.buy_orders or not book.sell_orders:
                continue
            best_bid, best_ask = self._best_prices(book)
            mid = (best_bid + best_ask) / 2.0
            fair = self._update_fair_value(symbol, mid, memory)
            orders = self._make_orders(
                symbol, book, int(state.position.get(symbol, 0)), fair
            )
            if orders:
                result[symbol] = orders

        memory["last_timestamp"] = timestamp
        return result, 0, json.dumps(memory, separators=(",", ":"))
