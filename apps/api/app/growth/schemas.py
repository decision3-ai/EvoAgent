from pydantic import BaseModel


class VisibilityRequest(BaseModel):
    domain: str


class BotStatus(BaseModel):
    bot: str
    allowed: bool


class VisibilityReport(BaseModel):
    domain: str
    robots_found: bool
    llms_txt: bool
    llms_full_txt: bool
    json_ld: bool
    meta_description: bool
    h1: bool
    content_readable: bool
    content_length: int
    bots: list[BotStatus]
    ai_blocked_count: int
