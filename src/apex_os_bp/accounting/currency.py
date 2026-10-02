"""Multi-currency support: exchange rates, conversion, and Money type."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional


class Currency(str, Enum):
    """ISO 4217 currency codes."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    CNY = "CNY"
    INR = "INR"
    BRL = "BRL"
    MXN = "MXN"
    SGD = "SGD"
    HKD = "HKD"
    KRW = "KRW"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"
    NZD = "NZD"
    ZAR = "ZAR"
    AED = "AED"
    SAR = "SAR"


# Default precision for each currency (ISO 4217).
_CURRENCY_PRECISION: dict[str, int] = {
    "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "CHF": 2,
    "CAD": 2, "AUD": 2, "CNY": 2, "INR": 2, "BRL": 2,
    "MXN": 2, "SGD": 2, "HKD": 2, "KRW": 0, "SEK": 2,
    "NOK": 2, "DKK": 2, "NZD": 2, "ZAR": 2, "AED": 2,
    "SAR": 2,
}


def _precision_for(currency: str) -> int:
    """Return the decimal precision for a currency code."""
    return _CURRENCY_PRECISION.get(currency.upper(), 2)


def _quantize(amount: Decimal, currency: str) -> Decimal:
    """Round *amount* to the currency's standard precision."""
    places = _precision_for(currency)
    exponent = Decimal(1).scaleb(-places)
    return amount.quantize(exponent, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ExchangeRate:
    """A single exchange-rate observation."""

    base_currency: str
    quote_currency: str
    rate: Decimal
    effective_date: date = field(default_factory=date.today)
    source: str = "manual"
    rate_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if self.base_currency == self.quote_currency:
            raise ValueError("Base and quote currency must differ")
        if self.rate <= 0:
            raise ValueError("Exchange rate must be positive")

    def inverse(self) -> ExchangeRate:
        """Return the reciprocal rate (quote → base)."""
        return ExchangeRate(
            base_currency=self.quote_currency,
            quote_currency=self.base_currency,
            rate=Decimal("1") / self.rate,
            effective_date=self.effective_date,
            source=self.source,
        )


@dataclass
class Money:
    """An amount tagged with a currency."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if isinstance(self.amount, (int, float)):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        object.__setattr__(self, "amount", _quantize(self.amount, self.currency))

    # -- arithmetic ---------------------------------------------------------

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot add {self.currency} and {other.currency} without conversion"
            )
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot subtract {other.currency} from {self.currency} without conversion"
            )
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount >= other.amount

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def __repr__(self) -> str:
        return f"Money({self.amount}, '{self.currency}')"

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"

    def convert_to(
        self, target_currency: str, rate: Decimal | float | str
    ) -> Money:
        """Convert to *target_currency* using the supplied *rate*."""
        if self.currency == target_currency:
            return Money(self.amount, self.currency)
        rate_dec = Decimal(str(rate))
        if rate_dec <= 0:
            raise ValueError("Exchange rate must be positive")
        converted = _quantize(self.amount * rate_dec, target_currency)
        return Money(converted, target_currency)


class CurrencyConverter:
    """Convert amounts between currencies using stored exchange rates."""

    def __init__(self) -> None:
        self._rates: dict[tuple[str, str], ExchangeRate] = {}

    # -- rate management ----------------------------------------------------

    def add_rate(self, rate: ExchangeRate) -> None:
        """Register an exchange rate (and its inverse)."""
        key = (rate.base_currency, rate.quote_currency)
        self._rates[key] = rate
        inv_key = (rate.quote_currency, rate.base_currency)
        self._rates[inv_key] = rate.inverse()

    def add_rate_from_values(
        self,
        base: str,
        quote: str,
        rate: Decimal | float | str,
        effective_date: Optional[date] = None,
        source: str = "manual",
    ) -> ExchangeRate:
        """Convenience: build an ExchangeRate from raw values and store it."""
        er = ExchangeRate(
            base_currency=base.upper(),
            quote_currency=quote.upper(),
            rate=Decimal(str(rate)),
            effective_date=effective_date or date.today(),
            source=source,
        )
        self.add_rate(er)
        return er

    def get_rate(self, base: str, quote: str) -> ExchangeRate:
        """Look up a direct exchange rate."""
        key = (base.upper(), quote.upper())
        if key not in self._rates:
            raise KeyError(f"No exchange rate for {base} → {quote}")
        return self._rates[key]

    def has_rate(self, base: str, quote: str) -> bool:
        """Return True if a direct rate exists."""
        return (base.upper(), quote.upper()) in self._rates

    def remove_rate(self, base: str, quote: str) -> None:
        """Remove a rate pair (both directions)."""
        key = (base.upper(), quote.upper())
        inv_key = (quote.upper(), base.upper())
        self._rates.pop(key, None)
        self._rates.pop(inv_key, None)

    @property
    def available_currencies(self) -> set[str]:
        """All currencies that have at least one rate registered."""
        currencies: set[str] = set()
        for base, quote in self._rates:
            currencies.add(base)
            currencies.add(quote)
        return currencies

    # -- conversion --------------------------------------------------------

    def convert(
        self,
        amount: Decimal | float | str | Money,
        target_currency: str,
        source_currency: Optional[str] = None,
    ) -> Money:
        """Convert *amount* to *target_currency*.

        If *amount* is a :class:`Money` instance its currency is used
        unless *source_currency* is explicitly provided.
        """
        if isinstance(amount, Money):
            src = source_currency or amount.currency
            amt = amount.amount
        else:
            if source_currency is None:
                raise ValueError("source_currency required when amount is not Money")
            src = source_currency
            amt = Decimal(str(amount))

        src = src.upper()
        tgt = target_currency.upper()

        if src == tgt:
            return Money(amt, tgt)

        rate = self.get_rate(src, tgt)
        converted = _quantize(amt * rate.rate, tgt)
        return Money(converted, tgt)

    def convert_money(self, money: Money, target_currency: str) -> Money:
        """Convert a :class:`Money` instance to *target_currency*."""
        return self.convert(money, target_currency)
