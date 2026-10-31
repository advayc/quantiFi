"""QuantiFi Team 23, V12B: causal multi-product market making.

Preserves V8 Growth's directional models. Independent buy/sell delta
reservations prevent unfilled opposite orders from masking exposure.
All persistent state is carried in traderData. Historical performance is
not an estimate of guaranteed out-of-sample returns.
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

# the supplied data uses voucher_<strike>; the wiki describes these as
# lychee_vouchers_<strike>. support either spelling with the same limit.
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
    # this value is exact in all three supplied training files.
    AMETHYST_FAIR_VALUE = 10_000.0

    # ema parameters are in ticks. paper_lanterns' price deviation from a
    # 100-tick average predicted continuation in all three training days.
    EMA_ALPHA = 2.0 / 101.0
    FAST_EMA_ALPHA = 2.0 / 21.0
    PAPER_MOMENTUM = 0.50
    TOFFEE_MEAN_REVERSION = 0.20
    GENERAL_MOMENTUM = 0.30
    MAX_SIGNAL_MOVE = 2.0

    # V10 capacity: 49 contracts on the two core products and 20 on
    # selected calls, with independent portfolio delta reservations.
    CORE_RISK_FRACTION = 0.98
    PROFITABLE_VOUCHER_RISK_FRACTION = 0.40
    LYCHEE_RISK_FRACTION = 0.12
    STABLE_VOUCHER_STRIKES = {7000, 7300, 7400, 7500, 7600, 7750, 7900}

    # an isolated low-risk breadth experiment on a wide-spread product
    ENABLE_JELLY_QUOTES = True
    JELLY_EXIT_ONLY = True
    JELLY_RISK_FRACTION = 0.04
    JELLY_HALF_SPREAD_MULTIPLIER = 1.0
    JELLY_MOMENTUM = 0.0
    JELLY_SIGNAL_CAP = 1.5
    JELLY_MIN_SPREAD = 11
    JELLY_MAX_TICK_MOVE = 5.0

    # Passive exits may concede estimated edge to reduce non-core inventory.
    INVENTORY_EXIT_PRODUCTS = {
        "TELLURIUM", "FRUIT_BASKET", "DRAGONFRUIT", "GRANADILLA",
        "MANGOSTEEN", "JELLY", "PEANUT_BUTTER", "LYCHEE",
        "WHITE_PEARLS", "BLACK_PEARLS", "GOLDEN_PEARLS", "PINK_PEARLS", "BLUE_PEARLS",
    }
    DEFAULT_ORDER_SIZE = 2
    VOUCHER_ORDER_SIZE = 1
    MIN_TAKE_EDGE = 0.5
    OPTION_TAKE_EDGE = 1.0
    MAX_TOTAL_VOL = 0.20
    MIN_TOTAL_VOL = 0.005

    # experimental controls: isolate historically weak products without
    # changing the paper lanterns and toffee cake signal parameters
    # v6: weak strikes remain available through conservative passive quoting
    PASSIVE_WINGS = {6800, 8100}
    WING_QUOTE_MULTIPLIER = 1.0
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
    DELTA_TOTAL_VOL = 0.10  # fallback only when no reliable live volatility exists
    CAUTIOUS_PRODUCTS = {"JELLY", "PEANUT_BUTTER", "BLACK_PEARLS"}
    CAUTIOUS_SIZE = 1
    CAUTIOUS_HALF_SPREAD_MULTIPLIER = 1.0

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
            for key in ("ema", "fast_ema", "last_mids", "count"):
                values = memory.get(key, {})
                if not isinstance(values, dict) or any(
                    isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                    for v in values.values()
                ):
                    raise ValueError("invalid numeric memory")
            last = memory.get("last_timestamp")
            if last is not None and (not isinstance(last, (int, float)) or not math.isfinite(last)):
                raise ValueError("invalid timestamp")
            if not isinstance(memory.get("basket_signal", 0), (int, float)) or not math.isfinite(memory.get("basket_signal", 0)):
                raise ValueError("invalid basket state")
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

    @classmethod
    def _order_size(cls, symbol: str) -> int:
        if symbol.startswith("VOUCHER_") or symbol.startswith("LYCHEE_VOUCHERS_"):
            return cls.VOUCHER_ORDER_SIZE
        if symbol in cls.CAUTIOUS_PRODUCTS:
            return cls.CAUTIOUS_SIZE
        return BASE_ORDER_SIZE.get(symbol, cls.DEFAULT_ORDER_SIZE)

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
        if cls._call_price(spot, strike, low) > price or cls._call_price(spot, strike, high) < price:
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
            value = self._call_price(spot, strike, total_vol)
            # A zero-rate call is decreasing and 1-Lipschitz in strike.
            # Use executable peer bid/ask intervals, not mid-only equalities:
            # C(K) lies between C(L)-(K-L) and C(L) for L<K,
            # and between C(U) and C(U)+(U-K) for U>K.
            # These are valuation guardrails, not atomic multi-leg arbitrage.
            floor_value = max(0.0, spot - strike)
            ceiling_value = spot
            for peer, (peer_strike, _) in option_mids.items():
                if peer_strike == strike:
                    continue
                peer_bid, peer_ask = self._best_prices(books[peer])
                gap = strike - peer_strike
                floor_value = max(floor_value, peer_bid - max(0, gap))
                ceiling_value = min(ceiling_value, peer_ask + max(0, -gap))
            if floor_value > ceiling_value:
                # Inconsistent chain: decline its cross-strike valuation.
                continue
            fairs[symbol] = max(floor_value, min(ceiling_value, value))
        return fairs

    @classmethod
    def _option_delta(cls, spot: float, strike: int, total_vol=None) -> float:
        # estimate directional option exposure using a bounded total volatility
        if spot <= 0:
            return 0.0
        v = total_vol if total_vol is not None else cls.DELTA_TOTAL_VOL
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

        # Peer-relative pearl residual (portfolio neutrality is not enforced): compare each pearl's percentage move
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

    @classmethod
    def _risk_limit(cls, symbol: str, hard_limit: int) -> int:
        """Use softer exposure targets to reduce adverse-selection losses."""
        if symbol == "AMETHYST":
            fraction = 1.0
        elif symbol in ("PAPER_LANTERNS", "TOFFEE_CAKE"):
            # these strategies were positive in each of the three training days
            fraction = cls.CORE_RISK_FRACTION
        elif symbol == "TELLURIUM":
            fraction = 0.25
        elif symbol == "LYCHEE":
            # Limit outright underlying inventory; this is not an active hedge.
            fraction = cls.LYCHEE_RISK_FRACTION
        elif symbol == "JELLY" and cls.ENABLE_JELLY_QUOTES:
            fraction = cls.JELLY_RISK_FRACTION
        elif symbol in cls.CAUTIOUS_PRODUCTS:
            fraction = 0.04
        elif cls._option_strike(symbol) in cls.PASSIVE_WINGS:
            fraction = 0.04
        elif cls._option_strike(symbol) in cls.STABLE_VOUCHER_STRIKES:
            # seven interior strikes earned positive pnl on every training day
            # the remaining voucher strikes retain v7's conservative budget
            fraction = cls.PROFITABLE_VOUCHER_RISK_FRACTION
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
            # Optional bounded directional tilt; disabled in selected V10.
            correction = self.JELLY_MOMENTUM * deviation * warmup
            fair += max(-self.JELLY_SIGNAL_CAP, min(self.JELLY_SIGNAL_CAP, correction))
        elif symbol in self.CAUTIOUS_PRODUCTS:
            # for these products, avoid unvalidated directional signals
            pass
        elif symbol != "AMETHYST":
            # a bounded fast/slow ema spread supplies a small directional
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
        delta_lower=None,
        reduce_only: bool = False,
    ) -> List[Order]:
        # Upper bound reserves every proposed buy; lower reserves every sell.
        # Never credit an unfilled opposite-side order against either bound.
        delta_upper = delta_exposure
        delta_lower = delta_exposure if delta_lower is None else delta_lower
        orders: List[Order] = []
        limit = POSITION_LIMITS.get(symbol)
        if limit is None:
            # unknown products are left untouched rather than risking an
            # unrecognized position limit.
            return orders

        best_bid, best_ask = self._best_prices(book)
        bid_volume = max(0, int(book.buy_orders[best_bid]))
        ask_volume = max(0, -int(book.sell_orders[best_ask]))
        spread = max(1, best_ask - best_bid)

        # top-of-book size imbalance gives a small short-horizon fair-value
        # adjustment for products without a stronger valuation model.
        total_top_volume = bid_volume + ask_volume
        if total_top_volume and not modeled_fair:
            imbalance = (bid_volume - ask_volume) / total_top_volume
            fair += 0.25 * (spread / 2.0) * imbalance

        # inventory shifts the reservation price toward reducing exposure.
        risk_limit = self._risk_limit(symbol, limit)
        inventory_skew = (position / float(risk_limit)) * max(2.0, spread * 0.50)
        reservation = fair - inventory_skew

        buy_capacity = max(0, risk_limit - position)
        sell_capacity = max(0, risk_limit + position)
        if reduce_only:
            buy_capacity = min(buy_capacity, max(0, -position))
            sell_capacity = min(sell_capacity, max(0, position))

        # weak products are quoted passively only, with wider prices and
        # reduced inventory; this is an experiment, not a proven improvement
        cautious = symbol in self.CAUTIOUS_PRODUCTS or self._option_strike(symbol) in self.PASSIVE_WINGS

        # cross only when the modeled edge covers a small execution buffer.
        # the buffer is deliberately below a full spread: a directional fair
        # value should be able to consume stale top-of-book liquidity.
        if self._option_strike(symbol) is not None and modeled_fair:
            take_edge = max(self.OPTION_TAKE_EDGE, spread * 0.75)
        else:
            take_edge = max(self.MIN_TAKE_EDGE, spread * 0.25)
        if not cautious and book.sell_orders and best_ask <= fair - take_edge and buy_capacity:
            quantity = min(buy_capacity, ask_volume, self._order_size(symbol), self._delta_budget(delta_upper, unit_delta, 1, self.OPTION_DELTA_LIMIT))
            if quantity > 0:
                orders.append(Order(symbol, best_ask, quantity))
                buy_capacity -= quantity
                delta_upper += quantity * unit_delta

        if not cautious and book.buy_orders and best_bid >= fair + take_edge and sell_capacity:
            quantity = min(sell_capacity, bid_volume, self._order_size(symbol), self._delta_budget(delta_lower, unit_delta, -1, self.OPTION_DELTA_LIMIT))
            if quantity > 0:
                orders.append(Order(symbol, best_bid, -quantity))
                sell_capacity -= quantity
                delta_lower -= quantity * unit_delta

        # quote around the reservation price while staying behind the
        # opposite best quote, so these orders cannot accidentally cross.
        half_width = max(0.5, spread / 2.0)
        if symbol == "JELLY" and self.ENABLE_JELLY_QUOTES:
            # place an occasional competitive passive quote inside the wide
            # jelly spread, with inventory capped by JELLY_RISK_FRACTION
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

        # Inventory has a holding cost. For non-core products, the reducing
        # side can concede part of the spread; never exceed the held amount
        # on that concessional quote or cross the opposite top of book.
        exit_allowance = 0.0
        if symbol in self.INVENTORY_EXIT_PRODUCTS and position:
            exit_allowance = min(spread / 2.0, abs(inventory_skew))
            if position > 0:
                sell_size = min(sell_size, max(0, position - sum(-o.quantity for o in orders if o.quantity < 0)))
            else:
                buy_size = min(buy_size, max(0, -position - sum(o.quantity for o in orders if o.quantity > 0)))
        # Entry-side quotes retain a small estimated edge.
        # Prices retain an edge to estimated fair value. Estimation errors
        # and later market moves can still cause losses.
        if buy_capacity > 0:
            bid_price = min(bid_price, math.floor(fair - 0.5 + (exit_allowance if position < 0 else 0.0)))
            quantity = min(buy_capacity, buy_size, self._delta_budget(delta_upper, unit_delta, 1, self.OPTION_DELTA_LIMIT))
            if quantity > 0:
                orders.append(Order(symbol, bid_price, quantity))
                delta_upper += quantity * unit_delta

        if sell_capacity > 0:
            ask_price = max(ask_price, math.ceil(fair + 0.5 - (exit_allowance if position > 0 else 0.0)))
            quantity = min(sell_capacity, sell_size, self._delta_budget(delta_lower, unit_delta, -1, self.OPTION_DELTA_LIMIT))
            if quantity > 0:
                orders.append(Order(symbol, ask_price, -quantity))
                delta_lower -= quantity * unit_delta

        return orders

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        memory = self._load_memory(state.traderData)
        timestamp = int(state.timestamp)

        # Reset state only if the supplied clock moves backwards.
        # A continuous multi-day clock intentionally preserves the EMAs.
        previous_timestamp = memory.get("last_timestamp")
        if previous_timestamp is not None and timestamp < int(previous_timestamp):
            memory["ema"] = {}
            memory["fast_ema"] = {}
            memory["count"] = {}
            memory["last_mids"] = {}
            memory["basket_signal"] = 0.0

        # record the last jelly mid before updating last_mids, so the
        # volatility gate measures an actual one-tick move instead of the
        # distance from a slowly changing average
        previous_jelly_mid = memory["last_mids"].get("JELLY")
        option_fairs = self._option_fair_values(state.order_depths)
        cross_fairs = self._cross_asset_fairs(state.order_depths, memory)
        lychee_book = state.order_depths.get("LYCHEE")
        spot = None
        if lychee_book and lychee_book.buy_orders and lychee_book.sell_orders:
            bid, ask = self._best_prices(lychee_book)
            spot = (bid + ask) / 2.0
        # Use the same live total volatility as valuation where available.
        deltas = {}
        if spot is not None and spot > 0:
            for name, book in state.order_depths.items():
                strike = self._option_strike(name)
                if strike is not None and book.buy_orders and book.sell_orders:
                    bid, ask = self._best_prices(book)
                    value = option_fairs.get(name, (bid + ask) / 2.0)
                    vol = self._implied_total_vol(value, spot, strike)
                    deltas[name] = self._option_delta(spot, strike, vol)
        net_delta = float(state.position.get("LYCHEE", 0))
        if spot is not None:
            for name, position in state.position.items():
                strike = self._option_strike(name)
                if strike is not None:
                    net_delta += float(position) * deltas.get(name, self._option_delta(spot, strike))
        delta_upper = delta_lower = net_delta
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
            if strike is not None and spot is None:
                continue  # No new option orders without an observed underlying.
            unit_delta = 1.0 if symbol == "LYCHEE" else deltas.get(symbol, 0.0)
            reduce_only = False
            if symbol == "JELLY":
                entry_ok = self.ENABLE_JELLY_QUOTES and best_ask - best_bid >= self.JELLY_MIN_SPREAD
                if previous_jelly_mid is not None:
                    entry_ok = entry_ok and abs(mid - float(previous_jelly_mid)) <= self.JELLY_MAX_TICK_MOVE
                reduce_only = not entry_ok
                if reduce_only and not self.JELLY_EXIT_ONLY:
                    continue

            orders = self._make_orders(
                symbol,
                book,
                int(state.position.get(symbol, 0)),
                fair,
                modeled_fair,
                delta_upper,
                unit_delta,
                delta_lower,
                reduce_only,
            )
            if orders:
                result[symbol] = orders
                delta_upper += sum(max(0, o.quantity) for o in orders) * unit_delta
                delta_lower += sum(min(0, o.quantity) for o in orders) * unit_delta

        memory["last_timestamp"] = timestamp
        return result, 0, json.dumps(memory, separators=(",", ":"))
