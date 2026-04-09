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
        if len(text) > self.chunk_size:
            text = text[:self.chunk_size]
            logger.info(f"文本过长，截取前{self.chunk_size}字符进行事实提取")
        
        prompt = CyberJudgePrompts.FACT_EXTRACTION_PROMPT.format(text_content=text)
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content
            
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                logger.warning("无法解析事实提取结果，使用默认值")
                result = self._get_default_facts(text)
        except Exception as e:
            logger.error(f"事实提取LLM调用失败: {str(e)}")
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

    async def generate_search_keywords(
        self,
        user_question: str,
        extracted_facts: Optional[ExtractedFacts]
    ) -> tuple[List[str], List[str]]:
        if not extracted_facts:
            return self._quick_generate_keywords(user_question)
        
        facts_text = CyberJudgePrompts.format_extracted_facts(extracted_facts)
        
        prompt = CyberJudgePrompts.KEYWORD_GENERATION_PROMPT.format(
            user_question=user_question,
            extracted_facts=facts_text
        )
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content
            
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                case_keywords = result.get("case_keywords", [])
                law_keywords = result.get("law_keywords", [])
                
                if not case_keywords:
                    case_keywords = self._quick_generate_keywords(user_question)[0]
                if not law_keywords:
                    law_keywords = self._quick_generate_keywords(user_question)[1]
                
                logger.info(f"关键词生成完成 - case: {case_keywords}, law: {law_keywords}")
                return case_keywords, law_keywords
        except Exception as e:
            logger.error(f"关键词生成失败: {str(e)}")
        
        return self._quick_generate_keywords(user_question)

    def _quick_generate_keywords(self, query: str) -> tuple[List[str], List[str]]:
        stop_words = {"的", "了", "是", "在", "有", "和", "与", "或", "我", "你", "他", "她", "它", "这", "那", "什么", "怎么", "如何", "为什么", "吗", "呢", "啊", "吧"}
        
        words = []
        for word in re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', query):
            if word not in stop_words and len(word) > 1:
                words.append(word)
        
        keywords = list(set(words))[:5]
        
        return keywords, keywords

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
