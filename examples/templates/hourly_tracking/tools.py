"""Tools for Hourly Tracking Agent."""

from __future__ import annotations

from typing import Any

from engine.runner.tool_registry import tool


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

    return {
        "structured_transactions": transactions
    }


@tool(description="Validate transaction reconciliation.")
def validate_transactions() -> dict[str, Any]:
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

    discrepancies = []

    for txn in transactions:
        expected_input = txn["output_amount"] + txn["fees"]

        if txn["input_amount"] != expected_input:
            discrepancies.append(
                {
                    "transaction_id": txn["transaction_id"],
                    "expected_input": expected_input,
                    "actual_input": txn["input_amount"],
                }
            )

    return {
        "validation_passed": len(discrepancies) == 0,
        "discrepancies": discrepancies,
    }


@tool(description="Correct transaction discrepancies.")
def correct_transactions() -> dict[str, Any]:
    corrected_transactions = [
        {
            "transaction_id": "TXN001",
            "broker_id": "BRK001",
            "investor_id": "INV001",
            "input_amount": 1000,
            "output_amount": 950,
            "fees": 50,
        }
    ]

    return {
        "corrected_transactions": corrected_transactions
    }


@tool(description="Store verified transaction results.")
def store_verified_results() -> dict[str, Any]:
    return {
        "result": "stored",
        "status": "success",
    }