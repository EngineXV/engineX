"""Tools for Hourly Tracking Agent."""

from __future__ import annotations

import json
from typing import Any

from engine.runner.tool_registry import tool


@tool(description="Fetch broker transactions from last hour.")
def fetch_broker_transactions() -> dict[str, Any]:
    return {
        "transactions": [
            {
                "transaction_id": "TXN001",
                "broker_id": "BRK001",
                "input_amount": 1000,
                "output_amount": 900,
                "fees": 50,
            }
        ]
    }


@tool(description="Fetch investor logs from last hour.")
def fetch_investor_logs() -> dict[str, Any]:
    return {
        "transactions": [
            {
                "investor_id": "INV001"
            }
        ]
    }


@tool(description="Validate reconciliation.")
def validate_transactions(transactions_json: str) -> dict[str, Any]:

    transactions = json.loads(transactions_json)

    discrepancies = []

    for txn in transactions:

        if txn["input_amount"] != (
            txn["output_amount"] + txn["fees"]
        ):
            discrepancies.append(txn)

    return {
        "validation_passed": len(discrepancies) == 0,
        "discrepancies": discrepancies,
    }


@tool(description="Auto-correct discrepancies.")
def correct_transactions(
    transactions_json: str,
) -> dict[str, Any]:

    transactions = json.loads(transactions_json)

    corrected = []

    for txn in transactions:

        txn["output_amount"] = (
            txn["input_amount"]
            - txn["fees"]
        )

        corrected.append(txn)

    return {
        "transactions": corrected
    }


@tool(description="Store verified results.")
def store_verified_results(
    transactions_json: str,
) -> dict[str, Any]:

    return {
        "stored": True,
        "record_count": len(
            json.loads(transactions_json)
        ),
    }
