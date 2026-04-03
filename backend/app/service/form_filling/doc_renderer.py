from typing import Dict, Any, Optional
from docxtpl import DocxTemplate
from pathlib import Path
import os
from app.core.logger import get_logger
from datetime import datetime

logger = get_logger("doc_renderer")


class DocRenderer:
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            self.template_dir = Path(__file__).parent.parent.parent.parent / "data"
        else:
            self.template_dir = Path(template_dir)
        
        self.output_dir = Path(__file__).parent.parent.parent.parent / "outputs"
        self.output_dir.mkdir(exist_ok=True)

    def render_document(
        self,
        template_file: str,
        slot_data: Dict[str, Any],
        output_filename: Optional[str] = None
    ) -> str:
        """
        将槽位数据填充到Word模板中（使用Jinja2语法）
        """
        try:
            template_path = self.template_dir / template_file
            if not template_path.exists():
                logger.error(f"模板文件不存在 - template_path: {template_path}")
                raise FileNotFoundError(f"模板文件不存在: {template_file}")

            logger.info(f"开始渲染文档 - template: {template_file}, output: {output_filename}")

            doc = DocxTemplate(str(template_path))

            nested_data = self._flatten_to_nested(slot_data)
            logger.info(f"槽位数据转换完成 - nested_keys: {list(nested_data.keys())}")

            doc.render(nested_data)

            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"filled_document_{timestamp}.docx"

            output_path = self.output_dir / output_filename
            doc.save(str(output_path))

            logger.info(f"文档渲染完成 - output_path: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"文档渲染失败 - error: {str(e)}")
            raise

    def _flatten_to_nested(self, flat_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将扁平的槽位名称转换为嵌套的字典结构
        例如：plaintiff.name -> {"plaintiff": {"name": value}}
        """
        nested = {}
        
        for key, value in flat_data.items():
            if value is None:
                continue
                
            parts = key.split(".")
            current = nested
            
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            current[parts[-1]] = value
        
        return nested

    def format_value(self, value: Any) -> str:
        """
        格式化值以便显示
        """
        if value is None:
            return ""
        
        if isinstance(value, bool):
            return "是" if value else "否"
        
        if isinstance(value, list):
            return "、".join(str(v) for v in value)
        
        if isinstance(value, dict):
            if "value" in value:
                return self.format_value(value["value"])
            return str(value)
        
        return str(value)

    def get_template_file(self, template_type: str) -> Optional[str]:
        """
        根据模板类型获取模板文件名
        """
        template_files = {
            "labor_dispute": "Labour_Litigation_Template.docx"
        }
        return template_files.get(template_type)

    def extract_slots_from_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从会话数据中提取所有槽位值
        """
        slot_values = {}

        blocks = session_data.get("blocks", {})
        for block_id, block_data in blocks.items():
            slots = block_data.get("slots", {})
            for slot_name, slot_status in slots.items():
                if slot_status.get("value") is not None:
                    slot_values[f"{block_id}.{slot_name}"] = slot_status["value"]

        inferred_data = session_data.get("inferred", {})
        for key, value in inferred_data.items():
            if value:
                slot_values[f"inferred_{key}"] = value

        return slot_values

    def validate_template(self, template_file: str) -> Dict[str, Any]:
        """
        验证模板文件的有效性
        """
        template_path = self.template_dir / template_file
        if not template_path.exists():
            return {
                "valid": False,
                "error": f"模板文件不存在: {template_file}"
            }

        try:
            doc = DocxTemplate(str(template_path))
            
            return {
                "valid": True,
                "message": "模板文件有效"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"模板文件损坏或格式错误: {str(e)}"
            }

    def cleanup_old_files(self, days: int = 7):
        """
        清理旧的输出文件
        """
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)

            for file_path in self.output_dir.glob("*.docx"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.info(f"删除旧文件 - file: {file_path}")

        except Exception as e:
            logger.error(f"清理旧文件失败 - error: {str(e)}")


_doc_renderer_instance = None


def get_doc_renderer() -> DocRenderer:
    global _doc_renderer_instance
    if _doc_renderer_instance is None:
        _doc_renderer_instance = DocRenderer()
    return _doc_renderer_instance
