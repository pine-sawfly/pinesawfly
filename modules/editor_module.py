import logging
import re
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QSyntaxHighlighter
from PySide6.QtCore import QRegularExpression

logger = logging.getLogger(__name__)

class PythonHighlighter(QSyntaxHighlighter):
    """Python语法高亮器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 定义高亮规则
        self.highlightingRules = []
        
        # 关键字格式
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(86, 156, 214))  # 蓝色
        keywordFormat.setFontWeight(QFont.Bold)
        
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'exec', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
            'not', 'or', 'pass', 'print', 'raise', 'return', 'try',
            'while', 'with', 'yield'
        ]
        
        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self.highlightingRules.append((pattern, keywordFormat))
            
        # 操作符格式
        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(QColor(214, 157, 133))  # 浅褐色
        
        operators = [
            r'=', r'==', r'!=', r'<', r'<=', r'>', r'>=',
            r'\+', r'-', r'\*', r'/', r'//', r'\%', r'\*\*',
            r'\+=', r'-=', r'\*=', r'/=', r'\%=', r'\^', r'\|', r'\&',
            r'\~', r'>>', r'<<'
        ]
        
        for operator in operators:
            pattern = QRegularExpression(operator)
            self.highlightingRules.append((pattern, operatorFormat))
            
        # 括号格式
        braceFormat = QTextCharFormat()
        braceFormat.setForeground(QColor(106, 149, 180))  # 蓝绿色
        braces = [r'\{', r'\}', r'\(', r'\)', r'\[', r'\]']
        
        for brace in braces:
            pattern = QRegularExpression(brace)
            self.highlightingRules.append((pattern, braceFormat))
            
        # 注释格式
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(96, 139, 78))  # 绿色
        commentFormat.setFontItalic(True)
        self.highlightingRules.append((QRegularExpression(r'#[^\n]*'), commentFormat))
        
        # 字符串格式
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(214, 157, 133))  # 浅褐色
        
        # 单引号字符串
        self.highlightingRules.append((QRegularExpression(r"'[^']*'"), stringFormat))
        # 双引号字符串
        self.highlightingRules.append((QRegularExpression(r'"[^"]*"'), stringFormat))
        # 三引号字符串
        self.highlightingRules.append((QRegularExpression(r'""".*"""'), stringFormat))
        self.highlightingRules.append((QRegularExpression(r"'''.*'''"), stringFormat))
        
        # 数字格式
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(181, 206, 168))  # 淡绿色
        self.highlightingRules.append((QRegularExpression(r'\b[0-9]+\b'), numberFormat))
        
        # 函数格式
        functionFormat = QTextCharFormat()
        functionFormat.setForeground(QColor(220, 220, 170))  # 米黄色
        self.highlightingRules.append((QRegularExpression(r'\b[A-Za-z0-9_]+(?=\()'), functionFormat))
        
    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, format in self.highlightingRules:
            expression = QRegularExpression(pattern)
            match = expression.match(text)
            while match.hasMatch():
                length = match.capturedLength()
                start = match.capturedStart()
                self.setFormat(start, length, format)
                match = expression.match(text, start + length)

class PHPLighlighter(QSyntaxHighlighter):
    """PHP语法高亮器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 定义高亮规则
        self.highlightingRules = []
        
        # PHP关键字格式
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(86, 156, 214))  # 蓝色
        keywordFormat.setFontWeight(QFont.Bold)
        
        keywords = [
            'abstract', 'and', 'array', 'as', 'break', 'callable', 'case',
            'catch', 'class', 'clone', 'const', 'continue', 'declare', 'default',
            'do', 'else', 'elseif', 'enddeclare', 'endfor', 'endforeach',
            'endif', 'endswitch', 'endwhile', 'extends', 'final', 'finally',
            'for', 'foreach', 'function', 'global', 'goto', 'if', 'implements',
            'include', 'include_once', 'instanceof', 'insteadof', 'interface',
            'isset', 'list', 'namespace', 'new', 'or', 'print', 'private',
            'protected', 'public', 'require', 'require_once', 'return',
            'static', 'switch', 'throw', 'trait', 'try', 'unset', 'use',
            'var', 'while', 'xor', 'yield'
        ]
        
        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self.highlightingRules.append((pattern, keywordFormat))
            
        # PHP内置函数格式
        builtinFormat = QTextCharFormat()
        builtinFormat.setForeground(QColor(220, 220, 170))  # 米黄色
        
        builtins = [
            'echo', 'empty', 'eval', 'die', 'exit', 'isset', 'unset',
            'count', 'sizeof', 'array_push', 'array_pop', 'array_shift',
            'array_unshift', 'sort', 'rsort', 'usort', 'explode', 'implode',
            'strtolower', 'strtoupper', 'substr', 'strlen', 'strpos',
            'file_get_contents', 'file_put_contents', 'fopen', 'fclose',
            'fwrite', 'fread', 'header', 'isset', 'unset', 'define'
        ]
        
        for word in builtins:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self.highlightingRules.append((pattern, builtinFormat))
            
        # 操作符格式
        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(QColor(214, 157, 133))  # 浅褐色
        
        operators = [
            r'=', r'==', r'!=', r'<', r'<=', r'>', r'>=',
            r'\+', r'-', r'\*', r'/', r'//', r'\%', r'\*\*',
            r'\+=', r'-=', r'\*=', r'/=', r'\%=', r'\^', r'\|', r'\&',
            r'\~', r'>>', r'<<'
        ]
        
        for operator in operators:
            pattern = QRegularExpression(operator)
            self.highlightingRules.append((pattern, operatorFormat))
            
        # 括号格式
        braceFormat = QTextCharFormat()
        braceFormat.setForeground(QColor(106, 149, 180))  # 蓝绿色
        braces = [r'\{', r'\}', r'\(', r'\)', r'\[', r'\]']
        
        for brace in braces:
            pattern = QRegularExpression(brace)
            self.highlightingRules.append((pattern, braceFormat))
            
        # 注释格式
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(96, 139, 78))  # 绿色
        commentFormat.setFontItalic(True)
        # 单行注释
        self.highlightingRules.append((QRegularExpression(r'//[^\n]*'), commentFormat))
        # 多行注释
        self.highlightingRules.append((QRegularExpression(r'#[^\n]*'), commentFormat))
        # PHPDoc注释
        self.highlightingRules.append((QRegularExpression(r'/\*.*\*/'), commentFormat))
        
        # 字符串格式
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(214, 157, 133))  # 浅褐色
        
        # 单引号字符串
        self.highlightingRules.append((QRegularExpression(r"'[^']*'"), stringFormat))
        # 双引号字符串
        self.highlightingRules.append((QRegularExpression(r'"[^"]*"'), stringFormat))
        
        # 数字格式
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(181, 206, 168))  # 淡绿色
        self.highlightingRules.append((QRegularExpression(r'\b[0-9]+\b'), numberFormat))
        
        # PHP标签格式
        phpTagFormat = QTextCharFormat()
        phpTagFormat.setForeground(QColor(156, 220, 254))  # 浅蓝色
        phpTagFormat.setFontWeight(QFont.Bold)
        self.highlightingRules.append((QRegularExpression(r'<\?php'), phpTagFormat))
        self.highlightingRules.append((QRegularExpression(r'\?>'), phpTagFormat))
        
    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, format in self.highlightingRules:
            expression = QRegularExpression(pattern)
            match = expression.match(text)
            while match.hasMatch():
                length = match.capturedLength()
                start = match.capturedStart()
                self.setFormat(start, length, format)
                match = expression.match(text, start + length)

