"""Tools for Hourly Tracking Agent."""

from __future__ import annotations

from typing import Any

from engine.runner.tool_registry import tool

_correction_attempts = 0


@tool(description="Fetch broker transactions from last hour.")
def fetch_broker_transactions() -> dict[str, Any]:
    return {
        "transactions": [
            {
                "transaction_id": "TXN001",
                "broker_id": "BRK001",
                "investor_id": "INV001",
                "input_amount": 1000,
                "output_amount": 950,
                "fees": 50,
            }
        ]
    }


@tool(description="Fetch investor logs from last hour.")
def fetch_investor_logs() -> dict[str, Any]:
    return {
        "transactions": [
            {
                "transaction_id": "TXN001",
                "broker_id": "BRK001",
                "investor_id": "INV001",
                "input_amount": 1000,
                "output_amount": 950,
                "fees": 50,
            }
        ]
    }


@tool(description="Normalize raw transaction data.")
def normalize_transactions() -> dict[str, Any]:
    transactions = [
        {
            "transaction_id": "TXN001",
            "broker_id": "BRK001",
            "investor_id": "INV001",
            "input_amount": 1000,
            "output_amount": 950,
            "fees": 50,
        }
    ]

    return {"structured_transactions": transactions}


@tool(description="Validate transaction reconciliation.")
def validate_transactions() -> dict[str, Any]:
    global _correction_attempts

    # Demo: fee mismatch survives one auto-correction cycle, then needs human review.
    transactions = [
        {
            "transaction_id": "TXN001",
            "broker_id": "BRK001",
            "investor_id": "INV001",
            "input_amount": 1000,
            "output_amount": 950,
            "fees": 60 if _correction_attempts == 0 else 55,
        }
    ]

    discrepancies = []

    for txn in transactions:
        expected_input = txn["output_amount"] + txn["fees"]

        if txn["input_amount"] != expected_input:
            discrepancies.append(
                {
                    "transaction_id": txn["transaction_id"],
                    "expected_input": expected_input,
                    "actual_input": txn["input_amount"],
                    "reason": "fee_mismatch",
                }
            )

    validation_passed = len(discrepancies) == 0
    requires_human_review = not validation_passed and _correction_attempts >= 1

    return {
        "validation_passed": validation_passed,
        "discrepancies": discrepancies,
        "requires_human_review": requires_human_review,
    }


@tool(description="Correct transaction discrepancies.")
def correct_transactions() -> dict[str, Any]:
    global _correction_attempts
    _correction_attempts += 1

    corrected_transactions = [
        {
            "transaction_id": "TXN001",
            "broker_id": "BRK001",
            "investor_id": "INV001",
            "input_amount": 1000,
            "output_amount": 950,
            "fees": 55,
        }
    ]

    return {
        "corrected_transactions": corrected_transactions,
        "correction_attempted": True,
    }


@tool(description="Store verified transaction results.")
def store_verified_results() -> dict[str, Any]:
    return {
        "result": "stored",
        "status": "success",
    }
