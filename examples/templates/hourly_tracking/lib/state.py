from engine.schemas.session_state import SessionState


class HourlyTrackingState(SessionState):
    raw_transactions: list = []
    structured_transactions: list = []
    validation_passed: bool = False
    discrepancies: list = []
