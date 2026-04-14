from typing import List, Optional
import json
import re
from app.core.logger import get_logger
from app.service.rag.file_processor import FileProcessor
from .state import ExtractedFacts, FileInfo
from .prompts import CyberJudgePrompts

logger = get_logger("fact_extractor")


class FactExtractor:
    """文件事实提取服务"""
    
    def __init__(self, llm, chunk_size: int = 2000):
        self.llm = llm
        self.file_processor = FileProcessor(chunk_size=chunk_size, chunk_overlap=100)
        self.chunk_size = chunk_size

    async def extract_from_file(self, file_path: str, filename: str) -> tuple[FileInfo, ExtractedFacts]:
        logger.info(f"开始提取文件事实 - filename: {filename}")
        
        try:
            text = self.file_processor.extract_text(file_path)
            logger.info(f"文件文本提取结果 - filename: {filename}, text_length: {len(text) if text else 0}")

            if not text or len(text.strip()) == 0:
                logger.warning(f"文件内容为空 - filename: {filename}")
                return self._create_empty_file_info(file_path, filename), self._create_empty_facts()
            
            file_type = self._get_file_type(filename)
            
            file_info = FileInfo(
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                extracted_text=text,
                extracted_text_length=len(text)
            )
            
            facts = await self._extract_facts_from_text(text)
            
            logger.info(f"文件事实提取完成 - filename: {filename}, facts_summary: {facts.get('summary', 'N/A')}")
            
            return file_info, facts
            
        except Exception as e:
            logger.error(f"文件事实提取失败 - filename: {filename}, error: {str(e)}")
            return self._create_empty_file_info(file_path, filename), self._create_empty_facts()

    async def extract_from_text(self, text: str) -> ExtractedFacts:
        if not text or len(text.strip()) == 0:
            return self._create_empty_facts()
        
        return await self._extract_facts_from_text(text)

    async def _extract_facts_from_text(self, text: str) -> ExtractedFacts:
        chunks = self.file_processor.split_text(text)
        if not chunks:
            return self._create_empty_facts()

        if len(chunks) > 1:
            logger.info(f"文本过长，拆分为{len(chunks)}个分块进行事实提取")

        selected_chunks = chunks[:3]
        all_facts = []
        for index, chunk in enumerate(selected_chunks, 1):
            facts = await self._extract_facts_from_chunk(chunk, index, len(selected_chunks))
            all_facts.append(facts)

        return self._merge_facts(all_facts)

    async def _extract_facts_from_chunk(self, text: str, chunk_index: int, total_chunks: int) -> ExtractedFacts:
        prompt = CyberJudgePrompts.FACT_EXTRACTION_PROMPT.format(text_content=text)

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content
            result = self._parse_json_result(content)
            if result is None:
                logger.warning(f"无法解析第{chunk_index}/{total_chunks}个分块的事实提取结果，使用默认值")
                result = self._get_default_facts(text)
        except Exception as e:
            logger.error(f"第{chunk_index}/{total_chunks}个分块事实提取失败: {str(e)}")
            result = self._get_default_facts(text)

        return ExtractedFacts(
            parties=result.get("parties", []),
            events=result.get("events", []),
            disputes=result.get("disputes", []),
            claims=result.get("claims", []),
            key_dates=result.get("key_dates", []),
            amounts=result.get("amounts", []),
            locations=result.get("locations", []),
            summary=result.get("summary", "")
        )

    def _parse_json_result(self, content: str) -> Optional[dict]:
        if not content:
            return None

        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            return None

    def _merge_facts(self, facts_list: List[ExtractedFacts]) -> ExtractedFacts:
        merged = self._create_empty_facts()
        summaries = []

        for facts in facts_list:
            merged["parties"].extend(self._normalize_fact_list(facts.get("parties", [])))
            merged["events"].extend(self._normalize_fact_list(facts.get("events", [])))
            merged["disputes"].extend(self._normalize_fact_list(facts.get("disputes", [])))
            merged["claims"].extend(self._normalize_fact_list(facts.get("claims", [])))
            merged["key_dates"].extend(self._normalize_fact_list(facts.get("key_dates", [])))
            merged["amounts"].extend(self._normalize_fact_list(facts.get("amounts", [])))
            merged["locations"].extend(self._normalize_fact_list(facts.get("locations", [])))
            summary = self._stringify_fact_value(facts.get("summary"))
            if summary:
                summaries.append(summary)

        for field in ["parties", "events", "disputes", "claims", "key_dates", "amounts", "locations"]:
            merged[field] = list(dict.fromkeys(merged[field]))

        merged["summary"] = "；".join(dict.fromkeys(summaries))[:500]
        return merged

    def _normalize_fact_list(self, values: list) -> list[str]:
        normalized = []
        for value in values or []:
            text = self._stringify_fact_value(value)
            if text:
                normalized.append(text)
        return normalized

    def _stringify_fact_value(self, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, dict):
            parts = []
            for key, item in value.items():
                item_text = self._stringify_fact_value(item)
                if item_text:
                    parts.append(f"{key}:{item_text}")
            return "，".join(parts)
        if isinstance(value, (list, tuple, set)):
            parts = [self._stringify_fact_value(item) for item in value]
            parts = [item for item in parts if item]
            return "，".join(parts)
        return str(value).strip()

    def _sanitize_keywords(self, values: list, fallback: list[str], *, for_law: bool = False) -> list[str]:
        keywords = []
        seen = set()
        for value in values or []:
            keyword = self._normalize_keyword(self._stringify_fact_value(value), for_law=for_law)
            if not keyword or keyword in seen:
                continue
            seen.add(keyword)
            keywords.append(keyword)
        if keywords:
            return keywords[:5]
        return fallback[:5]

    def _normalize_keyword(self, keyword: str, *, for_law: bool = False) -> str:
        if not keyword:
            return ""

        keyword = re.sub(r"\s+", "", keyword)
        keyword = keyword.replace("\r", "").replace("\n", "")
        keyword = re.split(r"[，。；;：:（）()【】\[\]]", keyword)[0].strip()
        keyword = re.sub(r"第[一二三四五六七八九十百千\d]+[条款项]", "", keyword)
        keyword = re.sub(r"依照.*$", "", keyword)
        keyword = re.sub(r"根据.*$", "", keyword)
        keyword = re.sub(r"应当.*$", "", keyword)
        keyword = re.sub(r"可以.*$", "", keyword)

        banned = {
            "法律责任", "处罚依据", "法律后果", "违法行为类型", "处罚措施", "责任认定", "证据材料", "主要证据",
            "事故责任", "行为认定", "违法事实", "处理结果", "赔偿责任", "承担责任", "如何处理"
        }
        if keyword in banned:
            return ""

        if len(keyword) < 2 or len(keyword) > 16:
            return ""

        if for_law:
            mapping = {
                "道路交通事故": "道路交通安全法",
                "交通事故": "道路交通安全法",
                "事故责任认定": "道路交通安全法",
                "机动车交通事故责任纠纷": "民法典侵权责任",
                "电动车交通事故": "道路交通安全法"
            }
            return mapping.get(keyword, keyword)

        return keyword

    def _extract_law_clues(self, text: str) -> list[str]:
        clues = []
        mapping_patterns = [
            (r"道路交通事故|交通事故|事故责任认定|电动车交通事故", "道路交通安全法"),
            (r"机动车交通事故责任纠纷|侵权责任|人身损害", "民法典侵权责任"),
            (r"受伤|医疗费|误工费|护理费|残疾赔偿金", "人身损害赔偿")
        ]
        for pattern, clue in mapping_patterns:
            if re.search(pattern, text) and clue not in clues:
                clues.append(clue)
        return clues[:5]

    def _pick_best_keywords(self, candidates: list[str], *, for_law: bool = False) -> list[str]:
        direct = []
        seen = set()
        for candidate in candidates:
            keyword = self._normalize_keyword(candidate, for_law=for_law)
            if keyword and keyword not in seen:
                seen.add(keyword)
                direct.append(keyword)

        prioritized = []
        for keyword in direct:
            if any(token in keyword for token in ["交通事故", "工伤", "纠纷", "合同", "借款", "处罚", "诈骗", "侵权"]):
                prioritized.append(keyword)

        result = list(dict.fromkeys(prioritized + direct))
        return result[:5]

    def _build_keyword_plan(
        self,
        query: str,
        extracted_facts: Optional[ExtractedFacts] = None,
        uploaded_files: Optional[List[FileInfo]] = None
    ) -> tuple[list[str], list[str]]:
        candidates = self._build_keyword_candidates(query, extracted_facts, uploaded_files)
        case_candidates = []
        law_candidates = []

        for text in candidates:
            case_candidates.extend(self._extract_case_clues(text))
            law_candidates.extend(self._extract_law_clues(text))

        if extracted_facts:
            case_candidates.extend(self._normalize_fact_list(extracted_facts.get("disputes", [])))
            case_candidates.extend(self._normalize_fact_list(extracted_facts.get("events", [])))
            law_candidates.extend(self._normalize_fact_list(extracted_facts.get("disputes", [])))

        case_candidates.extend(candidates)
        law_candidates.extend(candidates)

        case_keywords = self._pick_best_keywords(case_candidates, for_law=False)
        law_keywords = self._pick_best_keywords(law_candidates, for_law=True)

        if not law_keywords:
            law_keywords = case_keywords[:]
        if not case_keywords:
            case_keywords = law_keywords[:]

        return case_keywords[:5], law_keywords[:5]

    def _combine_keywords(self, primary: list[str], fallback: list[str], *, for_law: bool = False) -> list[str]:
        combined = []
        seen = set()
        for value in primary + fallback:
            keyword = self._normalize_keyword(value, for_law=for_law)
            if not keyword or keyword in seen:
                continue
            seen.add(keyword)
            combined.append(keyword)
        return combined[:5]

    def _narrow_keywords(self, keywords: list[str], *, for_law: bool = False) -> list[str]:
        narrowed = []
        seen = set()
        for keyword in keywords:
            base = self._normalize_keyword(keyword, for_law=for_law)
            if not base or base in seen:
                continue
            seen.add(base)
            narrowed.append(base)
        return narrowed[:3]

    def build_retry_keywords(
        self,
        query: str,
        extracted_facts: Optional[ExtractedFacts] = None,
        uploaded_files: Optional[List[FileInfo]] = None,
        *,
        for_law: bool = False
    ) -> list[str]:
        case_keywords, law_keywords = self._build_keyword_plan(query, extracted_facts, uploaded_files)
        return self._narrow_keywords(law_keywords if for_law else case_keywords, for_law=for_law)

    def build_search_keywords(
        self,
        query: str,
        extracted_facts: Optional[ExtractedFacts] = None,
        uploaded_files: Optional[List[FileInfo]] = None
    ) -> tuple[list[str], list[str]]:
        return self._build_keyword_plan(query, extracted_facts, uploaded_files)

    def has_search_hits(self, keywords: list[str], text: str) -> bool:
        if not text:
            return False
        joined = "".join(keywords)
        return "找到 0 条" not in text and "未找到相关" not in text and bool(joined)

    def should_retry_search(self, primary: list[str], retry: list[str]) -> bool:
        return bool(retry) and retry != primary

    def log_retry_keywords(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"检索降级重试关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_keyword_plan(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"关键词规划完成 - case: {case_keywords}, law: {law_keywords}")

    def log_llm_keywords(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"关键词生成完成 - case: {case_keywords}, law: {law_keywords}")

    def log_fallback_keywords(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"兜底关键词生成完成 - case: {case_keywords}, law: {law_keywords}")

    def log_empty_keyword_parse(self) -> None:
        logger.warning("无法解析关键词生成结果，使用兜底关键词")

    def log_keyword_error(self, error: str) -> None:
        logger.error(f"关键词生成失败: {error}")

    def log_search_retry_result(self, case_count: int, law_count: int) -> None:
        logger.info(f"检索降级重试完成 - case_count: {case_count}, law_count: {law_count}")

    def log_search_retry_skip(self) -> None:
        logger.info("检索结果为空，且没有更优降级关键词，跳过重试")

    def log_search_retry_start(self) -> None:
        logger.info("检索结果为空，开始使用更短更准的关键词重试")

    def log_search_retry_done(self) -> None:
        logger.info("检索重试流程结束")

    def log_search_primary_result(self, case_count: int, law_count: int) -> None:
        logger.info(f"首次检索完成 - case_count: {case_count}, law_count: {law_count}")

    def log_search_primary_keywords(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"准备首次检索 - case: {case_keywords}, law: {law_keywords}")

    def log_search_retry_keywords_empty(self) -> None:
        logger.info("未生成可用的降级重试关键词")

    def log_search_retry_keywords_same(self) -> None:
        logger.info("降级重试关键词与首次关键词相同，不再重复检索")

    def log_search_retry_trigger(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"触发降级检索 - case: {case_keywords}, law: {law_keywords}")

    def log_search_retry_not_needed(self) -> None:
        logger.info("首次检索已有结果，无需降级重试")

    def log_search_retry_no_result(self) -> None:
        logger.info("降级检索后仍未命中案例或法规")

    def log_search_retry_hit(self) -> None:
        logger.info("降级检索命中结果")

    def log_search_retry_candidates(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"生成降级候选关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_retry_primary_same(self) -> None:
        logger.info("降级关键词与主关键词一致，停止重试")

    def log_search_retry_primary_empty(self) -> None:
        logger.info("主关键词为空，无法执行重试")

    def log_search_retry_secondary_empty(self) -> None:
        logger.info("重试关键词为空，无法执行重试")

    def log_search_retry_state(self, primary_case: list[str], primary_law: list[str], retry_case: list[str], retry_law: list[str]) -> None:
        logger.info(f"检索重试状态 - primary_case: {primary_case}, primary_law: {primary_law}, retry_case: {retry_case}, retry_law: {retry_law}")

    def log_search_no_result(self, case_count: int, law_count: int) -> None:
        logger.info(f"检索无结果 - case_count: {case_count}, law_count: {law_count}")

    def log_search_with_result(self, case_count: int, law_count: int) -> None:
        logger.info(f"检索有结果 - case_count: {case_count}, law_count: {law_count}")

    def log_search_plan_result(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"最终检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_merge(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"合并后的检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_retry_merge(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试合并后的检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_filter(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"过滤后的检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_filter_retry(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试过滤后的检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_llm(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"LLM原始检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_retry_llm(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"LLM重试检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_fallback(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"兜底规划检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_final(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"最终采用检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_retry_final(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试最终采用检索关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_strategy(self) -> None:
        logger.info("关键词策略：优先案由、其次争议、再次事实")

    def log_search_keyword_strategy_retry(self) -> None:
        logger.info("重试关键词策略：缩短为案由级关键词")

    def log_search_keyword_strategy_law(self) -> None:
        logger.info("法规关键词策略：映射到法名或法域")

    def log_search_keyword_strategy_case(self) -> None:
        logger.info("案例关键词策略：映射到案由或裁判争点")

    def log_search_keyword_strategy_complete(self) -> None:
        logger.info("关键词策略生成完成")

    def log_search_keyword_strategy_retry_complete(self) -> None:
        logger.info("重试关键词策略生成完成")

    def log_search_keyword_source(self, source: str) -> None:
        logger.info(f"关键词来源: {source}")

    def log_search_keyword_source_retry(self, source: str) -> None:
        logger.info(f"重试关键词来源: {source}")

    def log_search_keyword_source_complete(self) -> None:
        logger.info("关键词来源分析完成")

    def log_search_keyword_source_retry_complete(self) -> None:
        logger.info("重试关键词来源分析完成")

    def log_search_keyword_trim(self, keyword: str, trimmed: str) -> None:
        logger.info(f"关键词裁剪 - before: {keyword}, after: {trimmed}")

    def log_search_keyword_drop(self, keyword: str) -> None:
        logger.info(f"关键词丢弃 - keyword: {keyword}")

    def log_search_keyword_keep(self, keyword: str) -> None:
        logger.info(f"关键词保留 - keyword: {keyword}")

    def log_search_keyword_complete(self) -> None:
        logger.info("关键词清洗完成")

    def log_search_keyword_retry_complete_final(self) -> None:
        logger.info("重试关键词清洗完成")

    def log_search_keyword_law_map(self, keyword: str, mapped: str) -> None:
        logger.info(f"法规关键词映射 - before: {keyword}, after: {mapped}")

    def log_search_keyword_case_map(self, keyword: str, mapped: str) -> None:
        logger.info(f"案例关键词映射 - before: {keyword}, after: {mapped}")

    def log_search_keyword_narrow(self, keyword: str, narrowed: str) -> None:
        logger.info(f"关键词收窄 - before: {keyword}, after: {narrowed}")

    def log_search_keyword_narrow_complete(self) -> None:
        logger.info("关键词收窄完成")

    def log_search_keyword_retry_plan(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试关键词规划完成 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_plan_complete(self) -> None:
        logger.info("检索关键词规划完成")

    def log_search_keyword_retry_plan_complete(self) -> None:
        logger.info("重试检索关键词规划完成")

    def log_search_keyword_api_fit(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"适配API后的关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_api_fit_retry(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试适配API后的关键词 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_api_done(self) -> None:
        logger.info("关键词API适配完成")

    def log_search_keyword_api_retry_done(self) -> None:
        logger.info("重试关键词API适配完成")

    def log_search_keyword_quality(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"关键词质量检查 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_quality_retry(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试关键词质量检查 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_quality_done(self) -> None:
        logger.info("关键词质量检查完成")

    def log_search_keyword_quality_retry_done(self) -> None:
        logger.info("重试关键词质量检查完成")

    def log_search_keyword_summary(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"关键词总结 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_summary_retry(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试关键词总结 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_summary_done(self) -> None:
        logger.info("关键词总结完成")

    def log_search_keyword_summary_retry_done(self) -> None:
        logger.info("重试关键词总结完成")

    def log_search_keyword_finalize(self) -> None:
        logger.info("关键词生成流程完成")

    def log_search_keyword_retry_finalize(self) -> None:
        logger.info("重试关键词生成流程完成")

    def log_search_keyword_end(self) -> None:
        logger.info("关键词阶段结束")

    def log_search_keyword_retry_end(self) -> None:
        logger.info("重试关键词阶段结束")

    def log_search_keyword_primary_end(self) -> None:
        logger.info("首次关键词阶段结束")

    def log_search_keyword_retry_start(self) -> None:
        logger.info("开始生成重试关键词")

    def log_search_keyword_retry_end_complete(self) -> None:
        logger.info("重试关键词生成结束")

    def log_search_keyword_case_only(self, keywords: list[str]) -> None:
        logger.info(f"仅案例关键词: {keywords}")

    def log_search_keyword_law_only(self, keywords: list[str]) -> None:
        logger.info(f"仅法规关键词: {keywords}")

    def log_search_keyword_case_retry_only(self, keywords: list[str]) -> None:
        logger.info(f"仅案例重试关键词: {keywords}")

    def log_search_keyword_law_retry_only(self, keywords: list[str]) -> None:
        logger.info(f"仅法规重试关键词: {keywords}")

    def log_search_keyword_case_final_only(self, keywords: list[str]) -> None:
        logger.info(f"最终案例关键词: {keywords}")

    def log_search_keyword_law_final_only(self, keywords: list[str]) -> None:
        logger.info(f"最终法规关键词: {keywords}")

    def log_search_keyword_case_retry_final_only(self, keywords: list[str]) -> None:
        logger.info(f"重试最终案例关键词: {keywords}")

    def log_search_keyword_law_retry_final_only(self, keywords: list[str]) -> None:
        logger.info(f"重试最终法规关键词: {keywords}")

    def log_search_keyword_ready(self) -> None:
        logger.info("关键词已准备完成")

    def log_search_keyword_retry_ready(self) -> None:
        logger.info("重试关键词已准备完成")

    def log_search_keyword_pipeline_end(self) -> None:
        logger.info("关键词流水线结束")

    def log_search_keyword_retry_pipeline_end(self) -> None:
        logger.info("重试关键词流水线结束")

    def log_search_keyword_monitor(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"关键词监控 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_retry_monitor(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试关键词监控 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_metrics(self, case_count: int, law_count: int) -> None:
        logger.info(f"关键词命中指标 - case_count: {case_count}, law_count: {law_count}")

    def log_search_keyword_retry_metrics(self, case_count: int, law_count: int) -> None:
        logger.info(f"重试关键词命中指标 - case_count: {case_count}, law_count: {law_count}")

    def log_search_keyword_record(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"关键词记录 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_retry_record(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试关键词记录 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_observe(self) -> None:
        logger.info("关键词观察完成")

    def log_search_keyword_retry_observe(self) -> None:
        logger.info("重试关键词观察完成")

    def log_search_keyword_recall(self, case_count: int, law_count: int) -> None:
        logger.info(f"关键词召回结果 - case_count: {case_count}, law_count: {law_count}")

    def log_search_keyword_retry_recall(self, case_count: int, law_count: int) -> None:
        logger.info(f"重试关键词召回结果 - case_count: {case_count}, law_count: {law_count}")

    def log_search_keyword_traffic(self) -> None:
        logger.info("关键词流量路径完成")

    def log_search_keyword_retry_traffic(self) -> None:
        logger.info("重试关键词流量路径完成")

    def log_search_keyword_close(self) -> None:
        logger.info("关键词环节关闭")

    def log_search_keyword_retry_close(self) -> None:
        logger.info("重试关键词环节关闭")

    def log_search_keyword_case_domain(self) -> None:
        logger.info("案例关键词域：案由与争点")

    def log_search_keyword_law_domain(self) -> None:
        logger.info("法规关键词域：法名与法域")

    def log_search_keyword_retry_case_domain(self) -> None:
        logger.info("重试案例关键词域：案由")

    def log_search_keyword_retry_law_domain(self) -> None:
        logger.info("重试法规关键词域：法名")

    def log_search_keyword_domain_done(self) -> None:
        logger.info("关键词域分析完成")

    def log_search_keyword_retry_domain_done(self) -> None:
        logger.info("重试关键词域分析完成")

    def log_search_keyword_snapshot(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"关键词快照 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_retry_snapshot(self, case_keywords: list[str], law_keywords: list[str]) -> None:
        logger.info(f"重试关键词快照 - case: {case_keywords}, law: {law_keywords}")

    def log_search_keyword_finish(self) -> None:
        logger.info("关键词任务完成")

    def log_search_keyword_retry_finish(self) -> None:
        logger.info("重试关键词任务完成")

    def _extract_case_clues(self, text: str) -> list[str]:
        patterns = [
            r"道路交通事故[^，。；\n]{0,20}",
            r"交通事故[^，。；\n]{0,20}",
            r"劳动争议[^，。；\n]{0,20}",
            r"工伤[^，。；\n]{0,20}",
            r"合同纠纷[^，。；\n]{0,20}",
            r"借款纠纷[^，。；\n]{0,20}",
            r"行政处罚[^，。；\n]{0,20}",
            r"诈骗[^，。；\n]{0,20}",
            r"侵权责任[^，。；\n]{0,20}"
        ]
        clues = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                clue = match.strip("，。；：:、 ")
                if clue and clue not in clues:
                    clues.append(clue)
        return clues[:5]

    def _build_keyword_candidates(
        self,
        query: str,
        extracted_facts: Optional[ExtractedFacts] = None,
        uploaded_files: Optional[List[FileInfo]] = None
    ) -> list[str]:
        candidates = []
        if extracted_facts:
            candidates.extend(self._normalize_fact_list(extracted_facts.get("disputes", [])))
            candidates.extend(self._normalize_fact_list(extracted_facts.get("events", [])))
            candidates.extend(self._normalize_fact_list(extracted_facts.get("claims", [])))
            candidates.extend(self._normalize_fact_list(extracted_facts.get("parties", [])))
            summary = self._stringify_fact_value(extracted_facts.get("summary"))
            if summary:
                candidates.extend(self._extract_case_clues(summary))
                candidates.append(summary)

        for file_info in uploaded_files or []:
            extracted_text = (file_info.get("extracted_text") or "")[:1500]
            if extracted_text:
                candidates.extend(self._extract_case_clues(extracted_text))
                candidates.append(extracted_text)

        if query:
            candidates.append(query)

        return candidates

    async def generate_search_keywords(
        self,
        user_question: str,
        extracted_facts: Optional[ExtractedFacts],
        uploaded_files: Optional[List[FileInfo]] = None
    ) -> tuple[List[str], List[str]]:
        facts_text = CyberJudgePrompts.format_extracted_facts(extracted_facts)
        file_context = self._build_file_context(uploaded_files or [])

        if not extracted_facts and file_context == "（未提供文档内容）":
            return self._quick_generate_keywords(user_question)

        prompt = CyberJudgePrompts.KEYWORD_GENERATION_PROMPT.format(
            user_question=user_question,
            extracted_facts=facts_text,
            file_context=file_context
        )

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content
            result = self._parse_json_result(content)
            if result:
                fallback_case, fallback_law = self.build_search_keywords(
                    user_question,
                    extracted_facts=extracted_facts,
                    uploaded_files=uploaded_files
                )
                self.log_keyword_plan(fallback_case, fallback_law)
                case_keywords = self._combine_keywords(
                    self._sanitize_keywords(result.get("case_keywords", []), fallback_case, for_law=False),
                    fallback_case,
                    for_law=False
                )
                law_keywords = self._combine_keywords(
                    self._sanitize_keywords(result.get("law_keywords", []), fallback_law, for_law=True),
                    fallback_law,
                    for_law=True
                )

                self.log_llm_keywords(case_keywords, law_keywords)
                return case_keywords, law_keywords

            self.log_empty_keyword_parse()
        except Exception as e:
            self.log_keyword_error(str(e))

        case_keywords, law_keywords = self._quick_generate_keywords(
            user_question,
            extracted_facts=extracted_facts,
            uploaded_files=uploaded_files
        )
        self.log_fallback_keywords(case_keywords, law_keywords)
        return case_keywords, law_keywords

    def _quick_generate_keywords(
        self,
        query: str,
        extracted_facts: Optional[ExtractedFacts] = None,
        uploaded_files: Optional[List[FileInfo]] = None
    ) -> tuple[List[str], List[str]]:
        case_keywords, law_keywords = self.build_search_keywords(query, extracted_facts, uploaded_files)
        if not case_keywords and query:
            case_keywords = [query[:12]]
        if not law_keywords:
            law_keywords = case_keywords[:]
        return case_keywords[:5], law_keywords[:5]

    def _build_file_context(self, uploaded_files: List[FileInfo]) -> str:
        if not uploaded_files:
            return "（未提供文档内容）"

        parts = []
        for index, file_info in enumerate(uploaded_files[:3], 1):
            filename = file_info.get("filename", f"文件{index}")
            extracted_text = (file_info.get("extracted_text") or "").strip()
            excerpt = extracted_text[:800] if extracted_text else "（文档未提取到文本）"
            parts.append(f"文档{index}：{filename}\n{excerpt}")

        return "\n\n".join(parts)

    def _get_file_type(self, filename: str) -> str:
        ext = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
        type_map = {
            'pdf': 'pdf',
            'doc': 'word',
            'docx': 'word',
            'txt': 'text',
            'md': 'markdown',
            'xls': 'excel',
            'xlsx': 'excel'
        }
        return type_map.get(ext, ext)

    def _create_empty_file_info(self, file_path: str, filename: str) -> FileInfo:
        return FileInfo(
            filename=filename,
            file_type=self._get_file_type(filename),
            file_path=file_path,
            extracted_text="",
            extracted_text_length=0
        )

    def _create_empty_facts(self) -> ExtractedFacts:
        return ExtractedFacts(
            parties=[],
            events=[],
            disputes=[],
            claims=[],
            key_dates=[],
            amounts=[],
            locations=[],
            summary=""
        )

    def _get_default_facts(self, text: str) -> dict:
        summary = text[:100] + "..." if len(text) > 100 else text
        return {
            "parties": [],
            "events": [],
            "disputes": [],
            "claims": [],
            "key_dates": [],
            "amounts": [],
            "locations": [],
            "summary": summary
        }
