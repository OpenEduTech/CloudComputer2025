import json
import jsonschema
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class GraphJSONValidator:
    """GraphJSON Schema校验器"""
    
    def __init__(self):
        # 从文件中加载Schema，或使用硬编码
        self.schema = self._load_schema()
    
    def _load_schema(self) -> Dict[str, Any]:
        """加载Schema定义"""
        # 这里使用graph.schema.json的内容
        # 实际项目中应该从文件加载
        schema_path = Path(__file__).parent.parent.parent / "graph.schema.json"
        if schema_path.exists():
            with open(schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 返回简化的Schema结构（用于开发）
            return {
                "$schema": "http://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": ["meta", "nodes", "edges"],
                "properties": {
                    "meta": {"type": "object"},
                    "nodes": {"type": "array"},
                    "edges": {"type": "array"}
                }
            }
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """验证数据是否符合Schema"""
        try:
            jsonschema.validate(instance=data, schema=self.schema)
            return True, "验证通过"
        except jsonschema.ValidationError as e:
            error_msg = f"Schema验证失败: {e.message} (路径: {e.json_path})"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Schema验证异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_schema_info(self) -> Dict[str, Any]:
        """获取Schema信息"""
        return {
            "schema_version": self.schema.get("$id", "unknown"),
            "required_fields": self.schema.get("required", []),
            "nodes_min": self.schema.get("properties", {})
                .get("nodes", {}).get("minItems", 0),
            "nodes_max": self.schema.get("properties", {})
                .get("nodes", {}).get("maxItems", "unlimited"),
            "edges_min": self.schema.get("properties", {})
                .get("edges", {}).get("minItems", 0),
        }

validator = GraphJSONValidator()