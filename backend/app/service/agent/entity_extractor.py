import os
import re
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.core.logger import get_logger

logger = get_logger("entity_extractor")

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False
    logger.warning("transformers库未安装，NER模型不可用，将使用规则匹配")

MODELS_DIR = Path(__file__).parent.parent.parent.parent / "huggingface_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

NER_MODEL_DIR = MODELS_DIR / "ner_model"


class LegalEntity(BaseModel):
    entity_type: str
    entity_value: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0


class EntityResult(BaseModel):
    entities: Dict[str, Any] = {}
    entities_list: List[LegalEntity] = []
    confidence: float = 0.0
    extraction_time: float = 0.0
    method: str = "rule"


LEGAL_ENTITY_PATTERNS = {
    "law_name": [
        r"《([^《》]+法)》",
        r"([^，。！？\s]{2,10}法)",
        r"(民法典|刑法|行政法|宪法|公司法|合同法|劳动法|劳动合同法|知识产权法|商标法|专利法|著作权法)",
    ],
    "article": [
        r"(第[一二三四五六七八九十百零〇]+条)",
        r"(第\d+条)",
        r"(第[一二三四五六七八九十百零〇]+款)",
        r"(第\d+款)",
    ],
    "topic": [
        r"(经济补偿金|赔偿金|违约金|工资|加班费|年终奖|绩效奖金)",
        r"(解除劳动合同|终止劳动合同|辞退|开除|离职|辞职)",
        r"(工伤|职业病|医疗期|病假|产假|年假)",
        r"(知识产权|专利权|商标权|著作权|侵权)",
        r"(合同纠纷|劳动纠纷|债务纠纷|房产纠纷)",
    ],
    "case_type": [
        r"(劳动争议|劳动仲裁|劳动合同纠纷)",
        r"(合同纠纷|买卖合同纠纷|租赁合同纠纷)",
        r"(侵权纠纷|知识产权纠纷)",
        r"(婚姻家庭|继承纠纷|离婚纠纷)",
        r"(债权债务|借贷纠纷)",
    ],
    "amount": [
        r"(\d+(?:\.\d+)?(?:万|千|百)?元)",
        r"(\d+(?:\.\d+)?个月?(?:工资|薪金))",
        r"(\d+(?:\.\d+)?%的?(?:违约金|赔偿金))",
    ],
    "time_period": [
        r"(\d+年)",
        r"(\d+个月)",
        r"(\d+天)",
        r"(诉讼时效|仲裁时效|除斥期间)",
    ],
    "action": [
        r"(计算|如何计算|怎么计算)",
        r"(赔偿|补偿|追偿)",
        r"(解除|终止|撤销|无效)",
        r"(起诉|上诉|申诉|仲裁)",
    ],
}

CLUENER_LABEL_MAPPING = {
    "address": "address",
    "book": "book",
    "company": "company",
    "game": "game",
    "government": "government",
    "movie": "movie",
    "name": "name",
    "organization": "organization",
    "position": "position",
    "scene": "scene",
}


