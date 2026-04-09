from typing import List, Optional
from app.service.agent.official_tools import (
    _search_cases_impl,
    _search_laws_impl,
    _laws_detail_impl
)
from app.core.logger import get_logger
from .state import CaseInfo, LawInfo, LawDetail

logger = get_logger("cyber_judge_tools")


class CyberJudgeTools:
    """赛博判官工具封装"""
    
    @staticmethod
    async def search_cases(
        keywords: List[str],
        long_text: Optional[str] = None,
        court_level_arr: Optional[List[str]] = None,
        case_year_start: Optional[str] = None,
        case_year_end: Optional[str] = None,
        judgement_type_arr: Optional[List[str]] = None,
        page_no: int = 1,
        page_size: int = 5
    ) -> List[CaseInfo]:
        logger.info(f"搜索案例 - keywords: {keywords}")
        
        try:
            result = await _search_cases_impl(
                keywords=keywords,
                long_text=long_text,
                court_level_arr=court_level_arr,
                case_year_start=case_year_start,
                case_year_end=case_year_end,
                judgement_type_arr=judgement_type_arr,
                page_no=page_no,
                page_size=page_size
            )
            
            cases = CyberJudgeTools._parse_case_result(result)
            logger.info(f"案例搜索完成 - 找到 {len(cases)} 条案例")
            return cases
            
        except Exception as e:
            logger.error(f"案例搜索失败: {str(e)}")
            return []

    @staticmethod
    async def search_laws(
        keywords: List[str],
        time_liness_type_arr: Optional[List[str]] = None,
        publish_year_start: Optional[str] = None,
        publish_year_end: Optional[str] = None,
        page_no: int = 1,
        page_size: int = 5
    ) -> List[LawInfo]:
        logger.info(f"搜索法规 - keywords: {keywords}")
        
        try:
            result = await _search_laws_impl(
                keywords=keywords,
                time_liness_type_arr=time_liness_type_arr,
                publish_year_start=publish_year_start,
                publish_year_end=publish_year_end,
                page_no=page_no,
                page_size=page_size
            )
            
            laws = CyberJudgeTools._parse_law_result(result)
            logger.info(f"法规搜索完成 - 找到 {len(laws)} 条法规")
            return laws
            
        except Exception as e:
            logger.error(f"法规搜索失败: {str(e)}")
            return []

    @staticmethod
    async def get_law_detail(law_id: str) -> Optional[LawDetail]:
        logger.info(f"获取法规详情 - law_id: {law_id}")
        
        try:
            result = await _laws_detail_impl(law_id=law_id)
            
            detail = CyberJudgeTools._parse_law_detail_result(result, law_id)
            if detail:
                logger.info(f"法规详情获取成功 - title: {detail.get('title', '未知')}")
            return detail
            
        except Exception as e:
            logger.error(f"法规详情获取失败: {str(e)}")
            return None

    @staticmethod
    async def batch_get_law_details(law_ids: List[str], max_count: int = 3) -> List[LawDetail]:
        if not law_ids:
            return []
        
        ids_to_fetch = law_ids[:max_count]
        logger.info(f"批量获取法规详情 - count: {len(ids_to_fetch)}")
        
        details = []
        for law_id in ids_to_fetch:
            detail = await CyberJudgeTools.get_law_detail(law_id)
            if detail:
                details.append(detail)
        
        return details

    @staticmethod
    def _parse_case_result(result: str) -> List[CaseInfo]:
        cases = []
        
        if "未找到相关案例" in result or "找到 0 条" in result:
            return cases
        
        lines = result.split('\n')
        current_case = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                if current_case:
                    cases.append(CaseInfo(**current_case))
                current_case = {}
                title_match = line.split('.', 1)
                if len(title_match) > 1:
                    title = title_match[1].strip()
                    if title.startswith('【') and '】' in title:
                        title = title.split('】', 1)[1].strip()
                    current_case['title'] = title
            
            elif line.startswith('案号：'):
                current_case['case_number'] = line.replace('案号：', '').strip()
            elif line.startswith('法院：'):
                court_info = line.replace('法院：', '').strip()
                if '（' in court_info:
                    parts = court_info.split('（')
                    current_case['court'] = parts[0].strip()
                    current_case['level_of_trial'] = parts[1].replace('）', '').strip()
                else:
                    current_case['court'] = court_info
            elif line.startswith('案由：'):
                current_case['cause'] = line.replace('案由：', '').strip()
            elif line.startswith('文书类型：'):
                current_case['case_type'] = line.replace('文书类型：', '').strip()
            elif line.startswith('裁判日期：'):
                current_case['judgement_date'] = line.replace('裁判日期：', '').strip()
            elif line.startswith('内容摘要：'):
                current_case['content'] = line.replace('内容摘要：', '').strip()
        
        if current_case:
            cases.append(CaseInfo(**current_case))
        
        return cases

    @staticmethod
    def _parse_law_result(result: str) -> List[LawInfo]:
        laws = []
        
        if "未找到相关法律法规" in result or "找到 0 条" in result:
            return laws
        
        lines = result.split('\n')
        current_law = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                if current_law:
                    laws.append(LawInfo(**current_law))
                current_law = {}
                title_match = line.split('.', 1)
                if len(title_match) > 1:
                    title = title_match[1].strip()
                    if title.startswith('【') and '】' in title:
                        title = title.split('】', 1)[1].strip()
                    current_law['title'] = title
            
            elif line.startswith('发布机关：'):
                current_law['publisher'] = line.replace('发布机关：', '').strip()
            elif line.startswith('文号：'):
                current_law['issued_no'] = line.replace('文号：', '').strip()
            elif line.startswith('层级：'):
                current_law['level_name'] = line.replace('层级：', '').strip()
            elif line.startswith('发布日期：'):
                current_law['publish_date'] = line.replace('发布日期：', '').strip()
            elif line.startswith('生效日期：'):
                current_law['active_date'] = line.replace('生效日期：', '').strip()
            elif line.startswith('时效性：'):
                current_law['timeliness'] = line.replace('时效性：', '').strip()
            elif line.startswith('法律ID：'):
                current_law['law_id'] = line.replace('法律ID：', '').strip()
        
        if current_law:
            laws.append(LawInfo(**current_law))
        
        return laws

    @staticmethod
    def _parse_law_detail_result(result: str, law_id: str) -> Optional[LawDetail]:
        if "未找到法律ID" in result:
            return None
        
        detail = {'law_id': law_id}
        lines = result.split('\n')
        
        content_start = False
        content_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('【') and '】' in line:
                detail['title'] = line.split('】', 1)[1].strip() if '】' in line else line
            elif line.startswith('发布机关：'):
                detail['publisher'] = line.replace('发布机关：', '').strip()
            elif line.startswith('文号：'):
                detail['issued_no'] = line.replace('文号：', '').strip()
            elif line.startswith('层级：'):
                detail['level_name'] = line.replace('层级：', '').strip()
            elif line.startswith('发布日期：'):
                detail['publish_date'] = line.replace('发布日期：', '').strip()
            elif line.startswith('生效日期：'):
                detail['active_date'] = line.replace('生效日期：', '').strip()
            elif line.startswith('时效性：'):
                detail['timeliness'] = line.replace('时效性：', '').strip()
            elif line.startswith('法律条文内容：'):
                content_start = True
            elif content_start:
                content_lines.append(line)
        
        if content_lines:
            detail['content'] = '\n'.join(content_lines)
        
        return LawDetail(**detail) if detail.get('title') else None
