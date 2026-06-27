# Hourly Tracking Agent

Hourly reconciliation workflow for broker and investor transactions.

## Workflow

Fetch Transactions
↓
Process Transactions
↓
Validate Transactions
↓
Validation Passed?

YES → Store Results

NO → Correct Transactions
        ↓
     Validate Transactions

## Features

- Hourly execution via AsyncEntryPointSpec
- Multi-source transaction ingestion
- Structured transaction normalization
- Deterministic financial validation
- Auto-correction feedback loop
- Verified result storage

## Validation Rule

input_amount = output_amount + fees
