"""Accounting routes — accounts, invoices, journal entries."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apex_os_bp.accounting.engine import AccountingEngine
from apex_os_bp.accounting.ledger import Account, AccountType, JournalEntry, JournalEntryLine
from apex_os_bp.api.models import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    InvoiceCreate,
    InvoiceResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    TrialBalanceResponse,
)

router = APIRouter(prefix="/accounting", tags=["Accounting"])


def get_accounting_engine(request: Request) -> AccountingEngine:
    """Get the accounting engine from the app state."""
    return request.app.state.accounting_engine


def _account_to_response(account: Account) -> AccountResponse:
    """Convert an Account model to a response."""
    return AccountResponse(
        id=account.id,
        name=account.name,
        type=account.type.value,
        balance=account.balance,
    )


# ─── Accounts ─────────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> List[AccountResponse]:
    """List all accounts."""
    return [_account_to_response(a) for a in engine.get_accounts()]


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreate,
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> AccountResponse:
    """Create a new account."""
    account = Account(
        id=str(__import__("uuid").uuid4()),
        name=body.name,
        type=AccountType(body.type.value),
        balance=body.balance,
    )
    engine.add_account(account)
    return _account_to_response(account)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> AccountResponse:
    """Get an account by ID."""
    account = engine._ledger.get_account(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}",
        )
    return _account_to_response(account)


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    body: AccountUpdate,
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> AccountResponse:
    """Update an account."""
    account = engine._ledger.get_account(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}",
        )
    if body.name is not None:
        account.name = body.name
    if body.type is not None:
        account.type = AccountType(body.type.value)
    if body.balance is not None:
        account.balance = body.balance
    return _account_to_response(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> None:
    """Delete an account."""
    account = engine._ledger.get_account(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}",
        )
    del engine._ledger._accounts[account_id]


# ─── Invoices ─────────────────────────────────────────────────────────────────

@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> List[InvoiceResponse]:
    """List all invoices."""
    return [InvoiceResponse(**inv) for inv in engine._invoices.values()]


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> InvoiceResponse:
    """Create a new invoice."""
    items = [
        {"description": item.description, "quantity": item.quantity, "unit_price": item.unit_price, "amount": item.amount}
        for item in body.items
    ]
    invoice = engine.create_invoice(customer_id=body.customer_id, items=items)
    return InvoiceResponse(**invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> InvoiceResponse:
    """Get an invoice by ID."""
    invoice = engine.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {invoice_id}",
        )
    return InvoiceResponse(**invoice)


@router.post("/invoices/{invoice_id}/post", response_model=InvoiceResponse)
async def post_invoice(
    invoice_id: str,
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> InvoiceResponse:
    """Post an invoice to the ledger."""
    invoice = engine.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {invoice_id}",
        )
    try:
        engine.post_invoice(invoice_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return InvoiceResponse(**engine.get_invoice(invoice_id))


# ─── Journal Entries ───────────────────────────────────────────────────────────

@router.get("/journal-entries", response_model=List[JournalEntryResponse])
async def list_journal_entries(
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> List[JournalEntryResponse]:
    """List all journal entries."""
    entries = engine._ledger.get_entries()
    return [
        JournalEntryResponse(
            id=e.id,
            description=e.description,
            lines=[{"account_id": l.account_id, "debit": l.debit, "credit": l.credit} for l in e.lines],
            metadata=e.metadata,
        )
        for e in entries
    ]


@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    body: JournalEntryCreate,
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> JournalEntryResponse:
    """Create and post a new journal entry."""
    lines = [
        JournalEntryLine(account_id=l.account_id, debit=l.debit, credit=l.credit)
        for l in body.lines
    ]
    try:
        entry = JournalEntry(
            id=str(__import__("uuid").uuid4()),
            description=body.description,
            lines=lines,
            metadata=body.metadata,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    try:
        engine._ledger.post(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return JournalEntryResponse(
        id=entry.id,
        description=entry.description,
        lines=[{"account_id": l.account_id, "debit": l.debit, "credit": l.credit} for l in entry.lines],
        metadata=entry.metadata,
    )


# ─── Trial Balance ────────────────────────────────────────────────────────────

@router.get("/trial-balance", response_model=TrialBalanceResponse)
async def get_trial_balance(
    engine: AccountingEngine = Depends(get_accounting_engine),
) -> TrialBalanceResponse:
    """Get the trial balance."""
    tb = engine.trial_balance()
    return TrialBalanceResponse(trial_balance=tb, is_balanced=abs(tb) < 0.01)