class EntityExtractor:
    def __init__(self, use_ner: bool = True, model_name: str = "uer/roberta-base-finetuned-cluener2020-chinese"):
        self.use_ner = use_ner and NER_AVAILABLE
        self.ner_pipeline = None
        self.model_name = model_name
        self.local_model_path = NER_MODEL_DIR

        if self.use_ner:
            self._init_ner_model()

        logger.info(f"实体识别模块初始化完成 - use_ner: {self.use_ner}")

    def _init_ner_model(self):
        try:
            logger.info(f"正在加载NER模型: {self.model_name}")
            start_time = time.time()

            if self._is_model_cached():
                logger.info(f"从本地缓存加载NER模型: {self.local_model_path}")
                self.ner_pipeline = pipeline(
                    "ner",
                    model=str(self.local_model_path),
                    tokenizer=str(self.local_model_path),
                    aggregation_strategy="simple"
                )
            else:
                logger.info(f"首次运行，从Hugging Face下载NER模型到: {self.local_model_path}")
                self._download_and_cache_model()
                self.ner_pipeline = pipeline(
                    "ner",
                    model=str(self.local_model_path),
                    tokenizer=str(self.local_model_path),
                    aggregation_strategy="simple"
                )

            load_time = time.time() - start_time
            logger.info(f"NER模型加载完成 - time: {load_time:.2f}s")

        except Exception as e:
            logger.error(f"NER模型加载失败: {str(e)}")
            self.use_ner = False
            self.ner_pipeline = None

    def _is_model_cached(self) -> bool:
        config_file = self.local_model_path / "config.json"
        model_file = self.local_model_path / "pytorch_model.bin"
        tokenizer_file = self.local_model_path / "tokenizer.json"
        
        return config_file.exists() and (model_file.exists() or (self.local_model_path / "model.safetensors").exists()) and tokenizer_file.exists()

    def _download_and_cache_model(self):
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForTokenClassification.from_pretrained(self.model_name)
            
            self.local_model_path.mkdir(parents=True, exist_ok=True)
            
            tokenizer.save_pretrained(str(self.local_model_path))
            model.save_pretrained(str(self.local_model_path))
            
            logger.info(f"NER模型已保存到本地: {self.local_model_path}")
            
        except Exception as e:
            logger.error(f"下载NER模型失败: {str(e)}")
            raise

    async def extract(self, query: str) -> EntityResult:
        start_time = time.time()
        logger.info(f"实体识别开始 - query: {query[:50]}")

        entities = {}
        entities_list = []
        method = "rule"

        rule_entities = self._extract_by_rules(query)
        entities.update(rule_entities)

        if self.use_ner and self.ner_pipeline:
            try:
                ner_entities = await self._extract_by_ner(query)
                for entity in ner_entities:
                    if entity.entity_type not in entities:
                        entities[entity.entity_type] = entity.entity_value
                        entities_list.append(entity)
                method = "rule+ner"
            except Exception as e:
                logger.error(f"NER提取失败: {str(e)}")

        for entity_type, entity_value in entities.items():
            if not any(e.entity_type == entity_type for e in entities_list):
                entities_list.append(LegalEntity(
                    entity_type=entity_type,
                    entity_value=entity_value,
                    confidence=0.9
                ))

        extraction_time = time.time() - start_time
        confidence = 0.95 if method == "rule+ner" else 0.85

        logger.info(f"实体识别完成 - entities: {entities}, method: {method}, time: {extraction_time:.3f}s")

        return EntityResult(
            entities=entities,
            entities_list=entities_list,
            confidence=confidence,
            extraction_time=extraction_time,
            method=method
        )

    def _extract_by_rules(self, query: str) -> Dict[str, str]:
        entities = {}

        for entity_type, patterns in LEGAL_ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, query)
                if matches:
                    entities[entity_type] = matches[0]
                    break

        return entities

    async def _extract_by_ner(self, query: str) -> List[LegalEntity]:
        if not self.ner_pipeline:
            return []

        results = self.ner_pipeline(query)

        entities = []
        for result in results:
            entity_type = result.get("entity_group", "").lower()
            entity_value = result.get("word", "")
            confidence = result.get("score", 0.0)
            start = result.get("start", 0)
            end = result.get("end", 0)

            if entity_type in CLUENER_LABEL_MAPPING:
                mapped_type = self._map_to_legal_entity(entity_type, entity_value)
                if mapped_type:
                    entities.append(LegalEntity(
                        entity_type=mapped_type,
                        entity_value=entity_value,
                        start=start,
                        end=end,
                        confidence=confidence
                    ))

        return entities

    def _map_to_legal_entity(self, ner_type: str, entity_value: str) -> Optional[str]:
        if ner_type in ["organization", "company", "government"]:
            if "法院" in entity_value or "仲裁" in entity_value:
                return "court"
            return "organization"

        if ner_type == "name":
            return "person_name"

        if ner_type == "position":
            return "position"

        return None

    def build_retrieval_filter(self, entity_result: EntityResult) -> Optional[Dict[str, Any]]:
        entities = entity_result.entities
        filters = {}

        if "law_name" in entities:
            filters["law_name"] = entities["law_name"]

        if "case_type" in entities:
            filters["case_type"] = entities["case_type"]

        return filters if filters else None

    def enhance_query(self, query: str, entity_result: EntityResult) -> str:
        entities = entity_result.entities

        enhanced_parts = [query]

        if "topic" in entities and entities["topic"] not in query:
            enhanced_parts.append(entities["topic"])

        if "law_name" in entities and entities["law_name"] not in query:
            enhanced_parts.append(entities["law_name"])

        return " ".join(enhanced_parts) if len(enhanced_parts) > 1 else query
