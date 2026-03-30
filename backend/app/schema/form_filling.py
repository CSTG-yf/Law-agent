from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class SlotStatus(BaseModel):
    value: Any = None
    confirmed: bool = False
    source: Literal["user_input", "inferred", "ocr", "default"] = "user_input"
    confidence: float = 1.0
    turn_filled: int = 0


class BlockState(BaseModel):
    block_id: str
    display_name: str
    slots: Dict[str, SlotStatus] = Field(default_factory=dict)
    completion_rate: float = 0.0
    is_active: bool = False
    is_complete: bool = False


class FormFillingState(BaseModel):
    session_id: str
    template_type: str = "labor_dispute"
    blocks: Dict[str, BlockState] = Field(default_factory=dict)
    current_block: str = "plaintiff"
    conversation_turn: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SlotExtractionResult(BaseModel):
    extracted_slots: Dict[str, Any] = Field(default_factory=dict)
    inferred_slots: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    needs_clarification: List[str] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)


class BlockDefinition(BaseModel):
    block_id: str
    display_name: str
    description: str
    slots: List[str]
    required_slots: List[str]
    order: int


class TemplateDefinition(BaseModel):
    template_type: str
    template_name: str
    template_file: str
    blocks: List[BlockDefinition]


class StartFillingRequest(BaseModel):
    template_type: str = "labor_dispute"
    user_id: Optional[str] = None


class StartFillingResponse(BaseModel):
    session_id: str
    template_type: str
    current_block: str
    blocks: List[BlockDefinition]
    message: str


class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    user_id: Optional[str] = None


class SendMessageResponse(BaseModel):
    session_id: str
    message: str
    current_block: str
    completion_rate: float
    extracted_slots: Dict[str, Any] = Field(default_factory=dict)
    needs_clarification: bool = False
    clarification_questions: List[str] = Field(default_factory=list)
    suggested_next_action: Optional[str] = None


class GetStateRequest(BaseModel):
    session_id: str


class GetStateResponse(BaseModel):
    session_id: str
    template_type: str
    current_block: str
    blocks: Dict[str, BlockState] = Field(default_factory=dict)
    overall_completion_rate: float = 0.0
    conversation_turn: int = 0
    is_complete: bool = False


class UpdateSlotRequest(BaseModel):
    session_id: str
    block_id: str
    slot_name: str
    value: Any
    confirmed: bool = True


class UpdateSlotResponse(BaseModel):
    session_id: str
    block_id: str
    slot_name: str
    success: bool
    message: str


class GenerateDocumentRequest(BaseModel):
    session_id: str


class GenerateDocumentResponse(BaseModel):
    success: bool
    document_url: Optional[str] = None
    message: str
    missing_fields: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    code: int
    status: str
    message: str


class SessionListItem(BaseModel):
    session_id: str
    template_type: str
    current_block: str
    conversation_turn: int
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionListItem]
    total: int


class HistoryEntry(BaseModel):
    role: str
    message: str
    timestamp: str


class GetHistoryRequest(BaseModel):
    session_id: str
    limit: int = 50
