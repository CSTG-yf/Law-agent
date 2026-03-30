from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class PromptListItem(BaseModel):
    id: str = Field(description="提示词唯一ID")
    label: str = Field(description="提示词显示名称")
    description: Optional[str] = Field(None, description="提示词用途描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    category: str = Field(description="所属模块分类")
    source_file: str = Field(description="来源文件相对路径")


class PromptDetailItem(BaseModel):
    id: str = Field(description="提示词唯一ID")
    label: str = Field(description="提示词显示名称")
    content: str = Field(description="提示词完整内容")
    description: Optional[str] = Field(None, description="提示词用途描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    category: str = Field(description="所属模块分类")
    is_template: bool = Field(False, description="是否为模板（包含占位符）")
    source_file: str = Field(description="来源文件相对路径")


class PromptListData(BaseModel):
    prompts: List[PromptListItem] = Field(description="提示词列表（不含内容）")
    total_count: int = Field(description="提示词总数")
    all_tags: List[str] = Field(description="所有标签汇总")


class PromptListResponse(BaseModel):
    code: int
    status: str
    message: str
    data: Optional[PromptListData] = None


class PromptDetailResponse(BaseModel):
    code: int
    status: str
    message: str
    data: Optional[PromptDetailItem] = None