class JavaScriptHighlighter(QSyntaxHighlighter):
    """JavaScript语法高亮器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 定义高亮规则
        self.highlightingRules = []
        
        # 关键字格式
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(86, 156, 214))  # 蓝色
        keywordFormat.setFontWeight(QFont.Bold)
        
        keywords = [
            'break', 'case', 'catch', 'class', 'const', 'continue',
            'debugger', 'default', 'delete', 'do', 'else', 'export',
            'extends', 'finally', 'for', 'function', 'if', 'import',
            'in', 'instanceof', 'let', 'new', 'return', 'super',
            'switch', 'this', 'throw', 'try', 'typeof', 'var',
            'void', 'while', 'with', 'yield'
        ]
        
        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self.highlightingRules.append((pattern, keywordFormat))
            
        # 操作符格式
        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(QColor(214, 157, 133))  # 浅褐色
        
        operators = [
            r'=', r'==', r'!=', r'<', r'<=', r'>', r'>=',
            r'\+', r'-', r'\*', r'/', r'//', r'\%', r'\*\*',
            r'\+=', r'-=', r'\*=', r'/=', r'\%=', r'\^', r'\|', r'\&',
            r'\~', r'>>', r'<<'
        ]
        
        for operator in operators:
            pattern = QRegularExpression(operator)
            self.highlightingRules.append((pattern, operatorFormat))
            
        # 括号格式
        braceFormat = QTextCharFormat()
        braceFormat.setForeground(QColor(106, 149, 180))  # 蓝绿色
        braces = [r'\{', r'\}', r'\(', r'\)', r'\[', r'\]']
        
        for brace in braces:
            pattern = QRegularExpression(brace)
            self.highlightingRules.append((pattern, braceFormat))
            
        # 注释格式
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(96, 139, 78))  # 绿色
        commentFormat.setFontItalic(True)
        # 单行注释
        self.highlightingRules.append((QRegularExpression(r'//[^\n]*'), commentFormat))
        # 多行注释
        self.highlightingRules.append((QRegularExpression(r'/\*.*\*/'), commentFormat))
        
        # 字符串格式
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(214, 157, 133))  # 浅褐色
        
        # 单引号字符串
        self.highlightingRules.append((QRegularExpression(r"'[^']*'"), stringFormat))
        # 双引号字符串
        self.highlightingRules.append((QRegularExpression(r'"[^"]*"'), stringFormat))
        # 模板字符串
        self.highlightingRules.append((QRegularExpression(r'`[^`]*`'), stringFormat))
        
        # 数字格式
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(181, 206, 168))  # 淡绿色
        self.highlightingRules.append((QRegularExpression(r'\b[0-9]+\b'), numberFormat))
        
        # 函数格式
        functionFormat = QTextCharFormat()
        functionFormat.setForeground(QColor(220, 220, 170))  # 米黄色
        self.highlightingRules.append((QRegularExpression(r'\b[A-Za-z0-9_]+(?=\()'), functionFormat))
        
    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, format in self.highlightingRules:
            expression = QRegularExpression(pattern)
            match = expression.match(text)
            while match.hasMatch():
                length = match.capturedLength()
                start = match.capturedStart()
                self.setFormat(start, length, format)
                match = expression.match(text, start + length)

class CodeEditor(QTextEdit):
    """带语法高亮的代码编辑器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = None
        
    def setLanguage(self, language):
        """设置编程语言"""
        # 清除现有的高亮器
        if self.highlighter:
            self.highlighter.setDocument(None)
            
        # 根据语言创建相应的高亮器
        if language == 'python':
            self.highlighter = PythonHighlighter(self.document())
        elif language == 'php':
            self.highlighter = PHPLighlighter(self.document())
        elif language == 'javascript':
            self.highlighter = JavaScriptHighlighter(self.document())
        else:
            self.highlighter = None
            
    def lineNumberAreaPaintEvent(self, event):
        """行号区域绘制事件"""
        # 简化实现，实际项目中可以添加行号显示功能
        pass

class EditorModule:
    """
    编辑器模块，处理代码编辑器相关功能
    """
    
    @staticmethod
    def create_editor(parent=None):
        """
        创建代码编辑器
        
        Args:
            parent: 父级组件
            
        Returns:
            CodeEditor: 创建的编辑器实例
        """
        editor = CodeEditor(parent)
        editor.setReadOnly(True)
        editor.setPlainText("\n\n请选择文件以查看代码内容")
        return editor
    
    @staticmethod
    def set_editor_lexer(editor, file_path):
        """
        根据文件扩展名设置编辑器的语法高亮器
        
        Args:
            editor: 编辑器实例
            file_path: 文件路径
        """
        if not isinstance(editor, CodeEditor):
            return
            
        # 根据文件扩展名确定语言
        extension = file_path.split('.')[-1].lower() if '.' in file_path else ''
        
        language_map = {
            'py': 'python',
            'php': 'php',
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'javascript',
            'html': 'html',
            'htm': 'html',
            'css': 'css'
        }
        
        language = language_map.get(extension, None)
        if language:
            editor.setLanguage(language)