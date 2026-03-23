from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import httpx
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("official_tools")

CASE_API_URL = "https://openapi.delilegal.com/api/qa/v3/search/queryListCase"
LAW_API_URL = "https://openapi.delilegal.com/api/qa/v3/search/queryListLaw"
APP_ID = "QthdBErlyaYvyXul"
SECRET = "EC5D455E6BD348CE8E18BE05926D2EBE"


class CaseSearchInput(BaseModel):
    """案例检索输入参数"""
    keywords: List[str] = Field(description="关键词数组，例如：['劳动争议', '工伤']")
    long_text: Optional[str] = Field(default=None, description="长文本检索，与keywords二选一")
    court_level_arr: Optional[List[str]] = Field(default=None, description="法院层级数组，0:最高法院, 1:高级法院, 2:中级法院, 3:基层法院")
    case_year_start: Optional[str] = Field(default=None, description="案例裁判日期开始，格式：YYYY-MM-DD")
    case_year_end: Optional[str] = Field(default=None, description="案例裁判日期结束，格式：YYYY-MM-DD")
    judgement_type_arr: Optional[List[str]] = Field(default=None, description="文书类型数组，30:判决书, 31:裁决书, 32:调解书, 33:决定书, 34:通知书, 99:其他")
    page_no: int = Field(default=1, description="页码")
    page_size: int = Field(default=5, description="每页数量")
    sort_field: str = Field(default="correlation", description="排序字段：correlation(相关性)或time(裁判时间)")
    sort_order: str = Field(default="desc", description="排序方式：asc(升序)或desc(降序)")


class LawSearchInput(BaseModel):
    """法律法规检索输入参数"""
    keywords: List[str] = Field(description="关键词数组，例如：['房地产', '法律规定']")
    field_name: str = Field(default="semantic", description="检索字段：semantic(语义检索)")
    time_liness_type_arr: Optional[List[str]] = Field(default=None, description="时效性数组，5:有效")
    publish_year_start: Optional[str] = Field(default=None, description="发布日期开始，格式：YYYY-MM-DD")
    publish_year_end: Optional[str] = Field(default=None, description="发布日期结束，格式：YYYY-MM-DD")
    active_year_start: Optional[str] = Field(default=None, description="生效日期开始，格式：YYYY-MM-DD")
    active_year_end: Optional[str] = Field(default=None, description="生效日期结束，格式：YYYY-MM-DD")
    page_no: int = Field(default=1, description="页码")
    page_size: int = Field(default=5, description="每页数量")
    sort_field: str = Field(default="correlation", description="排序字段：correlation(相关性)或time(发布时间)")
    sort_order: str = Field(default="desc", description="排序方式：asc(升序)或desc(降序)")


async def call_case_api(payload: dict) -> dict:
    """调用案例检索API"""
    headers = {
        "appid": APP_ID,
        "secret": SECRET,
        "Content-Type": "application/json"
    }
    
    logger.info(f"调用案例检索API - keywords: {payload.get('condition', {}).get('keywordArr', [])}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(CASE_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success") and result.get("code") == 0:
                logger.info(f"案例检索成功 - 找到 {result.get('body', {}).get('totalCount', 0)} 条案例")
                return result["body"]
            else:
                logger.error(f"案例检索失败 - code: {result.get('code')}, msg: {result.get('msg')}")
                return {"data": [], "totalCount": 0, "totalPage": 0}
        except Exception as e:
            logger.error(f"案例检索API调用异常 - error: {str(e)}")
            return {"data": [], "totalCount": 0, "totalPage": 0}


async def call_law_api(payload: dict) -> dict:
    """调用法律法规检索API"""
    headers = {
        "appid": APP_ID,
        "secret": SECRET,
        "Content-Type": "application/json"
    }
    
    logger.info(f"调用法律法规检索API - keywords: {payload.get('condition', {}).get('keywords', [])}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(LAW_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success") and result.get("code") == 0:
                logger.info(f"法律法规检索成功 - 找到 {result.get('body', {}).get('totalCount', 0)} 条法规")
                return result["body"]
            else:
                logger.error(f"法律法规检索失败 - code: {result.get('code')}, msg: {result.get('msg')}")
                return {"data": [], "totalCount": 0, "totalPage": 0}
        except Exception as e:
            logger.error(f"法律法规检索API调用异常 - error: {str(e)}")
            return {"data": [], "totalCount": 0, "totalPage": 0}


