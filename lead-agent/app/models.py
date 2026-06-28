from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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


# --- MCP write-tool input schemas ---


class CreateLeadInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    name: str = Field(..., min_length=1, description="Lead name")
    phone: str = Field(..., min_length=1, description="Lead phone number")
    source: str = Field(..., min_length=1, description="Lead source e.g. IndiaMART, Referral")
    notes: Optional[str] = Field(None, description="Optional initial notes")


class UpdateLeadStatusInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    lead_id: int = Field(..., ge=1, description="Lead primary key")
    new_status: str = Field(..., description="New status value")

    @field_validator("new_status")
    @classmethod
    def validate_new_status(cls, value: str) -> str:
        if value not in LEAD_STATUS_VALUES:
            allowed = ", ".join(sorted(LEAD_STATUS_VALUES))
            raise ValueError(f"Invalid status. Allowed: {allowed}")
        return value


class AddLeadNoteInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    lead_id: int = Field(..., ge=1, description="Lead primary key")
    note: str = Field(..., min_length=1, description="Note text to append")


class AddLeadTagsInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    lead_id: int = Field(..., ge=1, description="Lead primary key")
    tags: str = Field(
        ...,
        min_length=1,
        description="Comma-separated tags e.g. site-visit, urgent, noida",
    )


class DraftFollowupMessageInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    lead_id: int = Field(..., ge=1, description="Lead primary key")
    tone: str = Field("friendly", description="Message tone e.g. friendly, formal, urgent")


class SendWhatsappMessageInput(BaseModel):
    owner_phone: str = Field(..., description="WhatsApp number of the business owner")
    lead_id: int = Field(..., ge=1, description="Lead primary key")
    message_text: str = Field(..., min_length=1, description="Message body to send to the lead")
