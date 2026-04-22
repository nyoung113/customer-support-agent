from pydantic import BaseModel

class UserAccontContext(BaseModel):
    customer_id: int
    name : str
    tier: str = "basic" # premium, basic, enterprise ... 


UserAccountContext = UserAccontContext


class InputGuardRailOutput(BaseModel):
    is_off_topic: bool
    is_inappropriate: bool = False
    reason: str


class OutputGuardRailOutput(BaseModel):
    violates_policy: bool
    reason: str