async def _search_cases_impl(
    keywords: List[str],
    long_text: Optional[str] = None,
    court_level_arr: Optional[List[str]] = None,
    case_year_start: Optional[str] = None,
    case_year_end: Optional[str] = None,
    judgement_type_arr: Optional[List[str]] = None,
    page_no: int = 1,
    page_size: int = 5,
    sort_field: str = "correlation",
    sort_order: str = "desc"
) -> str:
    """案例检索实现函数（不使用@tool装饰器）"""
    condition = {}
    
    if long_text:
        condition["longText"] = long_text
    elif keywords:
        condition["keywordArr"] = keywords
    else:
        return "错误：必须提供keywords或long_text参数"
    
    if court_level_arr:
        condition["courtLevelArr"] = court_level_arr
    if case_year_start:
        condition["caseYearStart"] = case_year_start
    if case_year_end:
        condition["caseYearEnd"] = case_year_end
    if judgement_type_arr:
        condition["judgementTypeArr"] = judgement_type_arr
    
    payload = {
        "pageNo": page_no,
        "pageSize": page_size,
        "sortField": sort_field,
        "sortOrder": sort_order,
        "condition": condition
    }
    
    result = await call_case_api(payload)
    
    if not result.get("data"):
        return f"未找到相关案例，共检索到 {result.get('totalCount', 0)} 条记录"
    
    cases = result["data"]
    summary = f"找到 {result['totalCount']} 条相关案例，显示前 {len(cases)} 条：\n\n"
    
    for i, case in enumerate(cases, 1):
        summary += f"{i}. 【{case.get('title', '未知标题')}】\n"
        summary += f"   案号：{case.get('caseNumber', '未知')}\n"
        summary += f"   法院：{case.get('court', '未知')}（{case.get('levelOfTrial', '未知')}）\n"
        summary += f"   案由：{case.get('cause', '未知')}\n"
        summary += f"   文书类型：{case.get('judgementType', '未知')}\n"
        summary += f"   裁判日期：{case.get('judgementDate', '未知')}\n"
        if case.get('content'):
            content_preview = case['content'][:100] + "..." if len(case['content']) > 100 else case['content']
            summary += f"   内容摘要：{content_preview}\n"
        summary += "\n"
    
    return summary


@tool
async def search_cases(
    keywords: List[str],
    long_text: Optional[str] = None,
    court_level_arr: Optional[List[str]] = None,
    case_year_start: Optional[str] = None,
    case_year_end: Optional[str] = None,
    judgement_type_arr: Optional[List[str]] = None,
    page_no: int = 1,
    page_size: int = 5,
    sort_field: str = "correlation",
    sort_order: str = "desc"
) -> str:
    """检索相关法律案例。
    
    用于搜索法院判决书、裁定书等法律案例，支持关键词检索、时间范围筛选、法院层级筛选等。
    
    Args:
        keywords: 关键词数组，例如：['劳动争议', '工伤']
        long_text: 长文本检索，与keywords二选一，例如："上班途中车祸工伤案例"
        court_level_arr: 法院层级数组，0:最高法院, 1:高级法院, 2:中级法院, 3:基层法院
        case_year_start: 案例裁判日期开始，格式：YYYY-MM-DD
        case_year_end: 案例裁判日期结束，格式：YYYY-MM-DD
        judgement_type_arr: 文书类型数组，30:判决书, 31:裁决书, 32:调解书, 33:决定书, 34:通知书, 99:其他
        page_no: 页码，默认1
        page_size: 每页数量，默认5
        sort_field: 排序字段，correlation(相关性)或time(裁判时间)
        sort_order: 排序方式，asc(升序)或desc(降序)
    
    Returns:
        检索结果摘要，包含案例标题、法院、案号、裁判日期等信息
    
    Examples:
        >>> search_cases(keywords=["劳动争议", "工伤"], page_size=3)
        >>> search_cases(long_text="上班途中车祸工伤案例", court_level_arr=["2", "3"])
    """
    return await _search_cases_impl(
        keywords=keywords,
        long_text=long_text,
        court_level_arr=court_level_arr,
        case_year_start=case_year_start,
        case_year_end=case_year_end,
        judgement_type_arr=judgement_type_arr,
        page_no=page_no,
        page_size=page_size,
        sort_field=sort_field,
        sort_order=sort_order
    )


