"""QuantiFi 2026 team 23 trading algorithm.

v8 capacity-only ablation experiment.

based on v7, preserving its validated directional models. v8 tests more
capacity in profitable product families, constrained lychee exposure, and
small passive jelly quotes. no pnl improvement is claimed until backtested.
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

    # exposure changes are the main v8 experiment; changing the alpha models
    # at the same time would make the results hard to interpret
    CORE_RISK_FRACTION = 0.82
    PROFITABLE_VOUCHER_RISK_FRACTION = 0.30
    LYCHEE_RISK_FRACTION = 0.50
    STABLE_VOUCHER_STRIKES = {7000, 7300, 7400, 7500, 7600, 7750, 7900}

    # an isolated low-risk breadth experiment on a wide-spread product
    ENABLE_JELLY_QUOTES = False
    JELLY_RISK_FRACTION = 0.08
    JELLY_HALF_SPREAD_MULTIPLIER = 0.85
    JELLY_MOMENTUM = 0.08
    JELLY_SIGNAL_CAP = 1.5

    DEFAULT_ORDER_SIZE = 2
    VOUCHER_ORDER_SIZE = 1
    MIN_TAKE_EDGE = 0.5
    OPTION_TAKE_EDGE = 1.0
    MAX_TOTAL_VOL = 0.20
    MIN_TOTAL_VOL = 0.005

    # experimental controls: isolate historically weak products without
    # changing the proven paper lanterns and toffee cake signals
    # v6: weak strikes remain available through conservative passive quoting
    PASSIVE_WINGS = {6800, 8100}
    WING_QUOTE_MULTIPLIER = 2.0
    # cross-asset models are individually gated following the v6 ablation
    # the basket and most pearl signals reduced training pnl and stay disabled
    ENABLE_BASKET_SIGNAL = False
    ENABLE_PEARL_SIGNALS = False
    ENABLE_PINK_PEARL_SIGNAL = True

    # v6: basket lead/lag signal and pearl common-factor residuals are capped
    BASKET_WEIGHTS = {"DRAGONFRUIT": 1.795, "GRANADILLA": 2.592, "MANGOSTEEN": 0.927}
    BASKET_ALPHA = 0.25
    BASKET_CAP = 1.0
    PEARL_ALPHA = 0.12
    PEARL_CAP = 0.8
    PEARLS = ("WHITE_PEARLS", "BLACK_PEARLS", "GOLDEN_PEARLS", "PINK_PEARLS", "BLUE_PEARLS")
    # only moderate total delta exposure; wing quotes get smaller risk budgets
    OPTION_DELTA_LIMIT = 35.0
    DELTA_TOTAL_VOL = 0.10
    CAUTIOUS_PRODUCTS = {"JELLY", "PEANUT_BUTTER", "BLACK_PEARLS"}
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
                "last_mids": {},
                "basket_signal": 0.0,
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
            memory.setdefault("last_mids", {})
            memory.setdefault("basket_signal", 0.0)
            return memory
        except (TypeError, ValueError, json.JSONDecodeError):
            return {
                "version": 2,
                "last_timestamp": None,
                "ema": {},
                "fast_ema": {},
                "count": {},
                "last_mids": {},
                "basket_signal": 0.0,
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
        If the live chain has too few reliable peer strikes, the contract
        falls back to ordinary order-book market making.
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
            # use only two-sided interpolation, never uncertain wing extrapolation
            if not lower or not upper:
                continue
            x1, _, v1 = lower[-1]
            x2, _, v2 = upper[0]

            if x2 == x1:
                continue
            total_vol = v1 + (v2 - v1) * (x - x1) / (x2 - x1)
            total_vol = max(self.MIN_TOTAL_VOL, min(self.MAX_TOTAL_VOL, total_vol))
            fairs[symbol] = self._call_price(spot, strike, total_vol)
        return fairs

    @classmethod
    def _option_delta(cls, spot: float, strike: int) -> float:
        # estimate directional option exposure using a bounded total volatility
        if spot <= 0:
            return 0.0
        v = cls.DELTA_TOTAL_VOL
        d1 = (math.log(spot / strike) + 0.5 * v * v) / v
        return cls._normal_cdf(d1)

    def _cross_asset_fairs(self, books: dict, memory: dict) -> dict:
        # use only observed prior-tick changes; never access future data
        mids = {}
        for symbol, book in books.items():
            if book.buy_orders and book.sell_orders:
                bid, ask = self._best_prices(book)
                mids[symbol] = (bid + ask) / 2.0
        previous = memory.get("last_mids", {})
        changes = {k: v - float(previous[k]) for k, v in mids.items() if k in previous}
        fairs = {}

        # predict a limited basket adjustment from contemporaneous fruit moves
        if self.ENABLE_BASKET_SIGNAL and "FRUIT_BASKET" in mids and all(k in changes for k in self.BASKET_WEIGHTS):
            fruit_move = sum(self.BASKET_WEIGHTS[k] * changes[k] for k in self.BASKET_WEIGHTS)
            basket_move = changes.get("FRUIT_BASKET", 0.0)
            innovation = fruit_move - basket_move
            # update one-step signal conservatively, with a bounded influence
            memory["basket_signal"] = 0.75 * float(memory.get("basket_signal", 0.0)) + 0.25 * innovation
            correction = max(-self.BASKET_CAP, min(self.BASKET_CAP, self.BASKET_ALPHA * memory["basket_signal"]))
            fairs["FRUIT_BASKET"] = mids["FRUIT_BASKET"] + correction

        # market-neutral pearl residual: compare each pearl's percentage move
        # to the median percentage move of the other pearls
        if (self.ENABLE_PEARL_SIGNALS or self.ENABLE_PINK_PEARL_SIGNAL) and all(p in mids and p in previous and float(previous[p]) > 0 for p in self.PEARLS):
            returns = {p: changes[p] / float(previous[p]) for p in self.PEARLS}
            for p in self.PEARLS:
                if not self.ENABLE_PEARL_SIGNALS and p != "PINK_PEARLS":
                    continue
                others = sorted(returns[q] for q in self.PEARLS if q != p)
                peer_return = 0.5 * (others[1] + others[2])
                relative_move = mids[p] * (peer_return - returns[p])
                correction = max(-self.PEARL_CAP, min(self.PEARL_CAP, self.PEARL_ALPHA * relative_move))
                fairs[p] = mids[p] + correction

        # cap persistent state so it remains cheap to serialize on each tick
        memory["last_mids"] = {p: mids[p] for p in mids}
        return fairs

    @staticmethod
    def _delta_budget(exposure: float, unit_delta: float, direction: int, limit: float) -> int:
        # zero delta instruments do not consume the option risk budget
        if unit_delta <= 0:
            return 10**9
        available = (limit - exposure) / unit_delta if direction > 0 else (limit + exposure) / unit_delta
        return max(0, int(math.floor(max(0.0, available))))

    @staticmethod
    def _risk_limit(symbol: str, hard_limit: int) -> int:
        """Use softer exposure targets to reduce adverse-selection losses."""
        if symbol == "AMETHYST":
            fraction = 1.0
        elif symbol in ("PAPER_LANTERNS", "TOFFEE_CAKE"):
            # these strategies were positive in each of the three training days
            fraction = Trader.CORE_RISK_FRACTION
        elif symbol == "TELLURIUM":
            fraction = 0.25
        elif symbol == "LYCHEE":
            # lychee was net negative in v7; retain trading for option hedges
            # but avoid the historically oversized outright inventory
            fraction = Trader.LYCHEE_RISK_FRACTION
        elif symbol == "JELLY" and Trader.ENABLE_JELLY_QUOTES:
            fraction = Trader.JELLY_RISK_FRACTION
        elif symbol in Trader.CAUTIOUS_PRODUCTS:
            fraction = 0.20
        elif Trader._option_strike(symbol) in Trader.PASSIVE_WINGS:
            fraction = 0.15
        elif Trader._option_strike(symbol) in Trader.STABLE_VOUCHER_STRIKES:
            # seven interior strikes earned positive pnl on every training day
            # the remaining voucher strikes retain v7's conservative budget
            fraction = Trader.PROFITABLE_VOUCHER_RISK_FRACTION
        elif symbol.startswith("VOUCHER_") or symbol.startswith("LYCHEE_VOUCHERS_"):
            fraction = 0.25
        else:
            fraction = 0.50
        return max(1, int(hard_limit * fraction))

    def _update_fair_value(
        self, symbol: str, mid: float, memory: dict
    ) -> float:
        if symbol == "AMETHYST":
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
        if symbol == "PAPER_LANTERNS":
            fair += self.PAPER_MOMENTUM * deviation * warmup
        elif symbol == "TOFFEE_CAKE":
            fair -= self.TOFFEE_MEAN_REVERSION * deviation * warmup
        elif symbol == "JELLY" and self.ENABLE_JELLY_QUOTES:
            # the historical 25-tick continuation signal was positive on all
            # three training days; use it only to tilt small passive quotes
            correction = self.JELLY_MOMENTUM * deviation * warmup
            fair += max(-self.JELLY_SIGNAL_CAP, min(self.JELLY_SIGNAL_CAP, correction))
        elif symbol in self.CAUTIOUS_PRODUCTS:
            # for these products, avoid unvalidated directional signals
            pass
        elif symbol != "AMETHYST":
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
        delta_exposure: float = 0.0,
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
        cautious = symbol in self.CAUTIOUS_PRODUCTS or self._option_strike(symbol) in self.PASSIVE_WINGS

        # Cross only when the modeled edge covers a small execution buffer.
        # The buffer is deliberately below a full spread: a directional fair
        # value should be able to consume stale top-of-book liquidity.
        if self._option_strike(symbol) is not None and modeled_fair:
            take_edge = max(self.OPTION_TAKE_EDGE, spread * 0.75)
        else:
            take_edge = max(self.MIN_TAKE_EDGE, spread * 0.25)
        if not cautious and book.sell_orders and best_ask <= fair - take_edge and buy_capacity:
            quantity = min(buy_capacity, ask_volume, self._order_size(symbol), self._delta_budget(delta_exposure, unit_delta, 1, self.OPTION_DELTA_LIMIT))
            if quantity > 0:
                orders.append(Order(symbol, best_ask, quantity))
                buy_capacity -= quantity
                delta_exposure += quantity * unit_delta

        if not cautious and book.buy_orders and best_bid >= fair + take_edge and sell_capacity:
            quantity = min(sell_capacity, bid_volume, self._order_size(symbol), self._delta_budget(delta_exposure, unit_delta, -1, self.OPTION_DELTA_LIMIT))
            if quantity > 0:
                orders.append(Order(symbol, best_bid, -quantity))
                sell_capacity -= quantity
                delta_exposure -= quantity * unit_delta

        # Quote around the reservation price while staying behind the
        # opposite best quote, so these orders cannot accidentally cross.
        half_width = max(0.5, spread / 2.0)
        if symbol == "JELLY" and self.ENABLE_JELLY_QUOTES:
            # place an occasional competitive passive quote inside the wide
            # jelly spread, with inventory capped to four contracts
            half_width *= self.JELLY_HALF_SPREAD_MULTIPLIER
        elif cautious:
            half_width *= self.CAUTIOUS_HALF_SPREAD_MULTIPLIER
        if self._option_strike(symbol) in self.PASSIVE_WINGS:
            half_width *= self.WING_QUOTE_MULTIPLIER
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
            quantity = min(buy_capacity, buy_size, self._delta_budget(delta_exposure, unit_delta, 1, self.OPTION_DELTA_LIMIT))
            if quantity > 0:
                orders.append(Order(symbol, bid_price, quantity))
                delta_exposure += quantity * unit_delta

        if sell_capacity > 0:
            ask_price = max(ask_price, math.ceil(fair + 0.5))
            quantity = min(sell_capacity, sell_size, self._delta_budget(delta_exposure, unit_delta, -1, self.OPTION_DELTA_LIMIT))
            if quantity > 0:
                orders.append(Order(symbol, ask_price, -quantity))
                delta_exposure -= quantity * unit_delta

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
            memory["last_mids"] = {}
            memory["basket_signal"] = 0.0

        option_fairs = self._option_fair_values(state.order_depths)
        cross_fairs = self._cross_asset_fairs(state.order_depths, memory)
        lychee_book = state.order_depths.get("LYCHEE")
        spot = None
        if lychee_book and lychee_book.buy_orders and lychee_book.sell_orders:
            bid, ask = self._best_prices(lychee_book)
            spot = (bid + ask) / 2.0
        net_delta = float(state.position.get("LYCHEE", 0))
        if spot is not None:
            for name, position in state.position.items():
                strike = self._option_strike(name)
                if strike is not None:
                    net_delta += float(position) * self._option_delta(spot, strike)
        result: Dict[str, List[Order]] = {}
        for symbol, book in state.order_depths.items():
            if not book.buy_orders or not book.sell_orders:
                continue
            best_bid, best_ask = self._best_prices(book)
            mid = (best_bid + best_ask) / 2.0
            fair = self._update_fair_value(symbol, mid, memory)
            modeled_fair = symbol == "AMETHYST" or (
                symbol == "JELLY" and self.ENABLE_JELLY_QUOTES
            )
            # only enable signals with a positive controlled test result
            # pink pearls improved slightly in v6; all other additions hurt
            apply_cross = (
                (symbol == "FRUIT_BASKET" and self.ENABLE_BASKET_SIGNAL)
                or (symbol == "PINK_PEARLS" and self.ENABLE_PINK_PEARL_SIGNAL)
                or (symbol in self.PEARLS and self.ENABLE_PEARL_SIGNALS)
            )
            if apply_cross and symbol in cross_fairs:
                fair = cross_fairs[symbol]
                modeled_fair = True
            if symbol in option_fairs:
                fair = option_fairs[symbol]
                modeled_fair = True
            strike = self._option_strike(symbol)
            if strike in self.PASSIVE_WINGS:
                fair = mid
                modeled_fair = False
            unit_delta = (1.0 if symbol == "LYCHEE" else
                          self._option_delta(spot, strike) if spot is not None and strike is not None else 0.0)
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
                net_delta += sum(o.quantity for o in orders) * unit_delta

        memory["last_timestamp"] = timestamp
        return result, 0, json.dumps(memory, separators=(",", ":"))
