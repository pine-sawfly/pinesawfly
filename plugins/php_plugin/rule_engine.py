import json
import logging
import os
from typing import List, Dict, Any
from core.exception_handler import safe_operation

logger = logging.getLogger(__name__)

class RuleEngine:
    """
    规则引擎，用于根据预定义规则扫描代码
    """
    
    def __init__(self, rules_file: str = None):
        if rules_file is None:
            # 使用默认规则文件路径
            rules_file = os.path.join(os.path.dirname(__file__), 'rules', 'default_rules.json')
        self.rules_file = rules_file
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[Dict[str, Any]]:
        """
        从JSON文件加载规则
        """
        try:
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    rules = data.get('rules', [])
                    logger.info(f"从 {self.rules_file} 加载了 {len(rules)} 条规则")
                    return rules
            else:
                # 如果规则文件不存在，使用默认规则
                default_rules = self._get_default_rules()
                logger.info(f"规则文件 {self.rules_file} 不存在，使用默认规则")
                return default_rules
        except Exception as e:
            logger.error(f"加载规则文件 {self.rules_file} 失败: {str(e)}")
            # 出错时返回默认规则
            return self._get_default_rules()
    
    def _get_default_rules(self) -> List[Dict[str, Any]]:
        """
        获取默认规则
        """
        default_rules = [
            {
                "id": "PHP001",
                "name": "危险函数调用",
                "type": "AST",
                "pattern": "FunctionCall[name='eval']",
                "severity": "Critical",
                "description": "检测到eval函数调用，可能导致代码注入"
            },
            {
                "id": "PHP002",
                "name": "文件包含漏洞",
                "type": "AST",
                "pattern": "FunctionCall[name='include']",
                "severity": "High",
                "description": "检测到include函数调用，可能存在文件包含漏洞"
            },
            {
                "id": "PHP003",
                "name": "命令执行函数",
                "type": "AST",
                "pattern": "FunctionCall[name='exec']",
                "severity": "High",
                "description": "检测到exec函数调用，可能导致命令执行"
            },
            {
                "id": "PHP004",
                "name": "系统命令函数",
                "type": "AST",
                "pattern": "FunctionCall[name='system']",
                "severity": "High",
                "description": "检测到system函数调用，可能导致命令执行"
            },
            {
                "id": "PHP005",
                "name": "反序列化漏洞",
                "type": "AST",
                "pattern": "FunctionCall[name='unserialize']",
                "severity": "High",
                "description": "检测到unserialize函数调用，可能存在反序列化漏洞"
            },
            {
                "id": "PHP006",
                "name": "任意文件读取风险",
                "type": "AST",
                "pattern": "FunctionCall[name='file_get_contents|fopen|readfile|fgets|fread|parse_ini_file|highlight_file|fgetss|show_source']",
                "severity": "High",
                "description": "检测到文件读取函数调用，参数包含变量，可能存在任意文件读取漏洞"
            }
        ]
        return default_rules
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """
        获取所有规则
        """
        return self.rules
    
    @safe_operation
    def scan(self, ast, file_path: str) -> List[Dict[str, Any]]:
        """
        根据规则扫描AST
        """
        results = []
        
        for rule in self.rules:
            try:
                matches = self._match_rule(ast, rule)
                for match in matches:
                    results.append({
                        "rule_id": rule["id"],
                        "rule_name": rule["name"],
                        "severity": rule["severity"],
                        "file": file_path,
                        "line": match.get("line", 0),
                        "description": rule["description"],
                        "details": match
                    })
            except Exception as e:
                logger.error(f"应用规则 {rule['id']} 时出错: {str(e)}")
        
        logger.info(f"规则引擎在文件 {file_path} 中发现 {len(results)} 个问题")
        return results
    
    def _match_rule(self, ast, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        在AST中匹配特定规则
        """
        matches = []
        pattern = rule.get("pattern", "")
        
        # 解析简单的AST模式
        # 例如: FunctionCall[name='eval']
        if pattern.startswith("FunctionCall"):
            matches.extend(self._match_function_call(ast, pattern))
        
        return matches
    
    def _match_function_call(self, ast, pattern: str) -> List[Dict[str, Any]]:
        """
        匹配函数调用节点
        """
        matches = []
        
        # 解析模式，例如: FunctionCall[name='eval']
        if "[name=" in pattern and "]" in pattern:
            start = pattern.find("[name='") + 7
            end = pattern.find("']", start)
            if start > 6 and end > start:  # 6是因为"[name='"的长度是7
                target_function = pattern[start:end]
                
                # 遍历AST查找匹配的函数调用
                def traverse(node, path=""):
                    if hasattr(node, '__dict__'):
                        # 检查节点是否为函数调用且名称匹配
                        if self._is_matching_function_call(node, target_function):
                            matches.append({
                                "node_type": type(node).__name__,
                                "line": getattr(node, 'lineno', 0),
                                "path": path,
                                "function_name": target_function
                            })
                        
                        # 递归遍历子节点
                        for key, value in node.__dict__.items():
                            if hasattr(value, '__dict__') or isinstance(value, list):
                                traverse(value, f"{path}.{key}" if path else key)
                    elif isinstance(node, list):
                        for i, item in enumerate(node):
                            traverse(item, f"{path}[{i}]")
                
                traverse(ast)
        
        return matches
    
    def _is_matching_function_call(self, node, target_function: str) -> bool:
        """
        检查节点是否为匹配的函数调用
        """
        # 检查是否为函数调用节点
        if type(node).__name__ == "FunctionCall":
            # 检查函数名是否匹配
            func_name = getattr(node, 'name', '')
            return func_name == target_function
        return False