async def _search_laws_impl(
    keywords: List[str],
    field_name: str = "semantic",
    time_liness_type_arr: Optional[List[str]] = None,
    publish_year_start: Optional[str] = None,
    publish_year_end: Optional[str] = None,
    active_year_start: Optional[str] = None,
    active_year_end: Optional[str] = None,
    page_no: int = 1,
    page_size: int = 5,
    sort_field: str = "correlation",
    sort_order: str = "desc"
) -> str:
    """法律法规检索实现函数（不使用@tool装饰器）"""
    condition = {
        "keywords": keywords,
        "fieldName": field_name
    }
    
    if time_liness_type_arr:
        condition["timeLinessTypeArr"] = time_liness_type_arr
    if publish_year_start:
        condition["publishYearStart"] = publish_year_start
    if publish_year_end:
        condition["publishYearEnd"] = publish_year_end
    if active_year_start:
        condition["activeYearStart"] = active_year_start
    if active_year_end:
        condition["activeYearEnd"] = active_year_end
    
    payload = {
        "pageNo": page_no,
        "pageSize": page_size,
        "sortField": sort_field,
        "sortOrder": sort_order,
        "condition": condition
    }
    
    result = await call_law_api(payload)
    
    if not result.get("data"):
        return f"未找到相关法律法规，共检索到 {result.get('totalCount', 0)} 条记录"
    
    laws = result["data"]
    summary = f"找到 {result['totalCount']} 条相关法律法规，显示前 {len(laws)} 条：\n\n"
    
    for i, law in enumerate(laws, 1):
        summary += f"{i}. 【{law.get('title', '未知标题')}】\n"
        summary += f"   发布机关：{law.get('publisherName', '未知')}\n"
        summary += f"   文号：{law.get('issuedNo', '未知')}\n"
        summary += f"   层级：{law.get('levelName', '未知')}\n"
        summary += f"   发布日期：{law.get('publishDate', '未知')}\n"
        summary += f"   生效日期：{law.get('activeDate', '未知')}\n"
        summary += f"   时效性：{law.get('timelinessName', '未知')}\n"
        summary += "\n"
    
    return summary


@tool
async def search_laws(
    keywords: List[str],
    field_name: str = "semantic",
    time_liness_type_arr: Optional[List[str]] = None,
    publish_year_start: Optional[str] = None,
    publish_year_end: Optional[str] = None,
    active_year_start: Optional[str] = None,
    active_year_end: Optional[str] = None,
    page_no: int = 1,
    page_size: int = 5,
    sort_field: str = "correlation",
    sort_order: str = "desc"
) -> str:
    """检索相关法律法规。
    
    用于搜索法律条文、行政法规、地方性法规等，支持关键词检索、时效性筛选、时间范围筛选等。
    
    Args:
        keywords: 关键词数组，例如：['房地产', '法律规定']
        field_name: 检索字段，默认semantic(语义检索)
        time_liness_type_arr: 时效性数组，例如：['5']表示有效
        publish_year_start: 发布日期开始，格式：YYYY-MM-DD
        publish_year_end: 发布日期结束，格式：YYYY-MM-DD
        active_year_start: 生效日期开始，格式：YYYY-MM-DD
        active_year_end: 生效日期结束，格式：YYYY-MM-DD
        page_no: 页码，默认1
        page_size: 每页数量，默认5
        sort_field: 排序字段，correlation(相关性)或time(发布时间)
        sort_order: 排序方式，asc(升序)或desc(降序)
    
    Returns:
        检索结果摘要，包含法规标题、发布机关、发布日期、生效日期等信息
    
    Examples:
        >>> search_laws(keywords=["深圳市", "房地产", "法律规定"], page_size=3)
        >>> search_laws(keywords=["劳动合同"], time_liness_type_arr=["5"])
    """
    return await _search_laws_impl(
        keywords=keywords,
        field_name=field_name,
        time_liness_type_arr=time_liness_type_arr,
        publish_year_start=publish_year_start,
        publish_year_end=publish_year_end,
        active_year_start=active_year_start,
        active_year_end=active_year_end,
        page_no=page_no,
        page_size=page_size,
        sort_field=sort_field,
        sort_order=sort_order
    )


def get_available_tools() -> List[dict]:
    """获取可用工具列表"""
    return [
        {
            "name": "search_cases",
            "description": "检索相关法律案例，支持关键词检索、时间范围筛选、法院层级筛选等",
            "category": "案例检索",
            "enabled": True
        },
        {
            "name": "search_laws",
            "description": "检索相关法律法规，支持关键词检索、时效性筛选、时间范围筛选等",
            "category": "法律法规检索",
            "enabled": True
        }
    ]
