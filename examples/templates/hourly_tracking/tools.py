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