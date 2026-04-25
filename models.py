from pydantic import BaseModel, Field

class UserAccountContext(BaseModel):
    customer_id: int
    name : str
    email: str | None = None
    tier: str = "basic" # premium, basic, enterprise ... 
    troubleshooting_history: list[str] = Field(default_factory=list)

    def is_premium_customer(self) -> bool:
        return self.tier.lower() in {"premium", "enterprise"}

    def add_troubleshooting_step(self, step: str) -> None:
        self.troubleshooting_history.append(step)


class InputGuardRailOutput(BaseModel):
    is_off_topic: bool
    reason: str


class HandoffData(BaseModel):
    to_agent_name: str
    issue_type: str
    issue_description: str
    reason : str


class TechnicalOutputGuardrailOutput(BaseModel):
    contains_off_topic: bool = False
    reason: str = ""
    contains_billing_data: bool = False
    contains_account_data: bool = False
