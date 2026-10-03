"""Tests for deepened accounting module."""
import pytest
from datetime import date, timedelta
from decimal import Decimal

class TestMultiCurrencyConversion:
    @pytest.fixture
    def converter(self):
        from apex_os_bp.accounting.deepened import CurrencyConverter
        return CurrencyConverter(rates={"EUR": "0.85", "GBP": "0.75", "JPY": "110.0"})

    def test_convert_usd_to_eur(self, converter):
        assert converter.convert(Decimal("100"), "USD", "EUR") == Decimal("85.00")

    def test_convert_usd_to_gbp(self, converter):
        assert converter.convert(Decimal("200"), "USD", "GBP") == Decimal("150.00")

    def test_convert_eur_to_usd(self, converter):
        assert converter.convert(Decimal("85"), "EUR", "USD") == Decimal("100.00")

    def test_same_currency_no_change(self, converter):
        assert converter.convert(Decimal("50"), "USD", "USD") == Decimal("50.00")

    def test_zero_amount(self, converter):
        assert converter.convert(Decimal("0"), "USD", "EUR") == Decimal("0.00")

    def test_missing_rate_raises(self, converter):
        with pytest.raises(ValueError, match="No rate"):
            converter.convert(Decimal("10"), "USD", "CHF")

    def test_rounding(self, converter):
        result = converter.convert(Decimal("100"), "USD", "JPY")
        assert result == Decimal("11000.00")


class TestRecurringEntries:
    @pytest.fixture
    def scheduler(self):
        from apex_os_bp.accounting.deepened import RecurringScheduler
        return RecurringScheduler()

    def test_monthly_recurrence(self, scheduler):
        entries = scheduler.generate("monthly", date(2024, 1, 15), 3)
        assert len(entries) == 3
        assert entries[0].date == date(2024, 1, 15)
        assert entries[1].date == date(2024, 2, 15)
        assert entries[2].date == date(2024, 3, 15)

    def test_weekly_recurrence(self, scheduler):
        entries = scheduler.generate("weekly", date(2024, 1, 1), 4)
        assert len(entries) == 4
        assert entries[1].date == date(2024, 1, 8)

    def test_end_date_cutoff(self, scheduler):
        entries = scheduler.generate("monthly", date(2024, 1, 1), 12, end_date=date(2024, 3, 31))
        assert len(entries) == 3

    def test_amount_preserved(self, scheduler):
        entries = scheduler.generate("monthly", date(2024, 1, 1), 2, amount=Decimal("500"))
        assert all(e.amount == Decimal("500") for e in entries)


class TestFinancialStatements:
    @pytest.fixture
    def ledger(self):
        from apex_os_bp.accounting.deepened import Ledger
        return Ledger()

    def test_balance_sheet_balances(self, ledger):
        ledger.add("assets", Decimal("10000"))
        ledger.add("liabilities", Decimal("4000"))
        ledger.add("equity", Decimal("6000"))
        bs = ledger.balance_sheet()
        assert bs["assets"] == bs["liabilities"] + bs["equity"]

    def test_income_statement(self, ledger):
        ledger.add("revenue", Decimal("50000"))
        ledger.add("expenses", Decimal("30000"))
        inc = ledger.income_statement()
        assert inc["net_income"] == Decimal("20000")

    def test_empty_ledger(self, ledger):
        bs = ledger.balance_sheet()
        assert bs["assets"] == Decimal("0")


class TestBudgetComparison:
    @pytest.fixture
    def budget(self):
        from apex_os_bp.accounting.deepened import BudgetComparator
        return BudgetComparator()

    def test_over_budget(self, budget):
        result = budget.compare(Decimal("1200"), Decimal("1000"))
        assert result.variance == Decimal("200")
        assert result.percent_variance == Decimal("20.00")
        assert result.is_over is True

    def test_under_budget(self, budget):
        result = budget.compare(Decimal("800"), Decimal("1000"))
        assert result.is_over is False
        assert result.variance == Decimal("-200")

    def test_on_budget(self, budget):
        result = budget.compare(Decimal("1000"), Decimal("1000"))
        assert result.variance == Decimal("0")
        assert result.is_over is False


class TestTaxCalculation:
    @pytest.fixture
    def tax(self):
        from apex_os_bp.accounting.deepened import TaxCalculator
        return TaxCalculator(brackets=[(Decimal("10000"), Decimal("0.10")),
                                        (Decimal("40000"), Decimal("0.20")),
                                        (Decimal("999999999"), Decimal("0.30"))])

    def test_first_bracket(self, tax):
        assert tax.calculate(Decimal("5000")) == Decimal("500.00")

    def test_second_bracket(self, tax):
        assert tax.calculate(Decimal("20000")) == Decimal("2500.00")

    def test_third_bracket(self, tax):
        assert tax.calculate(Decimal("50000")) == Decimal("9000.00")

    def test_zero_income(self, tax):
        assert tax.calculate(Decimal("0")) == Decimal("0.00")
