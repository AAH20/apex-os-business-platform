"""Tests for the deepened accounting module."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apex_os_bp.accounting import (
    Account,
    AccountType,
    BalanceSheet,
    CashFlowStatement,
    Currency,
    CurrencyConverter,
    ExchangeRate,
    Invoice,
    InvoiceLineItem,
    JournalEntry,
    Money,
    Payment,
    PaymentMethod,
    ProfitAndLoss,
    ReconciliationEngine,
    ReconciliationReport,
    ReconciliationResult,
    ReconciliationStatus,
    RecurrencePattern,
    RecurringInvoiceTemplate,
    RecurringInvoiceScheduler,
    ReportGenerator,
    ReportLineItem,
    ReportPeriod,
    TaxEngine,
    TaxLineItem,
    TaxRate,
    TaxRule,
    TaxType,
    Transaction,
)


# ===================================================================
# Multi-currency support
# ===================================================================


class TestCurrency:
    """Tests for the Currency enum."""

    def test_currency_codes(self) -> None:
        assert Currency.USD.value == "USD"
        assert Currency.EUR.value == "EUR"
        assert Currency.GBP.value == "GBP"

    def test_currency_from_string(self) -> None:
        assert Currency("USD") == Currency.USD
        assert Currency("EUR") == Currency.EUR


class TestExchangeRate:
    """Tests for ExchangeRate."""

    def test_create_rate(self) -> None:
        rate = ExchangeRate(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal("0.85"),
        )
        assert rate.base_currency == "USD"
        assert rate.quote_currency == "EUR"
        assert rate.rate == Decimal("0.85")

    def test_same_currency_raises(self) -> None:
        with pytest.raises(ValueError, match="must differ"):
            ExchangeRate(
                base_currency="USD",
                quote_currency="USD",
                rate=Decimal("1.0"),
            )

    def test_negative_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            ExchangeRate(
                base_currency="USD",
                quote_currency="EUR",
                rate=Decimal("-0.5"),
            )

    def test_inverse(self) -> None:
        rate = ExchangeRate(
            base_currency="USD",
            quote_currency="EUR",
            rate=Decimal("0.85"),
        )
        inv = rate.inverse()
        assert inv.base_currency == "EUR"
        assert inv.quote_currency == "USD"
        assert inv.rate == Decimal("1") / Decimal("0.85")


class TestMoney:
    """Tests for the Money type."""

    def test_create_money(self) -> None:
        m = Money(Decimal("100.50"), "USD")
        assert m.amount == Decimal("100.50")
        assert m.currency == "USD"

    def test_money_from_int(self) -> None:
        m = Money(100, "USD")
        assert m.amount == Decimal("100.00")

    def test_add_same_currency(self) -> None:
        a = Money(Decimal("50"), "USD")
        b = Money(Decimal("30"), "USD")
        result = a + b
        assert result.amount == Decimal("80.00")
        assert result.currency == "USD"

    def test_add_different_currency_raises(self) -> None:
        a = Money(Decimal("50"), "USD")
        b = Money(Decimal("30"), "EUR")
        with pytest.raises(ValueError, match="without conversion"):
            _ = a + b

    def test_sub_same_currency(self) -> None:
        a = Money(Decimal("50"), "USD")
        b = Money(Decimal("30"), "USD")
        result = a - b
        assert result.amount == Decimal("20.00")

    def test_sub_different_currency_raises(self) -> None:
        a = Money(Decimal("50"), "USD")
        b = Money(Decimal("30"), "EUR")
        with pytest.raises(ValueError, match="without conversion"):
            _ = a - b

    def test_neg(self) -> None:
        m = Money(Decimal("50"), "USD")
        assert (-m).amount == Decimal("-50.00")

    def test_abs(self) -> None:
        m = Money(Decimal("-50"), "USD")
        assert abs(m).amount == Decimal("50.00")

    def test_comparison_same_currency(self) -> None:
        a = Money(Decimal("50"), "USD")
        b = Money(Decimal("100"), "USD")
        assert a < b
        assert b > a
        assert a <= b
        assert b >= a
        assert a != b

    def test_comparison_different_currency_raises(self) -> None:
        a = Money(Decimal("50"), "USD")
        b = Money(Decimal("100"), "EUR")
        with pytest.raises(ValueError, match="Cannot compare"):
            _ = a < b

    def test_equality(self) -> None:
        a = Money(Decimal("50"), "USD")
        b = Money(Decimal("50.00"), "USD")
        assert a == b

    def test_inequality_currency(self) -> None:
        a = Money(Decimal("50"), "USD")
        b = Money(Decimal("50"), "EUR")
        assert a != b

    def test_hash(self) -> None:
        a = Money(Decimal("50"), "USD")
        b = Money(Decimal("50.00"), "USD")
        assert hash(a) == hash(b)

    def test_str(self) -> None:
        m = Money(Decimal("100.50"), "USD")
        assert str(m) == "100.50 USD"

    def test_convert_to(self) -> None:
        m = Money(Decimal("100"), "USD")
        result = m.convert_to("EUR", Decimal("0.85"))
        assert result.amount == Decimal("85.00")
        assert result.currency == "EUR"

    def test_convert_to_same_currency(self) -> None:
        m = Money(Decimal("100"), "USD")
        result = m.convert_to("USD", Decimal("1.0"))
        assert result.amount == Decimal("100.00")
        assert result.currency == "USD"

    def test_convert_to_zero_rate_raises(self) -> None:
        m = Money(Decimal("100"), "USD")
        with pytest.raises(ValueError, match="positive"):
            m.convert_to("EUR", Decimal("0"))

    def test_jpy_precision(self) -> None:
        m = Money(Decimal("100.5"), "JPY")
        assert m.amount == Decimal("101")  # rounded to 0 decimal places


class TestCurrencyConverter:
    """Tests for CurrencyConverter."""

    def test_add_and_get_rate(self) -> None:
        conv = CurrencyConverter()
        conv.add_rate_from_values("USD", "EUR", "0.85")
        rate = conv.get_rate("USD", "EUR")
        assert rate.rate == Decimal("0.85")

    def test_inverse_rate_auto_registered(self) -> None:
        conv = CurrencyConverter()
        conv.add_rate_from_values("USD", "EUR", "0.85")
        inv = conv.get_rate("EUR", "USD")
        assert inv.rate == Decimal("1") / Decimal("0.85")

    def test_has_rate(self) -> None:
        conv = CurrencyConverter()
        conv.add_rate_from_values("USD", "EUR", "0.85")
        assert conv.has_rate("USD", "EUR")
        assert conv.has_rate("EUR", "USD")
        assert not conv.has_rate("USD", "GBP")

    def test_get_missing_rate_raises(self) -> None:
        conv = CurrencyConverter()
        with pytest.raises(KeyError):
            conv.get_rate("USD", "GBP")

    def test_convert_amount(self) -> None:
        conv = CurrencyConverter()
        conv.add_rate_from_values("USD", "EUR", "0.85")
        result = conv.convert(Decimal("100"), "EUR", "USD")
        assert result.amount == Decimal("85.00")
        assert result.currency == "EUR"

    def test_convert_money(self) -> None:
        conv = CurrencyConverter()
        conv.add_rate_from_values("USD", "EUR", "0.85")
        m = Money(Decimal("100"), "USD")
        result = conv.convert(m, "EUR")
        assert result.amount == Decimal("85.00")

    def test_convert_same_currency(self) -> None:
        conv = CurrencyConverter()
        result = conv.convert(Decimal("100"), "USD", "USD")
        assert result.amount == Decimal("100.00")

    def test_convert_without_source_currency_raises(self) -> None:
        conv = CurrencyConverter()
        with pytest.raises(ValueError, match="source_currency"):
            conv.convert(Decimal("100"), "EUR")

    def test_remove_rate(self) -> None:
        conv = CurrencyConverter()
        conv.add_rate_from_values("USD", "EUR", "0.85")
        conv.remove_rate("USD", "EUR")
        assert not conv.has_rate("USD", "EUR")
        assert not conv.has_rate("EUR", "USD")

    def test_available_currencies(self) -> None:
        conv = CurrencyConverter()
        conv.add_rate_from_values("USD", "EUR", "0.85")
        conv.add_rate_from_values("USD", "GBP", "0.73")
        currencies = conv.available_currencies
        assert "USD" in currencies
        assert "EUR" in currencies
        assert "GBP" in currencies


# ===================================================================
# Tax calculation engine
# ===================================================================


class TestTaxRate:
    """Tests for TaxRate."""

    def test_create_rate(self) -> None:
        rate = TaxRate(
            name="VAT 20%",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
        )
        assert rate.name == "VAT 20%"
        assert rate.rate == Decimal("20")
        assert rate.tax_type == TaxType.VAT
        assert rate.jurisdiction == "UK"

    def test_negative_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            TaxRate(
                name="Bad",
                rate=Decimal("-5"),
                tax_type=TaxType.VAT,
                jurisdiction="UK",
            )

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="name"):
            TaxRate(
                name="",
                rate=Decimal("20"),
                tax_type=TaxType.VAT,
                jurisdiction="UK",
            )

    def test_empty_jurisdiction_raises(self) -> None:
        with pytest.raises(ValueError, match="Jurisdiction"):
            TaxRate(
                name="VAT",
                rate=Decimal("20"),
                tax_type=TaxType.VAT,
                jurisdiction="",
            )

    def test_is_effective_on(self) -> None:
        rate = TaxRate(
            name="VAT 20%",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
            effective_from=date(2024, 1, 1),
            effective_to=date(2024, 12, 31),
        )
        assert rate.is_effective_on(date(2024, 6, 15))
        assert not rate.is_effective_on(date(2023, 12, 31))
        assert not rate.is_effective_on(date(2025, 1, 1))

    def test_is_effective_on_inactive(self) -> None:
        rate = TaxRate(
            name="VAT 20%",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
            is_active=False,
        )
        assert not rate.is_effective_on(date(2024, 6, 15))

    def test_apply(self) -> None:
        rate = TaxRate(
            name="VAT 20%",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
        )
        assert rate.apply(Decimal("100")) == Decimal("20.00")
        assert rate.apply(Decimal("50.50")) == Decimal("10.10")


class TestTaxRule:
    """Tests for TaxRule."""

    def _make_rate(self) -> TaxRate:
        return TaxRate(
            name="VAT 20%",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
        )

    def test_matches_no_filters(self) -> None:
        rule = TaxRule(name="Standard", tax_rate=self._make_rate())
        assert rule.matches(Decimal("100"))

    def test_matches_product_category(self) -> None:
        rule = TaxRule(
            name="Food",
            tax_rate=self._make_rate(),
            product_category="food",
        )
        assert rule.matches(Decimal("100"), product_category="food")
        assert not rule.matches(Decimal("100"), product_category="electronics")

    def test_matches_customer_category(self) -> None:
        rule = TaxRule(
            name="Wholesale",
            tax_rate=self._make_rate(),
            customer_category="wholesale",
        )
        assert rule.matches(Decimal("100"), customer_category="wholesale")
        assert not rule.matches(Decimal("100"), customer_category="retail")

    def test_matches_amount_range(self) -> None:
        rule = TaxRule(
            name="Luxury",
            tax_rate=self._make_rate(),
            min_amount=Decimal("1000"),
            max_amount=Decimal("10000"),
        )
        assert rule.matches(Decimal("5000"))
        assert not rule.matches(Decimal("500"))
        assert not rule.matches(Decimal("20000"))

    def test_inactive_rule_does_not_match(self) -> None:
        rule = TaxRule(
            name="Inactive",
            tax_rate=self._make_rate(),
            is_active=False,
        )
        assert not rule.matches(Decimal("100"))


class TestTaxLineItem:
    """Tests for TaxLineItem."""

    def test_total_with_tax(self) -> None:
        item = TaxLineItem(
            line_description="Test",
            taxable_amount=Decimal("100"),
            tax_rate=Decimal("20"),
            tax_amount=Decimal("20"),
        )
        assert item.total_with_tax == Decimal("120")


class TestTaxEngine:
    """Tests for TaxEngine."""

    def _make_engine(self) -> TaxEngine:
        engine = TaxEngine()
        engine.register_rate(TaxRate(
            name="VAT 20%",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
        ))
        engine.register_rate(TaxRate(
            name="Sales Tax 8%",
            rate=Decimal("8"),
            tax_type=TaxType.SALES_TAX,
            jurisdiction="US-CA",
        ))
        return engine

    def test_register_and_get_rate(self) -> None:
        engine = self._make_engine()
        rates = engine.rates
        assert len(rates) == 2
        rate = engine.get_rate(rates[0].rate_id)
        assert rate.name in ("VAT 20%", "Sales Tax 8%")

    def test_get_missing_rate_raises(self) -> None:
        engine = TaxEngine()
        with pytest.raises(KeyError):
            engine.get_rate("nonexistent")

    def test_find_rates_by_jurisdiction(self) -> None:
        engine = self._make_engine()
        rates = engine.find_rates(jurisdiction="UK")
        assert len(rates) == 1
        assert rates[0].name == "VAT 20%"

    def test_find_rates_by_type(self) -> None:
        engine = self._make_engine()
        rates = engine.find_rates(tax_type=TaxType.SALES_TAX)
        assert len(rates) == 1
        assert rates[0].name == "Sales Tax 8%"

    def test_find_rates_by_date(self) -> None:
        engine = TaxEngine()
        engine.register_rate(TaxRate(
            name="Old VAT",
            rate=Decimal("17.5"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
            effective_from=date(2020, 1, 1),
            effective_to=date(2020, 12, 31),
        ))
        engine.register_rate(TaxRate(
            name="New VAT",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
            effective_from=date(2021, 1, 1),
        ))
        rates_2020 = engine.find_rates(jurisdiction="UK", on_date=date(2020, 6, 1))
        assert len(rates_2020) == 1
        assert rates_2020[0].name == "Old VAT"
        rates_2022 = engine.find_rates(jurisdiction="UK", on_date=date(2022, 1, 1))
        assert len(rates_2022) == 1
        assert rates_2022[0].name == "New VAT"

    def test_calculate_tax(self) -> None:
        engine = self._make_engine()
        vat_rate = next(r for r in engine.rates if r.name == "VAT 20%")
        result = engine.calculate_tax(Decimal("100"), vat_rate.rate_id)
        assert result.taxable_amount == Decimal("100")
        assert result.tax_amount == Decimal("20.00")
        assert result.tax_rate == Decimal("20")
        assert result.total_with_tax == Decimal("120.00")

    def test_calculate_total_tax(self) -> None:
        engine = self._make_engine()
        vat_rate = next(r for r in engine.rates if r.name == "VAT 20%")
        assert engine.calculate_total_tax(Decimal("200"), vat_rate.rate_id) == Decimal("40.00")

    def test_calculate_with_tax(self) -> None:
        engine = self._make_engine()
        vat_rate = next(r for r in engine.rates if r.name == "VAT 20%")
        assert engine.calculate_with_tax(Decimal("100"), vat_rate.rate_id) == Decimal("120.00")

    def test_reverse_calculate(self) -> None:
        engine = self._make_engine()
        vat_rate = next(r for r in engine.rates if r.name == "VAT 20%")
        net, tax = engine.reverse_calculate(Decimal("120"), vat_rate.rate_id)
        assert net == Decimal("100.00")
        assert tax == Decimal("20.00")

    def test_calculate_with_rules(self) -> None:
        engine = TaxEngine()
        rate = TaxRate(
            name="VAT 20%",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
        )
        engine.register_rate(rate)
        engine.register_rule(TaxRule(
            name="Standard",
            tax_rate=rate,
            product_category="general",
        ))
        results = engine.calculate_with_rules(
            Decimal("100"),
            product_category="general",
        )
        assert len(results) == 1
        assert results[0].tax_amount == Decimal("20.00")

    def test_calculate_with_rules_no_match(self) -> None:
        engine = TaxEngine()
        rate = TaxRate(
            name="VAT 20%",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
        )
        engine.register_rate(rate)
        engine.register_rule(TaxRule(
            name="Food only",
            tax_rate=rate,
            product_category="food",
        ))
        results = engine.calculate_with_rules(
            Decimal("100"),
            product_category="electronics",
        )
        assert len(results) == 0

    def test_remove_rate(self) -> None:
        engine = self._make_engine()
        rate = engine.rates[0]
        engine.remove_rate(rate.rate_id)
        assert len(engine.rates) == 1

    def test_remove_rule(self) -> None:
        engine = TaxEngine()
        rate = TaxRate(
            name="VAT 20%",
            rate=Decimal("20"),
            tax_type=TaxType.VAT,
            jurisdiction="UK",
        )
        engine.register_rate(rate)
        rule = TaxRule(name="Standard", tax_rate=rate)
        engine.register_rule(rule)
        assert len(engine.rules) == 1
        engine.remove_rule(rule.rule_id)
        assert len(engine.rules) == 0


# ===================================================================
# Recurring invoice scheduler
# ===================================================================


class TestRecurringInvoiceTemplate:
    """Tests for RecurringInvoiceTemplate."""

    def _make_line_items(self) -> list[InvoiceLineItem]:
        return [
            InvoiceLineItem(
                description="Consulting",
                quantity=Decimal("10"),
                unit_price=Decimal("100"),
            )
        ]

    def test_create_template(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.MONTHLY,
        )
        assert template.customer_id == "cust-1"
        assert template.pattern == RecurrencePattern.MONTHLY
        assert template.is_active is True

    def test_empty_customer_raises(self) -> None:
        with pytest.raises(ValueError, match="customer_id"):
            RecurringInvoiceTemplate(
                customer_id="",
                line_items=self._make_line_items(),
                pattern=RecurrencePattern.MONTHLY,
            )

    def test_empty_line_items_raises(self) -> None:
        with pytest.raises(ValueError, match="line item"):
            RecurringInvoiceTemplate(
                customer_id="cust-1",
                line_items=[],
                pattern=RecurrencePattern.MONTHLY,
            )

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="end_date"):
            RecurringInvoiceTemplate(
                customer_id="cust-1",
                line_items=self._make_line_items(),
                pattern=RecurrencePattern.MONTHLY,
                start_date=date(2024, 6, 1),
                end_date=date(2024, 1, 1),
            )

    def test_max_occurrences_validation(self) -> None:
        with pytest.raises(ValueError, match="max_occurrences"):
            RecurringInvoiceTemplate(
                customer_id="cust-1",
                line_items=self._make_line_items(),
                pattern=RecurrencePattern.MONTHLY,
                max_occurrences=0,
            )

    def test_day_of_month_validation(self) -> None:
        with pytest.raises(ValueError, match="day_of_month"):
            RecurringInvoiceTemplate(
                customer_id="cust-1",
                line_items=self._make_line_items(),
                pattern=RecurrencePattern.MONTHLY,
                day_of_month=32,
            )

    def test_next_occurrence_monthly(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.MONTHLY,
            start_date=date(2024, 1, 15),
        )
        assert template.next_occurrence(date(2024, 1, 14)) == date(2024, 1, 15)
        assert template.next_occurrence(date(2024, 1, 15)) == date(2024, 2, 15)
        assert template.next_occurrence(date(2024, 2, 15)) == date(2024, 3, 15)

    def test_next_occurrence_weekly(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.WEEKLY,
            start_date=date(2024, 1, 1),
        )
        assert template.next_occurrence(date(2024, 1, 1)) == date(2024, 1, 8)
        assert template.next_occurrence(date(2024, 1, 8)) == date(2024, 1, 15)

    def test_next_occurrence_daily(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.DAILY,
            start_date=date(2024, 1, 1),
        )
        assert template.next_occurrence(date(2024, 1, 1)) == date(2024, 1, 2)

    def test_next_occurrence_biweekly(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.BIWEEKLY,
            start_date=date(2024, 1, 1),
        )
        assert template.next_occurrence(date(2024, 1, 1)) == date(2024, 1, 15)

    def test_next_occurrence_quarterly(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.QUARTERLY,
            start_date=date(2024, 1, 1),
        )
        assert template.next_occurrence(date(2024, 1, 1)) == date(2024, 4, 1)

    def test_next_occurrence_yearly(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.YEARLY,
            start_date=date(2024, 1, 1),
        )
        assert template.next_occurrence(date(2024, 1, 1)) == date(2025, 1, 1)

    def test_next_occurrence_after_end_date(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.MONTHLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 1),
        )
        assert template.next_occurrence(date(2024, 3, 1)) is None

    def test_next_occurrence_inactive(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.MONTHLY,
            start_date=date(2024, 1, 1),
            is_active=False,
        )
        assert template.next_occurrence(date(2024, 1, 1)) is None

    def test_occurrences_between(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.MONTHLY,
            start_date=date(2024, 1, 1),
        )
        occurrences = template.occurrences_between(date(2024, 1, 1), date(2024, 4, 1))
        assert occurrences == [
            date(2024, 1, 1),
            date(2024, 2, 1),
            date(2024, 3, 1),
            date(2024, 4, 1),
        ]

    def test_occurrences_between_with_max(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.MONTHLY,
            start_date=date(2024, 1, 1),
            max_occurrences=2,
        )
        occurrences = template.occurrences_between(date(2024, 1, 1), date(2024, 12, 1))
        assert occurrences == [date(2024, 1, 1), date(2024, 2, 1)]

    def test_occurrences_between_inactive(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.MONTHLY,
            start_date=date(2024, 1, 1),
            is_active=False,
        )
        assert template.occurrences_between(date(2024, 1, 1), date(2024, 12, 1)) == []

    def test_month_end_clamping(self) -> None:
        template = RecurringInvoiceTemplate(
            customer_id="cust-1",
            line_items=self._make_line_items(),
            pattern=RecurrencePattern.MONTHLY,
            start_date=date(2024, 1, 31),
        )
        # Feb has 29 days in 2024 (leap year)
        assert template.next_occurrence(date(2024, 1, 31)) == date(2024, 2, 29)


class TestRecurringInvoiceScheduler:
    """Tests for RecurringInvoiceScheduler."""

    def _make_template(self, **kwargs: object) -> RecurringInvoiceTemplate:
        defaults: dict[str, object] = {
            "customer_id": "cust-1",
            "line_items": [
                InvoiceLineItem(
                    description="Service",
                    quantity=Decimal("1"),
                    unit_price=Decimal("500"),
                )
            ],
            "pattern": RecurrencePattern.MONTHLY,
            "start_date": date(2024, 1, 1),
        }
        defaults.update(kwargs)
        return RecurringInvoiceTemplate(**defaults)  # type: ignore[arg-type]

    def test_add_and_get_template(self) -> None:
        scheduler = RecurringInvoiceScheduler()
        template = self._make_template()
        scheduler.add_template(template)
        assert scheduler.get_template(template.template_id).customer_id == "cust-1"

    def test_get_missing_template_raises(self) -> None:
        scheduler = RecurringInvoiceScheduler()
        with pytest.raises(KeyError):
            scheduler.get_template("nonexistent")

    def test_remove_template(self) -> None:
        scheduler = RecurringInvoiceScheduler()
        template = self._make_template()
        scheduler.add_template(template)
        scheduler.remove_template(template.template_id)
        assert scheduler.templates == []

    def test_generate_invoice(self) -> None:
        scheduler = RecurringInvoiceScheduler()
        template = self._make_template()
        scheduler.add_template(template)
        invoice = scheduler.generate_invoice(template.template_id, date(2024, 3, 15))
        assert invoice.customer_id == "cust-1"
        assert invoice.issue_date == date(2024, 3, 15)
        assert invoice.total == Decimal("500.00")
        assert invoice.status == "draft"

    def test_generate_up_to(self) -> None:
        scheduler = RecurringInvoiceScheduler()
        template = self._make_template()
        scheduler.add_template(template)
        invoices = scheduler.generate_up_to(template.template_id, date(2024, 4, 1))
        assert len(invoices) == 4
        assert invoices[0].issue_date == date(2024, 1, 1)
        assert invoices[3].issue_date == date(2024, 4, 1)

    def test_generate_all_up_to(self) -> None:
        scheduler = RecurringInvoiceScheduler()
        scheduler.add_template(self._make_template(
            customer_id="cust-1",
            pattern=RecurrencePattern.MONTHLY,
            start_date=date(2024, 1, 1),
        ))
        scheduler.add_template(self._make_template(
            customer_id="cust-2",
            pattern=RecurrencePattern.WEEKLY,
            start_date=date(2024, 1, 1),
        ))
        invoices = scheduler.generate_all_up_to(date(2024, 1, 31))
        # Monthly: 1, Weekly: 5 (Jan 1, 8, 15, 22, 29)
        assert len(invoices) == 6

    def test_generate_all_skips_inactive(self) -> None:
        scheduler = RecurringInvoiceScheduler()
        scheduler.add_template(self._make_template(
            customer_id="cust-1",
            pattern=RecurrencePattern.MONTHLY,
            start_date=date(2024, 1, 1),
            is_active=False,
        ))
        invoices = scheduler.generate_all_up_to(date(2024, 12, 31))
        assert len(invoices) == 0


# ===================================================================
# Payment reconciliation
# ===================================================================


class TestPayment:
    """Tests for Payment."""

    def test_create_payment(self) -> None:
        payment = Payment(
            amount=Decimal("100"),
            currency="USD",
            payment_method=PaymentMethod.BANK_TRANSFER,
        )
        assert payment.amount == Decimal("100")
        assert payment.currency == "USD"
        assert payment.payment_method == PaymentMethod.BANK_TRANSFER
        assert payment.is_reconciled is False

    def test_zero_amount_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Payment(
                amount=Decimal("0"),
                currency="USD",
                payment_method=PaymentMethod.CASH,
            )

    def test_negative_amount_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            Payment(
                amount=Decimal("-50"),
                currency="USD",
                payment_method=PaymentMethod.CASH,
            )


class TestReconciliationResult:
    """Tests for ReconciliationResult."""

    def test_is_fully_reconciled(self) -> None:
        payment = Payment(
            amount=Decimal("100"),
            currency="USD",
            payment_method=PaymentMethod.BANK_TRANSFER,
        )
        result = ReconciliationResult(
            payment=payment,
            invoice=None,
            status=ReconciliationStatus.MATCHED,
            matched_amount=Decimal("100"),
            difference=Decimal("0"),
        )
        assert result.is_fully_reconciled is True

    def test_is_not_fully_reconciled(self) -> None:
        payment = Payment(
            amount=Decimal("50"),
            currency="USD",
            payment_method=PaymentMethod.BANK_TRANSFER,
        )
        result = ReconciliationResult(
            payment=payment,
            invoice=None,
            status=ReconciliationStatus.PARTIAL,
            matched_amount=Decimal("50"),
            difference=Decimal("-50"),
        )
        assert result.is_fully_reconciled is False


class TestReconciliationReport:
    """Tests for ReconciliationReport."""

    def _make_payment(self, amount: str, currency: str = "USD") -> Payment:
        return Payment(
            amount=Decimal(amount),
            currency=currency,
            payment_method=PaymentMethod.BANK_TRANSFER,
        )

    def _make_result(
        self,
        payment: Payment,
        status: ReconciliationStatus,
        matched: str,
        diff: str,
    ) -> ReconciliationResult:
        return ReconciliationResult(
            payment=payment,
            invoice=None,
            status=status,
            matched_amount=Decimal(matched),
            difference=Decimal(diff),
        )

    def test_counts(self) -> None:
        p1 = self._make_payment("100")
        p2 = self._make_payment("50")
        p3 = self._make_payment("200")
        p4 = self._make_payment("75")
        report = ReconciliationReport(results=[
            self._make_result(p1, ReconciliationStatus.MATCHED, "100", "0"),
            self._make_result(p2, ReconciliationStatus.PARTIAL, "50", "-50"),
            self._make_result(p3, ReconciliationStatus.OVERPAYMENT, "100", "100"),
            self._make_result(p4, ReconciliationStatus.UNMATCHED, "0", "75"),
        ])
        assert report.total_payments == 4
        assert report.matched_count == 1
        assert report.partial_count == 1
        assert report.overpayment_count == 1
        assert report.unmatched_count == 1

    def test_total_matched_amount(self) -> None:
        p1 = self._make_payment("100")
        p2 = self._make_payment("50")
        report = ReconciliationReport(results=[
            self._make_result(p1, ReconciliationStatus.MATCHED, "100", "0"),
            self._make_result(p2, ReconciliationStatus.PARTIAL, "50", "-50"),
        ])
        assert report.total_matched_amount == Decimal("150")

    def test_total_difference(self) -> None:
        p1 = self._make_payment("100")
        p2 = self._make_payment("150")
        report = ReconciliationReport(results=[
            self._make_result(p1, ReconciliationStatus.PARTIAL, "100", "-50"),
            self._make_result(p2, ReconciliationStatus.OVERPAYMENT, "100", "50"),
        ])
        assert report.total_difference == Decimal("100")

    def test_reconciliation_rate(self) -> None:
        p1 = self._make_payment("100")
        p2 = self._make_payment("50")
        report = ReconciliationReport(results=[
            self._make_result(p1, ReconciliationStatus.MATCHED, "100", "0"),
            self._make_result(p2, ReconciliationStatus.UNMATCHED, "0", "50"),
        ])
        assert report.reconciliation_rate == 0.5

    def test_reconciliation_rate_empty(self) -> None:
        report = ReconciliationReport(results=[])
        assert report.reconciliation_rate == 0.0

    def test_unmatched_payments(self) -> None:
        p1 = self._make_payment("100")
        p2 = self._make_payment("50")
        report = ReconciliationReport(results=[
            self._make_result(p1, ReconciliationStatus.MATCHED, "100", "0"),
            self._make_result(p2, ReconciliationStatus.UNMATCHED, "0", "50"),
        ])
        unmatched = report.unmatched_payments()
        assert len(unmatched) == 1
        assert unmatched[0].amount == Decimal("50")


class TestReconciliationEngine:
    """Tests for ReconciliationEngine."""

    def _make_invoice(
        self,
        total: str,
        currency: str = "USD",
        status: str = "sent",
    ) -> Invoice:
        return Invoice(
            customer_id="cust-1",
            line_items=[
                InvoiceLineItem(
                    description="Test",
                    quantity=Decimal("1"),
                    unit_price=Decimal(total),
                )
            ],
            currency=currency,
            status=status,
        )

    def _make_payment(
        self,
        amount: str,
        currency: str = "USD",
        invoice_id: str | None = None,
        reference: str | None = None,
    ) -> Payment:
        return Payment(
            amount=Decimal(amount),
            currency=currency,
            payment_method=PaymentMethod.BANK_TRANSFER,
            invoice_id=invoice_id,
            reference=reference,
        )

    def test_match_by_invoice_id_exact(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("100", invoice_id=invoice.invoice_id)
        result = engine.match_by_invoice_id(payment)
        assert result.status == ReconciliationStatus.MATCHED
        assert result.matched_amount == Decimal("100")
        assert result.difference == Decimal("0")

    def test_match_by_invoice_id_partial(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("60", invoice_id=invoice.invoice_id)
        result = engine.match_by_invoice_id(payment)
        assert result.status == ReconciliationStatus.PARTIAL
        assert result.matched_amount == Decimal("60")
        assert result.difference == Decimal("-40")

    def test_match_by_invoice_id_overpayment(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("150", invoice_id=invoice.invoice_id)
        result = engine.match_by_invoice_id(payment)
        assert result.status == ReconciliationStatus.OVERPAYMENT
        assert result.matched_amount == Decimal("100")
        assert result.difference == Decimal("50")

    def test_match_by_invoice_id_not_found(self) -> None:
        engine = ReconciliationEngine()
        payment = self._make_payment("100", invoice_id="nonexistent")
        result = engine.match_by_invoice_id(payment)
        assert result.status == ReconciliationStatus.UNMATCHED

    def test_match_by_invoice_id_no_id(self) -> None:
        engine = ReconciliationEngine()
        payment = self._make_payment("100")
        result = engine.match_by_invoice_id(payment)
        assert result.status == ReconciliationStatus.UNMATCHED

    def test_match_by_reference(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("100", reference=invoice.invoice_id)
        result = engine.match_by_reference(payment)
        assert result.status == ReconciliationStatus.MATCHED

    def test_match_by_reference_not_found(self) -> None:
        engine = ReconciliationEngine()
        payment = self._make_payment("100", reference="nonexistent")
        result = engine.match_by_reference(payment)
        assert result.status == ReconciliationStatus.UNMATCHED

    def test_match_by_amount(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("100")
        result = engine.match_by_amount(payment)
        assert result.status == ReconciliationStatus.MATCHED

    def test_match_by_amount_no_match(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("200")
        result = engine.match_by_amount(payment)
        assert result.status == ReconciliationStatus.UNMATCHED

    def test_match_by_amount_skips_paid(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100", status="paid")
        engine.register_invoice(invoice)
        payment = self._make_payment("100")
        result = engine.match_by_amount(payment)
        assert result.status == ReconciliationStatus.UNMATCHED

    def test_auto_match_by_invoice_id(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("100", invoice_id=invoice.invoice_id)
        result = engine.auto_match(payment)
        assert result.status == ReconciliationStatus.MATCHED

    def test_auto_match_by_amount_fallback(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("100")
        result = engine.auto_match(payment)
        assert result.status == ReconciliationStatus.MATCHED

    def test_auto_match_unmatched(self) -> None:
        engine = ReconciliationEngine()
        payment = self._make_payment("100")
        result = engine.auto_match(payment)
        assert result.status == ReconciliationStatus.UNMATCHED

    def test_currency_mismatch(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100", currency="EUR")
        engine.register_invoice(invoice)
        payment = self._make_payment("100", currency="USD", invoice_id=invoice.invoice_id)
        result = engine.match_by_invoice_id(payment)
        assert result.status == ReconciliationStatus.DISCREPANCY

    def test_reconcile_all(self) -> None:
        engine = ReconciliationEngine()
        inv1 = self._make_invoice("100")
        inv2 = self._make_invoice("200")
        engine.register_invoices([inv1, inv2])
        p1 = self._make_payment("100", invoice_id=inv1.invoice_id)
        p2 = self._make_payment("200", invoice_id=inv2.invoice_id)
        p3 = self._make_payment("50")
        engine.register_payments([p1, p2, p3])
        report = engine.reconcile_all()
        assert report.matched_count == 2
        assert report.unmatched_count == 1
        assert p1.is_reconciled is True
        assert p2.is_reconciled is True
        assert p3.is_reconciled is False

    def test_reconcile_payment_by_id(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("100", invoice_id=invoice.invoice_id)
        engine.register_payment(payment)
        result = engine.reconcile_payment(payment.payment_id)
        assert result.status == ReconciliationStatus.MATCHED
        assert payment.is_reconciled is True

    def test_reconcile_missing_payment_raises(self) -> None:
        engine = ReconciliationEngine()
        with pytest.raises(KeyError):
            engine.reconcile_payment("nonexistent")

    def test_unreconciled_payments(self) -> None:
        engine = ReconciliationEngine()
        p1 = self._make_payment("100")
        p2 = self._make_payment("200")
        engine.register_payments([p1, p2])
        assert len(engine.unreconciled_payments) == 2
        # Reconcile p1
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        p1.invoice_id = invoice.invoice_id
        engine.reconcile_payment(p1.payment_id)
        assert len(engine.unreconciled_payments) == 1
        assert engine.unreconciled_payments[0].payment_id == p2.payment_id

    def test_reconciled_payments(self) -> None:
        engine = ReconciliationEngine()
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        p1 = self._make_payment("100", invoice_id=invoice.invoice_id)
        engine.register_payment(p1)
        engine.reconcile_payment(p1.payment_id)
        assert len(engine.reconciled_payments) == 1

    def test_tolerance(self) -> None:
        engine = ReconciliationEngine(tolerance=Decimal("0.05"))
        invoice = self._make_invoice("100")
        engine.register_invoice(invoice)
        payment = self._make_payment("100.03", invoice_id=invoice.invoice_id)
        result = engine.match_by_invoice_id(payment)
        assert result.status == ReconciliationStatus.MATCHED


# ===================================================================
# Financial reporting
# ===================================================================


class TestReportPeriod:
    """Tests for ReportPeriod."""

    def test_create_period(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 12, 31)

    def test_start_after_end_raises(self) -> None:
        with pytest.raises(ValueError, match="start_date"):
            ReportPeriod(
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),
            )

    def test_contains(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert period.contains(date(2024, 6, 15))
        assert period.contains(date(2024, 1, 1))
        assert period.contains(date(2024, 12, 31))
        assert not period.contains(date(2023, 12, 31))
        assert not period.contains(date(2025, 1, 1))

    def test_display_label_default(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert "2024-01-01" in period.display_label
        assert "2024-12-31" in period.display_label

    def test_display_label_custom(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            label="FY2024",
        )
        assert period.display_label == "FY2024"


class TestReportLineItem:
    """Tests for ReportLineItem."""

    def test_create(self) -> None:
        item = ReportLineItem(
            account_id="REV-001",
            account_name="Sales",
            amount=Decimal("1000"),
        )
        assert item.account_id == "REV-001"
        assert item.account_name == "Sales"
        assert item.amount == Decimal("1000")


class TestProfitAndLoss:
    """Tests for ProfitAndLoss."""

    def _make_pl(self) -> ProfitAndLoss:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        return ProfitAndLoss(
            period=period,
            line_items=[
                ReportLineItem("REV-001", "Sales", Decimal("10000")),
                ReportLineItem("EXP-001", "Rent", Decimal("-3000")),
                ReportLineItem("EXP-002", "Salaries", Decimal("-5000")),
            ],
        )

    def test_total_revenue(self) -> None:
        pl = self._make_pl()
        assert pl.total_revenue == Decimal("10000")

    def test_total_expenses(self) -> None:
        pl = self._make_pl()
        assert pl.total_expenses == Decimal("8000")

    def test_net_income(self) -> None:
        pl = self._make_pl()
        assert pl.net_income == Decimal("2000")

    def test_is_profitable(self) -> None:
        pl = self._make_pl()
        assert pl.is_profitable is True

    def test_is_not_profitable(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        pl = ProfitAndLoss(
            period=period,
            line_items=[
                ReportLineItem("REV-001", "Sales", Decimal("5000")),
                ReportLineItem("EXP-001", "Rent", Decimal("-8000")),
            ],
        )
        assert pl.is_profitable is False

    def test_profit_margin(self) -> None:
        pl = self._make_pl()
        assert pl.profit_margin == Decimal("20.00")

    def test_profit_margin_no_revenue(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        pl = ProfitAndLoss(period=period, line_items=[])
        assert pl.profit_margin is None

    def test_gross_profit(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        pl = ProfitAndLoss(
            period=period,
            line_items=[
                ReportLineItem("REV-001", "Sales", Decimal("10000")),
                ReportLineItem("COGS-001", "COGS", Decimal("-4000")),
            ],
        )
        assert pl.gross_profit == Decimal("6000")


class TestBalanceSheet:
    """Tests for BalanceSheet."""

    def _make_bs(self) -> BalanceSheet:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        return BalanceSheet(
            period=period,
            line_items=[
                ReportLineItem("AST-001", "Cash", Decimal("50000")),
                ReportLineItem("AST-002", "AR", Decimal("10000")),
                ReportLineItem("LIA-001", "AP", Decimal("-15000")),
                ReportLineItem("LIA-002", "Loans", Decimal("-20000")),
                ReportLineItem("EQY-001", "Equity", Decimal("25000")),
            ],
        )

    def test_total_assets(self) -> None:
        bs = self._make_bs()
        assert bs.total_assets == Decimal("60000")

    def test_total_liabilities(self) -> None:
        bs = self._make_bs()
        assert bs.total_liabilities == Decimal("35000")

    def test_total_equity(self) -> None:
        bs = self._make_bs()
        assert bs.total_equity == Decimal("25000")

    def test_is_balanced(self) -> None:
        bs = self._make_bs()
        assert bs.is_balanced is True

    def test_is_not_balanced(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        bs = BalanceSheet(
            period=period,
            line_items=[
                ReportLineItem("AST-001", "Cash", Decimal("50000")),
                ReportLineItem("LIA-001", "AP", Decimal("-15000")),
            ],
        )
        assert bs.is_balanced is False

    def test_working_capital(self) -> None:
        bs = self._make_bs()
        assert bs.working_capital == Decimal("25000")

    def test_debt_to_equity(self) -> None:
        bs = self._make_bs()
        assert bs.debt_to_equity == Decimal("1.40")

    def test_debt_to_equity_no_equity(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        bs = BalanceSheet(
            period=period,
            line_items=[
                ReportLineItem("AST-001", "Cash", Decimal("50000")),
                ReportLineItem("LIA-001", "AP", Decimal("-15000")),
            ],
        )
        assert bs.debt_to_equity is None

    def test_current_ratio(self) -> None:
        bs = self._make_bs()
        assert bs.current_ratio == Decimal("1.71")

    def test_current_ratio_no_liabilities(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        bs = BalanceSheet(
            period=period,
            line_items=[
                ReportLineItem("AST-001", "Cash", Decimal("50000")),
            ],
        )
        assert bs.current_ratio is None


class TestCashFlowStatement:
    """Tests for CashFlowStatement."""

    def _make_cf(self) -> CashFlowStatement:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        return CashFlowStatement(
            period=period,
            line_items=[
                ReportLineItem("OCF-001", "Operations", Decimal("30000")),
                ReportLineItem("ICF-001", "Investments", Decimal("-10000")),
                ReportLineItem("FCF-001", "Financing", Decimal("-5000")),
            ],
        )

    def test_operating_cash_flow(self) -> None:
        cf = self._make_cf()
        assert cf.operating_cash_flow == Decimal("30000")

    def test_investing_cash_flow(self) -> None:
        cf = self._make_cf()
        assert cf.investing_cash_flow == Decimal("-10000")

    def test_financing_cash_flow(self) -> None:
        cf = self._make_cf()
        assert cf.financing_cash_flow == Decimal("-5000")

    def test_net_cash_flow(self) -> None:
        cf = self._make_cf()
        assert cf.net_cash_flow == Decimal("15000")

    def test_is_cash_positive(self) -> None:
        cf = self._make_cf()
        assert cf.is_cash_positive is True

    def test_is_cash_negative(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        cf = CashFlowStatement(
            period=period,
            line_items=[
                ReportLineItem("OCF-001", "Operations", Decimal("-5000")),
            ],
        )
        assert cf.is_cash_positive is False

    def test_free_cash_flow(self) -> None:
        period = ReportPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        cf = CashFlowStatement(
            period=period,
            line_items=[
                ReportLineItem("OCF-001", "Operations", Decimal("30000")),
                ReportLineItem("CAPEX-001", "CapEx", Decimal("-8000")),
            ],
        )
        assert cf.free_cash_flow == Decimal("22000")


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def _make_entry(
        self,
        account_id: str,
        amount: str,
        entry_date: date,
    ) -> JournalEntry:
        """Create a balanced entry: debit account, credit equity."""
        return JournalEntry(
            transactions=[
                Transaction(account_id=account_id, amount=Decimal(amount)),
                Transaction(account_id="EQY-001", amount=Decimal(str(-Decimal(amount)))),
            ],
            date=entry_date,
        )

    def test_generate_profit_and_loss(self) -> None:
        gen = ReportGenerator()
        gen.add_entry(self._make_entry("REV-001", "-10000", date(2024, 3, 15)))
        gen.add_entry(self._make_entry("EXP-001", "3000", date(2024, 3, 20)))
        gen.add_entry(self._make_entry("EXP-002", "2000", date(2024, 4, 10)))
        period = ReportPeriod(date(2024, 1, 1), date(2024, 12, 31))
        pl = gen.generate_profit_and_loss(period)
        assert pl.total_revenue == Decimal("10000")
        assert pl.total_expenses == Decimal("5000")
        assert pl.net_income == Decimal("5000")
        assert pl.is_profitable is True

    def test_generate_profit_and_loss_empty_period(self) -> None:
        gen = ReportGenerator()
        gen.add_entry(self._make_entry("REV-001", "-10000", date(2024, 3, 15)))
        period = ReportPeriod(date(2025, 1, 1), date(2025, 12, 31))
        pl = gen.generate_profit_and_loss(period)
        assert pl.total_revenue == Decimal("0")
        assert pl.net_income == Decimal("0")

    def test_generate_balance_sheet(self) -> None:
        gen = ReportGenerator()
        gen.add_entry(self._make_entry("AST-001", "50000", date(2024, 1, 15)))
        gen.add_entry(self._make_entry("LIA-001", "-15000", date(2024, 2, 1)))
        period = ReportPeriod(date(2024, 1, 1), date(2024, 12, 31))
        bs = gen.generate_balance_sheet(period)
        assert bs.total_assets == Decimal("50000")
        assert bs.total_liabilities == Decimal("15000")

    def test_generate_cash_flow(self) -> None:
        gen = ReportGenerator()
        gen.add_entry(self._make_entry("OCF-001", "30000", date(2024, 3, 15)))
        gen.add_entry(self._make_entry("ICF-001", "-10000", date(2024, 4, 1)))
        period = ReportPeriod(date(2024, 1, 1), date(2024, 12, 31))
        cf = gen.generate_cash_flow(period)
        assert cf.operating_cash_flow == Decimal("30000")
        assert cf.investing_cash_flow == Decimal("-10000")
        assert cf.net_cash_flow == Decimal("20000")

    def test_generate_all(self) -> None:
        gen = ReportGenerator()
        gen.add_entry(self._make_entry("REV-001", "-10000", date(2024, 3, 15)))
        gen.add_entry(self._make_entry("EXP-001", "3000", date(2024, 3, 20)))
        gen.add_entry(self._make_entry("AST-001", "50000", date(2024, 1, 15)))
        gen.add_entry(self._make_entry("OCF-001", "30000", date(2024, 3, 15)))
        period = ReportPeriod(date(2024, 1, 1), date(2024, 12, 31))
        pl, bs, cf = gen.generate_all(period)
        assert isinstance(pl, ProfitAndLoss)
        assert isinstance(bs, BalanceSheet)
        assert isinstance(cf, CashFlowStatement)
        assert pl.net_income == Decimal("7000")
        assert bs.total_assets == Decimal("50000")
        assert cf.operating_cash_flow == Decimal("30000")


# ===================================================================
# Core models (Account, Transaction, JournalEntry, Invoice)
# ===================================================================


class TestAccount:
    """Tests for Account."""

    def test_create_account(self) -> None:
        account = Account(name="Cash", account_type=AccountType.ASSET)
        assert account.name == "Cash"
        assert account.account_type == AccountType.ASSET
        assert account.is_active is True

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="name"):
            Account(name="", account_type=AccountType.ASSET)

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(TypeError):
            Account(name="Cash", account_type="invalid")  # type: ignore[arg-type]


class TestTransaction:
    """Tests for Transaction."""

    def test_create_transaction(self) -> None:
        txn = Transaction(account_id="AST-001", amount=Decimal("100"))
        assert txn.account_id == "AST-001"
        assert txn.amount == Decimal("100")

    def test_zero_amount_raises(self) -> None:
        with pytest.raises(ValueError, match="zero"):
            Transaction(account_id="AST-001", amount=Decimal("0"))

    def test_empty_account_id_raises(self) -> None:
        with pytest.raises(ValueError, match="account_id"):
            Transaction(account_id="", amount=Decimal("100"))


class TestJournalEntry:
    """Tests for JournalEntry."""

    def test_balanced_entry(self) -> None:
        entry = JournalEntry(
            transactions=[
                Transaction(account_id="AST-001", amount=Decimal("100")),
                Transaction(account_id="EQY-001", amount=Decimal("-100")),
            ],
        )
        assert entry.is_balanced() is True

    def test_unbalanced_entry_raises(self) -> None:
        with pytest.raises(ValueError, match="not balanced"):
            JournalEntry(
                transactions=[
                    Transaction(account_id="AST-001", amount=Decimal("100")),
                    Transaction(account_id="EQY-001", amount=Decimal("-50")),
                ],
            )

    def test_single_transaction_raises(self) -> None:
        with pytest.raises(ValueError, match="at least two"):
            JournalEntry(
                transactions=[
                    Transaction(account_id="AST-001", amount=Decimal("100")),
                ],
            )

    def test_total_debits(self) -> None:
        entry = JournalEntry(
            transactions=[
                Transaction(account_id="AST-001", amount=Decimal("100")),
                Transaction(account_id="AST-002", amount=Decimal("50")),
                Transaction(account_id="EQY-001", amount=Decimal("-150")),
            ],
        )
        assert entry.total_debits() == Decimal("150")

    def test_total_credits(self) -> None:
        entry = JournalEntry(
            transactions=[
                Transaction(account_id="AST-001", amount=Decimal("100")),
                Transaction(account_id="EQY-001", amount=Decimal("-100")),
            ],
        )
        assert entry.total_credits() == Decimal("100")


class TestInvoiceLineItem:
    """Tests for InvoiceLineItem."""

    def test_subtotal(self) -> None:
        item = InvoiceLineItem(
            description="Test",
            quantity=Decimal("3"),
            unit_price=Decimal("10"),
        )
        assert item.subtotal == Decimal("30")

    def test_discount_amount(self) -> None:
        item = InvoiceLineItem(
            description="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("100"),
            discount_percent=Decimal("10"),
        )
        assert item.discount_amount == Decimal("10")

    def test_net_amount(self) -> None:
        item = InvoiceLineItem(
            description="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("100"),
            discount_percent=Decimal("10"),
        )
        assert item.net_amount == Decimal("90")

    def test_tax_amount(self) -> None:
        item = InvoiceLineItem(
            description="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("100"),
            tax_rate=Decimal("20"),
        )
        assert item.tax_amount == Decimal("20")

    def test_total(self) -> None:
        item = InvoiceLineItem(
            description="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("100"),
            discount_percent=Decimal("10"),
            tax_rate=Decimal("20"),
        )
        # net = 90, tax = 18, total = 108
        assert item.total == Decimal("108")

    def test_negative_quantity_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            InvoiceLineItem(
                description="Test",
                quantity=Decimal("-1"),
                unit_price=Decimal("10"),
            )

    def test_negative_unit_price_raises(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            InvoiceLineItem(
                description="Test",
                quantity=Decimal("1"),
                unit_price=Decimal("-10"),
            )

    def test_discount_over_100_raises(self) -> None:
        with pytest.raises(ValueError, match="Discount"):
            InvoiceLineItem(
                description="Test",
                quantity=Decimal("1"),
                unit_price=Decimal("10"),
                discount_percent=Decimal("101"),
            )

    def test_negative_tax_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="Tax rate"):
            InvoiceLineItem(
                description="Test",
                quantity=Decimal("1"),
                unit_price=Decimal("10"),
                tax_rate=Decimal("-5"),
            )


class TestInvoice:
    """Tests for Invoice."""

    def test_create_invoice(self) -> None:
        invoice = Invoice(
            customer_id="cust-1",
            line_items=[
                InvoiceLineItem(
                    description="Service",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100"),
                )
            ],
        )
        assert invoice.customer_id == "cust-1"
        assert invoice.total == Decimal("100")
        assert invoice.status == "draft"

    def test_empty_customer_raises(self) -> None:
        with pytest.raises(ValueError, match="customer_id"):
            Invoice(
                customer_id="",
                line_items=[
                    InvoiceLineItem(
                        description="Service",
                        quantity=Decimal("1"),
                        unit_price=Decimal("100"),
                    )
                ],
            )

    def test_empty_line_items_raises(self) -> None:
        with pytest.raises(ValueError, match="line item"):
            Invoice(customer_id="cust-1", line_items=[])

    def test_subtotal(self) -> None:
        invoice = Invoice(
            customer_id="cust-1",
            line_items=[
                InvoiceLineItem("A", Decimal("1"), Decimal("100")),
                InvoiceLineItem("B", Decimal("2"), Decimal("50")),
            ],
        )
        assert invoice.subtotal == Decimal("200")

    def test_total_tax(self) -> None:
        invoice = Invoice(
            customer_id="cust-1",
            line_items=[
                InvoiceLineItem("A", Decimal("1"), Decimal("100"), tax_rate=Decimal("20")),
            ],
        )
        assert invoice.total_tax == Decimal("20")

    def test_amount_due_paid(self) -> None:
        invoice = Invoice(
            customer_id="cust-1",
            line_items=[
                InvoiceLineItem("A", Decimal("1"), Decimal("100")),
            ],
            status="paid",
        )
        assert invoice.amount_due == Decimal("0")

    def test_amount_due_unpaid(self) -> None:
        invoice = Invoice(
            customer_id="cust-1",
            line_items=[
                InvoiceLineItem("A", Decimal("1"), Decimal("100")),
            ],
            status="sent",
        )
        assert invoice.amount_due == Decimal("100")
