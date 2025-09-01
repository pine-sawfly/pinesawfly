import logging
from typing import List, Dict, Any
from core.exception_handler import safe_operation

logger = logging.getLogger(__name__)

class TaintAnalyzer:
    """
    污点分析器，用于跟踪用户输入到危险函数的数据流
    """
    
    def __init__(self):
        # 定义污点源（用户可控制的输入）
        self.taint_sources = [
            '$_GET', '$_POST', '$_REQUEST', '$_COOKIE', '$_SERVER'
        ]
        
        # 定义危险函数（可能导致安全问题的函数）
        self.sink_functions = [
            'eval', 'assert', 'system', 'exec', 'shell_exec', 
            'passthru', 'proc_open', 'popen'
        ]
        
        # 定义文件包含函数
        self.file_inclusion_functions = [
            'include', 'include_once', 'require', 'require_once'
        ]
    
    @safe_operation
    def analyze(self, ast, file_path: str) -> List[Dict[str, Any]]:
        """
        分析AST中的污点流
        """
        results = []
        
        # 查找污点源的使用
        tainted_vars = self._find_taint_sources(ast)
        
        # 查找危险函数调用
        sink_calls = self._find_sink_functions(ast)
        
        # 查找文件包含函数调用
        file_inclusion_calls = self._find_file_inclusion_functions(ast)
        
        # 分析数据流，检查是否存在从污点源到危险函数的数据流
        for sink in sink_calls:
            # 这里应该实现完整的数据流分析
            # 为简化起见，我们只做一个基本的检查
            results.append({
                "type": "TaintAnalysis",
                "rule_id": "TAINT001",
                "rule_name": "潜在污点传播",
                "severity": "High",
                "file": file_path,
                "line": sink.get("line", 0),
                "description": f"检测到从用户输入到危险函数 {sink.get('function')} 的潜在数据流",
                "details": sink
            })
        
        # 分析文件包含函数调用中的变量使用
        for inclusion in file_inclusion_calls:
            if self._has_variable_argument(inclusion):
                results.append({
                    "type": "FileInclusion",
                    "rule_id": "FILEINC001",
                    "rule_name": "文件包含漏洞",
                    "severity": "High",
                    "file": file_path,
                    "line": inclusion.get("line", 0),
                    "description": f"检测到文件包含函数 {inclusion.get('function')} 中使用变量，可能存在文件包含漏洞",
                    "details": inclusion
                })
        
        logger.info(f"污点分析在文件 {file_path} 中发现 {len(results)} 个问题")
        return results
    
    def _find_taint_sources(self, ast) -> List[Dict[str, Any]]:
        """
        在AST中查找污点源
        """
        sources = []
        # 实现查找污点源的逻辑
        # 这里应该遍历AST并查找对$_GET, $_POST等的引用
        return sources
    
    def _find_sink_functions(self, ast) -> List[Dict[str, Any]]:
        """
        在AST中查找危险函数调用
        """
        sinks = []
        
        def traverse(node):
            if hasattr(node, '__dict__'):
                # 检查是否为函数调用
                if type(node).__name__ == "FunctionCall":
                    func_name = getattr(node, 'name', '')
                    if func_name in self.sink_functions:
                        sinks.append({
                            "function": func_name,
                            "line": getattr(node, 'lineno', 0),
                            "args": getattr(node, 'params', [])
                        })
                
                # 递归遍历子节点
                for value in node.__dict__.values():
                    if hasattr(value, '__dict__') or isinstance(value, list):
                        traverse(value)
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
        
        traverse(ast)
        return sinks
    
    def _find_file_inclusion_functions(self, ast) -> List[Dict[str, Any]]:
        """
        在AST中查找文件包含函数调用
        """
        inclusions = []
        
        def traverse(node):
            if hasattr(node, '__dict__'):
                # 检查是否为函数调用
                if type(node).__name__ == "FunctionCall":
                    func_name = getattr(node, 'name', '')
                    if func_name in self.file_inclusion_functions:
                        inclusions.append({
                            "function": func_name,
                            "line": getattr(node, 'lineno', 0),
                            "args": getattr(node, 'params', [])
                        })
                
                # 递归遍历子节点
                for value in node.__dict__.values():
                    if hasattr(value, '__dict__') or isinstance(value, list):
                        traverse(value)
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
        
        traverse(ast)
        return inclusions
    
    def _has_variable_argument(self, inclusion_call: Dict[str, Any]) -> bool:
        """
        检查文件包含函数调用是否包含变量参数
        """
        args = inclusion_call.get("args", [])
        for arg in args:
            # 检查参数是否为变量
            if self._is_variable_expression(arg):
                return True
        return False
    
    def _is_variable_expression(self, node) -> bool:
        """
        判断节点是否为变量表达式
        """
        if hasattr(node, '__dict__'):
            # 检查是否为变量节点
            node_type = type(node).__name__
            if node_type in ["Variable", "Expr_Variable"]:
                return True
                
            # 检查是否为数组访问表达式
            if node_type in ["ArrayOffset", "Expr_ArrayDimFetch"]:
                return True
                
            # 检查二元表达式（如字符串拼接）
            if node_type in ["BinaryOp", "Expr_BinaryOp_Concat"]:
                return True
                
            # 检查函数调用返回值
            if node_type == "FunctionCall":
                return True
                
            # 检查属性访问（$this->property）
            if node_type in ["Property", "Expr_PropertyFetch"]:
                return True
                
            # 递归检查子节点
            for value in node.__dict__.values():
                if self._is_variable_expression(value):
                    return True
                    
        elif isinstance(node, list):
            for item in node:
                if self._is_variable_expression(item):
                    return True
                    
        return False