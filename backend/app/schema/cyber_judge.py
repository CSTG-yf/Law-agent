from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class IntentInfoResponse(BaseModel):
    intent_type: str = Field(..., description="意图类型")
    confidence: float = Field(..., description="置信度")
    sub_intents: List[str] = Field(default_factory=list, description="次要意图")


class CaseInfoResponse(BaseModel):
    title: str = Field(..., description="案例标题")
    case_number: Optional[str] = Field(None, description="案号")
    court: Optional[str] = Field(None, description="法院")
    judgement_date: Optional[str] = Field(None, description="裁判日期")
    cause: Optional[str] = Field(None, description="案由")
    content_preview: Optional[str] = Field(None, description="内容摘要")
    relevance_score: float = Field(0.0, description="相关性分数")


class LawInfoResponse(BaseModel):
    title: str = Field(..., description="法规标题")
    publisher: Optional[str] = Field(None, description="发布机关")
    publish_date: Optional[str] = Field(None, description="发布日期")
    timeliness: Optional[str] = Field(None, description="时效性")
    law_id: Optional[str] = Field(None, description="法规ID")
    content_preview: Optional[str] = Field(None, description="内容摘要")
    relevance_score: float = Field(0.0, description="相关性分数")


class LawDetailResponse(BaseModel):
    title: str = Field(..., description="法规标题")
    content: Optional[str] = Field(None, description="法规内容")


class ExtractedFactsResponse(BaseModel):
    parties: List[str] = Field(default_factory=list, description="当事人")
    events: List[str] = Field(default_factory=list, description="事件")
    disputes: List[str] = Field(default_factory=list, description="争议焦点")
    claims: List[str] = Field(default_factory=list, description="诉求")
    key_dates: List[str] = Field(default_factory=list, description="关键日期")
    summary: Optional[str] = Field(None, description="事实摘要")


class AnalysisResultResponse(BaseModel):
    legal_basis: List[str] = Field(default_factory=list, description="法律依据")
    risk_assessment: Optional[str] = Field(None, description="风险评估")
    suggestions: List[str] = Field(default_factory=list, description="建议")


class FileInfoResponse(BaseModel):
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    extracted_text_length: int = Field(0, description="提取文本长度")


class CyberJudgeRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID（可选，不传则自动生成）")
    user_id: str = Field(..., description="用户ID")
    file_paths: Optional[List[str]] = Field(None, description="上传文件路径列表")
    stream: bool = Field(False, description="是否使用流式输出")
    max_history: Optional[int] = Field(None, ge=1, le=50, description="最大历史记录数")


class CyberJudgeResponse(BaseModel):
    message_id: str = Field(..., description="消息ID")
    session_id: str = Field(..., description="会话ID")
    role: Literal["assistant"] = Field("assistant", description="消息角色")
    content: str = Field(..., description="回复内容")
    timestamp: str = Field(..., description="回复时间戳")
    
    intent: Optional[IntentInfoResponse] = Field(None, description="意图信息")
    related_cases: List[CaseInfoResponse] = Field(default_factory=list, description="相关案例")
    related_laws: List[LawInfoResponse] = Field(default_factory=list, description="相关法律法规")
    law_details: List[LawDetailResponse] = Field(default_factory=list, description="法规详情")
    extracted_facts: Optional[ExtractedFactsResponse] = Field(None, description="提取的事实")
    analysis_result: Optional[AnalysisResultResponse] = Field(None, description="分析结果")
    files_processed: List[FileInfoResponse] = Field(default_factory=list, description="处理的文件")
    title: Optional[str] = Field(None, description="会话标题")


class CyberJudgeSessionInfo(BaseModel):
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    created_at: str = Field(..., description="创建时间")
    message_count: int = Field(..., description="消息数量")
    title: Optional[str] = Field(None, description="会话标题")


class CyberJudgeSessionHistory(BaseModel):
    session_id: str = Field(..., description="会话ID")
    messages: List[dict] = Field(default_factory=list, description="对话历史")
    total_messages: int = Field(..., description="消息总数")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class FileUploadResponse(BaseModel):
    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    file_path: str = Field(..., description="文件存储路径")
    file_size: int = Field(..., description="文件大小（字节）")
    upload_time: str = Field(..., description="上传时间")
