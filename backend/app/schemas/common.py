from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, List, Any
from datetime import datetime, timezone
import uuid

T = TypeVar("T")


class ReportMeta(BaseModel):
    total:           int
    page:            int
    page_size:       int
    total_pages:     int
    generated_at:    datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    workspace_id:    str


class ReportResponse(BaseModel, Generic[T]):
    success:     bool = True
    data:        List[T]
    meta:        ReportMeta
    summary:     Optional[dict] = None
    request_id:  str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}")


class ErrorDetail(BaseModel):
    field:   Optional[str] = None
    message: str