from pydantic import BaseModel


class VisibilityRequest(BaseModel):
    domain: str


class BotStatus(BaseModel):
    bot: str
    allowed: bool


class VisibilityReport(BaseModel):
    domain: str
    robots_found: bool
    bots: list[BotStatus]
    ai_blocked_count: int
