"""Asset depreciation calculations."""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from apex_os_bp.assets.models import Asset, DepreciationMethod, DepreciationRecord


class DepreciationCalculator:
    """Calculate asset depreciation using various methods."""

    @staticmethod
    def straight_line(
        cost: float,
        salvage: float,
        life_years: int,
    ) -> float:
        """Annual straight-line depreciation."""
        if life_years <= 0:
            return 0.0
        return (cost - salvage) / life_years

    @staticmethod
    def declining_balance(
        cost: float,
        salvage: float,
        life_years: int,
        year: int,
        rate: float = 2.0,
    ) -> float:
        """Declining balance depreciation for a specific year."""
        if year <= 0 or year > life_years:
            return 0.0
        # Book value at start of year
        book_value = cost * (1 - rate / life_years) ** (year - 1)
        # Depreciation for this year
        dep = book_value * rate / life_years
        # Don't depreciate below salvage
        if book_value - dep < salvage:
            dep = book_value - salvage
        return max(0.0, dep)

    @staticmethod
    def sum_of_years_digits(
        cost: float,
        salvage: float,
        life_years: int,
        year: int,
    ) -> float:
        """Sum-of-years-digits depreciation for a specific year."""
        if year <= 0 or year > life_years:
            return 0.0
        total_digits = life_years * (life_years + 1) / 2
        remaining_life = life_years - year + 1
        return (cost - salvage) * remaining_life / total_digits

    @staticmethod
    def units_of_production(
        cost: float,
        salvage: float,
        total_units: float,
        units_produced: float,
    ) -> float:
        """Units-of-production depreciation."""
        if total_units <= 0:
            return 0.0
        rate = (cost - salvage) / total_units
        return rate * units_produced

    @classmethod
    def calculate_schedule(
        cls,
        asset: Asset,
        total_units: Optional[float] = None,
    ) -> List[DepreciationRecord]:
        """Generate full depreciation schedule for an asset."""
        records: List[DepreciationRecord] = []
        accumulated = 0.0
        book_value = asset.purchase_cost

        for year in range(1, asset.useful_life_years + 1):
            period_start = date(
                asset.purchase_date.year + year - 1,
                asset.purchase_date.month,
                asset.purchase_date.day,
            )
            period_end = date(
                asset.purchase_date.year + year,
                asset.purchase_date.month,
                asset.purchase_date.day,
            ) - timedelta(days=1)

            if asset.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
                dep = cls.straight_line(
                    asset.purchase_cost,
                    asset.salvage_value,
                    asset.useful_life_years,
                )
            elif asset.depreciation_method == DepreciationMethod.DECLINING_BALANCE:
                dep = cls.declining_balance(
                    asset.purchase_cost,
                    asset.salvage_value,
                    asset.useful_life_years,
                    year,
                )
            elif asset.depreciation_method == DepreciationMethod.SUM_OF_YEARS_DIGITS:
                dep = cls.sum_of_years_digits(
                    asset.purchase_cost,
                    asset.salvage_value,
                    asset.useful_life_years,
                    year,
                )
            elif asset.depreciation_method == DepreciationMethod.UNITS_OF_PRODUCTION:
                if total_units is None:
                    raise ValueError("total_units required for units_of_production")
                # Assume even distribution for schedule
                annual_units = total_units / asset.useful_life_years
                dep = cls.units_of_production(
                    asset.purchase_cost,
                    asset.salvage_value,
                    total_units,
                    annual_units,
                )
            else:
                dep = 0.0

            # Ensure we don't depreciate below salvage
            if book_value - dep < asset.salvage_value:
                dep = book_value - asset.salvage_value

            accumulated += dep
            book_value -= dep

            record = DepreciationRecord(
                id=f"dep-{asset.id}-{year}",
                asset_id=asset.id,
                period_start=period_start,
                period_end=period_end,
                depreciation_amount=round(dep, 2),
                accumulated_depreciation=round(accumulated, 2),
                book_value=round(book_value, 2),
                method=asset.depreciation_method,
            )
            records.append(record)

        return records

    @classmethod
    def get_book_value(
        cls,
        asset: Asset,
        as_of_date: date,
    ) -> float:
        """Calculate book value as of a specific date."""
        schedule = cls.calculate_schedule(asset)
        book_value = asset.purchase_cost

        for record in schedule:
            if record.period_end <= as_of_date:
                book_value = record.book_value
            else:
                break

        return round(book_value, 2)

    @classmethod
    def get_accumulated_depreciation(
        cls,
        asset: Asset,
        as_of_date: date,
    ) -> float:
        """Calculate accumulated depreciation as of a specific date."""
        schedule = cls.calculate_schedule(asset)
        accumulated = 0.0

        for record in schedule:
            if record.period_end <= as_of_date:
                accumulated = record.accumulated_depreciation
            else:
                break

        return round(accumulated, 2)
