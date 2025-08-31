import json
import logging
import os
import re
from typing import List, Dict, Any
from core.exception_handler import safe_operation

logger = logging.getLogger(__name__)

class GenericRuleEngine:
    """
    通用规则引擎，支持多种语言的静态代码分析
    """
    
    def __init__(self, rules_dir: str = None):
        if rules_dir is None:
            # 使用默认规则目录路径
            rules_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rules')
        self.rules_dir = rules_dir
        self.rules = {}
        self._load_all_rules()
    
    def _load_all_rules(self):
        """
        加载所有语言的规则
        """
        if not os.path.exists(self.rules_dir):
            logger.warning(f"规则目录 {self.rules_dir} 不存在")
            return
            
        for file_name in os.listdir(self.rules_dir):
            if file_name.endswith('_rules.json'):
                language = file_name.replace('_rules.json', '')
                file_path = os.path.join(self.rules_dir, file_name)
                self.rules[language] = self._load_rules_from_file(file_path)
    
    def _load_rules_from_file(self, rules_file: str) -> List[Dict[str, Any]]:
        """
        从JSON文件加载规则
        """
        try:
            if os.path.exists(rules_file):
                with open(rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    rules = data.get('rules', [])
                    logger.info(f"从 {rules_file} 加载了 {len(rules)} 条规则")
                    return rules
            else:
                logger.warning(f"规则文件 {rules_file} 不存在")
                return []
        except Exception as e:
            logger.error(f"加载规则文件 {rules_file} 失败: {str(e)}")
            return []
    
    def get_rules_by_language(self, language: str) -> List[Dict[str, Any]]:
        """
        根据语言获取规则
        """
        return self.rules.get(language, [])
    
    def get_all_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取所有规则
        """
        return self.rules
    
    @safe_operation
    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        根据文件后缀名选择对应规则进行扫描
        """
        # 根据文件扩展名确定语言
        extension = os.path.splitext(file_path)[1].lower()
        language_map = {
            '.php': 'php',
            '.py': 'python',
            '.java': 'java'
        }
        language = language_map.get(extension)
        
        if not language or language not in self.rules:
            logger.info(f"不支持的语言或无对应规则: {extension}")
            return []
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        # 使用对应语言的规则进行扫描
        language_rules = self.rules[language]
        results = []
        
        for rule in language_rules:
            try:
                matches = self._match_rule(content, rule, file_path)
                results.extend(matches)
            except Exception as e:
                logger.error(f"应用规则 {rule['id']} 时出错: {str(e)}")
        
        logger.info(f"通用规则引擎在文件 {file_path} 中发现 {len(results)} 个问题")
        return results
    
    def _match_rule(self, content: str, rule: Dict[str, Any], file_path: str) -> List[Dict[str, Any]]:
        """
        在文件内容中匹配特定规则
        """
        results = []
        pattern = rule.get("pattern", "")
        rule_type = rule.get("type", "REGEX")
        
        if rule_type == "REGEX":
            try:
                # 编译正则表达式
                regex = re.compile(pattern)
                # 在整个文件内容中查找匹配项
                for match in regex.finditer(content):
                    line_number = content[:match.start()].count('\n') + 1
                    results.append({
                        "rule_id": rule["id"],
                        "rule_name": rule["name"],
                        "severity": rule["severity"],
                        "file": file_path,
                        "line": line_number,
                        "description": rule["description"],
                        "match": match.group(0)
                    })
            except re.error as e:
                logger.error(f"规则 {rule['id']} 的正则表达式错误: {str(e)}")
        
        return results