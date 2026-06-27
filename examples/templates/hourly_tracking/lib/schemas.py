from pydantic import BaseModel


class Transaction(BaseModel):
    transaction_id: str
    broker_id: str
    investor_id: str
    input_amount: float
    output_amount: float
    fees: float


class ReconciliationResult(BaseModel):
    validation_passed: bool
    discrepancies: list[dict]
