"""QuantiFi 2026 team 23 trading algorithm.

Multi-product market making with product-specific signals, voucher valuation,
and inventory-aware execution.
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
    "AMETHYST": 5,
    "PAPER_LANTERNS": 4,
    "TOFFEE_CAKE": 4,
    "TELLURIUM": 1,
    "FRUIT_BASKET": 2,
    "DRAGONFRUIT": 2,
    "GRANADILLA": 2,
    "MANGOSTEEN": 2,
    "JELLY": 2,
    "PEANUT_BUTTER": 2,
    "LYCHEE": 3,
    "WHITE_PEARLS": 2,
    "BLACK_PEARLS": 2,
    "GOLDEN_PEARLS": 2,
    "PINK_PEARLS": 2,
    "BLUE_PEARLS": 2,
}


class Trader:
    FUNDAMENTAL_PRODUCTS = {"AMETHYST"}
    MOMENTUM_PRODUCTS = {"PAPER_LANTERNS"}
    REVERSION_PRODUCTS = {"TOFFEE_CAKE"}
    CAUTIOUS_PRODUCTS = {"JELLY", "PEANUT_BUTTER", "BLACK_PEARLS"}
    RELATIVE_VALUE_PRODUCTS = {
        "FRUIT_BASKET",
        "DRAGONFRUIT",
        "GRANADILLA",
        "MANGOSTEEN",
    }

    # This value is exact in all three supplied training files.
    AMETHYST_FAIR_VALUE = 10_000.0

    # EMA parameters are in ticks. PAPER_LANTERNS' price deviation from a
    # 100-tick average predicted continuation in all three training days.
    EMA_ALPHA = 2.0 / 101.0
    FAST_EMA_ALPHA = 2.0 / 21.0
    PAPER_MOMENTUM = 0.50
    TOFFEE_MEAN_REVERSION = 0.20
    GENERAL_MOMENTUM = 0.30
    MAX_SIGNAL_MOVE = 2.0
    DEFAULT_ORDER_SIZE = 2
    VOUCHER_ORDER_SIZE = 1
    MIN_TAKE_EDGE = 0.5
    OPTION_TAKE_EDGE = 1.0
    MAX_TOTAL_VOL = 0.20
    MIN_TOTAL_VOL = 0.005
    OPTION_DELTA_LIMIT = 30.0
    DELTA_VOL = 0.10

    # Weak option wings remain covered for breadth, but are passive-only:
    # they cannot use an unsupported fair-value extrapolation or cross the
    # spread into uncertain liquidity.
    PASSIVE_ONLY_STRIKES = {6800, 8100}
    PASSIVE_WING_SPREAD_MULTIPLIER = 2.0
    CAUTIOUS_SIZE = 1
    CAUTIOUS_HALF_SPREAD_MULTIPLIER = 1.5

    @staticmethod
    def _load_memory(raw: str) -> dict:
        if not raw:
            return {
                "version": 2,
                "last_timestamp": None,
                "ema": {},
                "fast_ema": {},
                "count": {},
            }
        try:
            memory = json.loads(raw)
            if not isinstance(memory, dict) or memory.get("version") not in (1, 2):
                raise ValueError("unsupported traderData")
            if not isinstance(memory.get("ema"), dict) or not isinstance(
                memory.get("count"), dict
            ):
                raise ValueError("invalid traderData")
            if not isinstance(memory.get("fast_ema", {}), dict):
                raise ValueError("invalid traderData")
            memory["version"] = 2
            memory.setdefault("fast_ema", {})
            return memory
        except (TypeError, ValueError, json.JSONDecodeError):
            return {
                "version": 2,
                "last_timestamp": None,
                "ema": {},
                "fast_ema": {},
                "count": {},
            }

    @staticmethod
    def _best_prices(book: OrderDepth) -> Tuple[int, int]:
        return max(book.buy_orders), min(book.sell_orders)

    @staticmethod
    def _order_size(symbol: str) -> int:
        if symbol.startswith("VOUCHER_") or symbol.startswith("LYCHEE_VOUCHERS_"):
            return Trader.VOUCHER_ORDER_SIZE
        if symbol in Trader.CAUTIOUS_PRODUCTS:
            return Trader.CAUTIOUS_SIZE
        return BASE_ORDER_SIZE.get(symbol, Trader.DEFAULT_ORDER_SIZE)

    @staticmethod
    def _option_strike(symbol: str):
        if symbol.startswith("VOUCHER_") or symbol.startswith("LYCHEE_VOUCHERS_"):
            try:
                strike = int(symbol.rsplit("_", 1)[1])
                return strike if strike in VOUCHER_STRIKES else None
            except (IndexError, ValueError):
                return None
        return None

    @staticmethod
    def _normal_cdf(value: float) -> float:
        return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))

    @classmethod
    def _call_price(cls, spot: float, strike: int, total_vol: float) -> float:
        """Black-Scholes call value using total volatility sigma * sqrt(T)."""
        if total_vol <= 0.0:
            return max(spot - strike, 0.0)
        d1 = (math.log(spot / strike) + 0.5 * total_vol * total_vol) / total_vol
        d2 = d1 - total_vol
        return spot * cls._normal_cdf(d1) - strike * cls._normal_cdf(d2)

    @classmethod
    def _implied_total_vol(cls, price: float, spot: float, strike: int):
        """Infer total volatility from a call mid; reject unstable wing quotes."""
        intrinsic = max(spot - strike, 0.0)
        if price <= intrinsic + 0.05 or price >= spot - 0.05:
            return None

        low, high = cls.MIN_TOTAL_VOL, cls.MAX_TOTAL_VOL
        if cls._call_price(spot, strike, high) < price:
            return None
        for _ in range(16):
            middle = (low + high) / 2.0
            if cls._call_price(spot, strike, middle) < price:
                low = middle
            else:
                high = middle

        total_vol = (low + high) / 2.0
        d1 = (math.log(spot / strike) + 0.5 * total_vol * total_vol) / total_vol
        vega = spot * math.exp(-0.5 * d1 * d1) / math.sqrt(2.0 * math.pi)
        return total_vol if vega >= 80.0 else None

    def _option_fair_values(self, books: dict):
        """Price each call from neighboring strikes, leaving it out of its fit.

        This uses the live option chain to infer the current volatility smile,
        so it does not need a day counter or a guessed expiry at OOS startup.
        Wing contracts are not valued unless reliable strikes exist on both
        sides; those contracts use no model-driven option signal.
        """
        underlying = books.get("LYCHEE")
        if underlying is None or not underlying.buy_orders or not underlying.sell_orders:
            return {}
        spot = (
            max(underlying.buy_orders) + min(underlying.sell_orders)
        ) / 2.0
        if spot <= 0:
            return {}

        option_mids = {}
        for symbol, book in books.items():
            strike = self._option_strike(symbol)
            if strike is None or not book.buy_orders or not book.sell_orders:
                continue
            best_bid, best_ask = self._best_prices(book)
            option_mids[symbol] = (
                strike,
                (best_bid + best_ask) / 2.0,
            )

        nodes = []
        for symbol, (strike, mid) in option_mids.items():
            total_vol = self._implied_total_vol(mid, spot, strike)
            if total_vol is not None:
                nodes.append((math.log(strike / spot), strike, total_vol))
        nodes.sort(key=lambda node: node[0])

        fairs = {}
        for symbol, (strike, _) in option_mids.items():
            x = math.log(strike / spot)
            peers = [node for node in nodes if node[1] != strike]
            lower = [node for node in peers if node[0] < x]
            upper = [node for node in peers if node[0] > x]
            if lower and upper:
                x1, _, v1 = lower[-1]
                x2, _, v2 = upper[0]
            else:
                # Never extrapolate a volatility smile into an option wing.
                continue

            if x2 == x1:
                continue
            total_vol = v1 + (v2 - v1) * (x - x1) / (x2 - x1)
            total_vol = max(self.MIN_TOTAL_VOL, min(self.MAX_TOTAL_VOL, total_vol))
            fairs[symbol] = self._call_price(spot, strike, total_vol)
        return fairs

    @classmethod
    def _option_delta(cls, spot: float, strike: int) -> float:
        if spot <= 0 or strike <= 0:
            return 0.0
        total_vol = cls.DELTA_VOL
        d1 = (math.log(spot / strike) + 0.5 * total_vol * total_vol) / total_vol
        return cls._normal_cdf(d1)

    def _portfolio_delta(self, books: dict, positions: dict) -> float:
        underlying = books.get("LYCHEE")
        if underlying is None or not underlying.buy_orders or not underlying.sell_orders:
            return 0.0
        best_bid, best_ask = self._best_prices(underlying)
        spot = (best_bid + best_ask) / 2.0
        exposure = float(positions.get("LYCHEE", 0))
        for symbol, position in positions.items():
            strike = self._option_strike(symbol)
            if strike is not None:
                exposure += float(position) * self._option_delta(spot, strike)
        return exposure

    @staticmethod
    def _delta_capacity(net_delta: float, delta: float, direction: int, limit: float) -> int:
        if delta <= 0.0:
            return 10**9
        if direction > 0:
            return max(0, math.floor((limit - net_delta) / delta))
        return max(0, math.floor((net_delta + limit) / delta))

    @staticmethod
    def _risk_limit(symbol: str, hard_limit: int) -> int:
        """Use softer exposure targets to reduce adverse-selection losses."""
        if symbol in Trader.FUNDAMENTAL_PRODUCTS:
            fraction = 1.0
        elif symbol in Trader.MOMENTUM_PRODUCTS | Trader.REVERSION_PRODUCTS:
            fraction = 0.75
        elif symbol == "TELLURIUM":
            fraction = 0.25
        elif symbol in Trader.CAUTIOUS_PRODUCTS:
            fraction = 0.20
        elif symbol.startswith("VOUCHER_") or symbol.startswith("LYCHEE_VOUCHERS_"):
            fraction = 0.25
        else:
            fraction = 0.50
        return max(1, int(hard_limit * fraction))

    def _update_fair_value(
        self, symbol: str, mid: float, memory: dict
    ) -> float:
        if symbol in self.FUNDAMENTAL_PRODUCTS:
            fair = self.AMETHYST_FAIR_VALUE
        else:
            fair = mid

        previous_ema = memory["ema"].get(symbol)
        previous_fast_ema = memory["fast_ema"].get(symbol)
        count = int(memory["count"].get(symbol, 0))
        if previous_ema is None:
            ema = mid
            count = 1
        else:
            ema = self.EMA_ALPHA * mid + (1.0 - self.EMA_ALPHA) * float(previous_ema)
            count += 1
        if previous_fast_ema is None:
            fast_ema = mid
        else:
            fast_ema = self.FAST_EMA_ALPHA * mid + (
                1.0 - self.FAST_EMA_ALPHA
            ) * float(previous_fast_ema)

        memory["ema"][symbol] = ema
        memory["fast_ema"][symbol] = fast_ema
        memory["count"][symbol] = count

        deviation = mid - ema
        trend = fast_ema - ema
        warmup = min(1.0, count / 100.0)
        if symbol in self.MOMENTUM_PRODUCTS:
            fair += self.PAPER_MOMENTUM * deviation * warmup
        elif symbol in self.REVERSION_PRODUCTS:
            fair -= self.TOFFEE_MEAN_REVERSION * deviation * warmup
        elif symbol in self.CAUTIOUS_PRODUCTS:
            # for these products, avoid an unvalidated directional signal
            # and use inventory-aware passive market making instead
            pass
        elif symbol not in self.FUNDAMENTAL_PRODUCTS:
            # A bounded fast/slow EMA spread supplies a small directional
            # bias without allowing one stale tick to move fair value far
            # outside the executable market.
            fair += max(
                -self.MAX_SIGNAL_MOVE,
                min(self.MAX_SIGNAL_MOVE, self.GENERAL_MOMENTUM * trend),
            ) * warmup

        return fair

    def _make_orders(
        self,
        symbol: str,
        book: OrderDepth,
        position: int,
        fair: float,
        modeled_fair: bool = False,
        net_delta: float = 0.0,
        unit_delta: float = 0.0,
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
        # adjustment for products without a stronger valuation model.
        total_top_volume = bid_volume + ask_volume
        if total_top_volume and not modeled_fair:
            imbalance = (bid_volume - ask_volume) / total_top_volume
            fair += 0.25 * (spread / 2.0) * imbalance

        # Inventory shifts the reservation price toward reducing exposure.
        risk_limit = self._risk_limit(symbol, limit)
        inventory_skew = (position / float(risk_limit)) * max(2.0, spread * 0.50)
        reservation = fair - inventory_skew

        buy_capacity = max(0, risk_limit - position)
        sell_capacity = max(0, risk_limit + position)

        # weak products are quoted passively only, with wider prices and
        # reduced inventory; this is an experiment, not a proven improvement
        cautious = symbol in self.CAUTIOUS_PRODUCTS
        passive_wing = self._option_strike(symbol) in self.PASSIVE_ONLY_STRIKES

        # Cross only when the modeled edge covers a small execution buffer.
        # The buffer is deliberately below a full spread: a directional fair
        # value should be able to consume stale top-of-book liquidity.
        if self._option_strike(symbol) is not None and modeled_fair:
            take_edge = max(self.OPTION_TAKE_EDGE, spread * 0.75)
        else:
            take_edge = max(self.MIN_TAKE_EDGE, spread * 0.25)
        if (
            not cautious
            and not passive_wing
            and book.sell_orders
            and best_ask <= fair - take_edge
            and buy_capacity
        ):
            quantity = min(
                buy_capacity,
                ask_volume,
                self._order_size(symbol),
                self._delta_capacity(
                    net_delta, unit_delta, 1, self.OPTION_DELTA_LIMIT
                ),
            )
            if quantity > 0:
                orders.append(Order(symbol, best_ask, quantity))
                buy_capacity -= quantity
                net_delta += quantity * unit_delta

        if (
            not cautious
            and not passive_wing
            and book.buy_orders
            and best_bid >= fair + take_edge
            and sell_capacity
        ):
            quantity = min(
                sell_capacity,
                bid_volume,
                self._order_size(symbol),
                self._delta_capacity(
                    net_delta, unit_delta, -1, self.OPTION_DELTA_LIMIT
                ),
            )
            if quantity > 0:
                orders.append(Order(symbol, best_bid, -quantity))
                sell_capacity -= quantity
                net_delta -= quantity * unit_delta

        # Quote around the reservation price while staying behind the
        # opposite best quote, so these orders cannot accidentally cross.
        half_width = max(0.5, spread / 2.0)
        if cautious:
            half_width *= self.CAUTIOUS_HALF_SPREAD_MULTIPLIER
        if passive_wing:
            half_width *= self.PASSIVE_WING_SPREAD_MULTIPLIER
        bid_price = min(best_ask - 1, math.floor(reservation - half_width))
        ask_price = max(best_bid + 1, math.ceil(reservation + half_width))

        base_size = self._order_size(symbol)
        inventory_fraction = min(1.0, abs(position) / float(risk_limit))
        if position > 0:
            buy_size = max(1, int(round(base_size * (1.0 - 0.70 * inventory_fraction))))
            sell_size = max(1, int(round(base_size * (1.0 + 0.50 * inventory_fraction))))
        elif position < 0:
            buy_size = max(1, int(round(base_size * (1.0 + 0.50 * inventory_fraction))))
            sell_size = max(1, int(round(base_size * (1.0 - 0.70 * inventory_fraction))))
        else:
            buy_size = sell_size = base_size

        # Keep at least a small positive edge to the unskewed fair value.
        # Inventory skew may improve a quote inside the spread, but never
        # crosses fair value and knowingly locks in a loss.
        if buy_capacity > 0:
            bid_price = min(bid_price, math.floor(fair - 0.5))
            quantity = min(
                buy_capacity,
                buy_size,
                self._delta_capacity(
                    net_delta, unit_delta, 1, self.OPTION_DELTA_LIMIT
                ),
            )
            if quantity > 0:
                orders.append(Order(symbol, bid_price, quantity))
                net_delta += quantity * unit_delta

        if sell_capacity > 0:
            ask_price = max(ask_price, math.ceil(fair + 0.5))
            quantity = min(
                sell_capacity,
                sell_size,
                self._delta_capacity(
                    net_delta, unit_delta, -1, self.OPTION_DELTA_LIMIT
                ),
            )
            if quantity > 0:
                orders.append(Order(symbol, ask_price, -quantity))
                net_delta -= quantity * unit_delta

        return orders

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        memory = self._load_memory(state.traderData)
        timestamp = int(state.timestamp)

        # The training data resets timestamp at each simulated day. Clear the
        # EMA so the overnight price gap does not become a false signal.
        previous_timestamp = memory.get("last_timestamp")
        if previous_timestamp is not None and timestamp < int(previous_timestamp):
            memory["ema"] = {}
            memory["fast_ema"] = {}
            memory["count"] = {}

        option_fairs = self._option_fair_values(state.order_depths)
        net_delta = self._portfolio_delta(state.order_depths, state.position)
        result: Dict[str, List[Order]] = {}
        for symbol, book in state.order_depths.items():
            if not book.buy_orders or not book.sell_orders:
                continue
            best_bid, best_ask = self._best_prices(book)
            mid = (best_bid + best_ask) / 2.0
            fair = self._update_fair_value(symbol, mid, memory)
            modeled_fair = symbol == "AMETHYST"
            if symbol in option_fairs:
                fair = option_fairs[symbol]
                modeled_fair = True
            if self._option_strike(symbol) in self.PASSIVE_ONLY_STRIKES:
                # Wing prices are intentionally market-based only.
                fair = mid
                modeled_fair = False
            strike = self._option_strike(symbol)
            if symbol == "LYCHEE":
                unit_delta = 1.0
            elif strike is not None and state.order_depths.get("LYCHEE"):
                lychee = state.order_depths["LYCHEE"]
                if lychee.buy_orders and lychee.sell_orders:
                    lychee_bid, lychee_ask = self._best_prices(lychee)
                    unit_delta = self._option_delta(
                        (lychee_bid + lychee_ask) / 2.0, strike
                    )
                else:
                    unit_delta = 0.0
            else:
                unit_delta = 0.0
            orders = self._make_orders(
                symbol,
                book,
                int(state.position.get(symbol, 0)),
                fair,
                modeled_fair,
                net_delta,
                unit_delta,
            )
            if orders:
                result[symbol] = orders
                net_delta += sum(order.quantity for order in orders) * unit_delta

        memory["last_timestamp"] = timestamp
        return result, 0, json.dumps(memory, separators=(",", ":"))
