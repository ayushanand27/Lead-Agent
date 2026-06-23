from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    WARM = "warm"
    HOT = "hot"
    CONVERTED = "converted"
    LOST = "lost"


LEAD_STATUS_VALUES = {status.value for status in LeadStatus}


class Lead(BaseModel):
    id: int
    owner_phone: str
    name: str
    phone: str
    source: str
    status: str
    notes: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    created_at: datetime


# --- MCP read-tool input schemas ---


class ListLeadsInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    status_filter: Optional[str] = Field(
        None, description="Optional status filter (new, contacted, warm, hot, converted, lost)"
    )


class GetStaleLeadsInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    days_since_contact: int = Field(2, ge=1, description="Leads not contacted in this many days")


class SearchLeadsInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    query: str = Field(..., min_length=1, description="Search term for name, phone, source, or notes")


class GetLeadDetailsInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    lead_id: int = Field(..., ge=1, description="Lead primary key")
