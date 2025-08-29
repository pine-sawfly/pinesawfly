import logging
import re
from PySide6.QtWidgets import QTextEdit, QWidget, QPlainTextEdit
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QSyntaxHighlighter, QPainter, QTextBlockFormat, QTextFormat
from PySide6.QtCore import QRegularExpression, QRect, Qt, QSize

logger = logging.getLogger(__name__)

class PythonHighlighter(QSyntaxHighlighter):
    """Python语法高亮器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 定义高亮规则
        self.highlightingRules = []
        
        # 关键字格式 (蓝色)
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(86, 156, 214))
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
            
        # 操作符格式 (浅橙色)
        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(QColor(214, 157, 133))
        
        operators = [
            r'=', r'==', r'!=', r'<', r'<=', r'>', r'>=',
            r'\+', r'-', r'\*', r'/', r'//', r'\%', r'\*\*',
            r'\+=', r'-=', r'\*=', r'/=', r'\%=', r'\^', r'\|', r'\&',
            r'\~', r'>>', r'<<'
        ]
        
        for operator in operators:
            pattern = QRegularExpression(operator)
            self.highlightingRules.append((pattern, operatorFormat))
            
        # 括号格式 (青色)
        braceFormat = QTextCharFormat()
        braceFormat.setForeground(QColor(106, 214, 214))
        braces = [r'\{', r'\}', r'\(', r'\)', r'\[', r'\]']
        
        for brace in braces:
            pattern = QRegularExpression(brace)
            self.highlightingRules.append((pattern, braceFormat))
            
        # 注释格式 (绿色)
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(96, 194, 102))
        commentFormat.setFontItalic(True)
        self.highlightingRules.append((QRegularExpression(r'#[^\n]*'), commentFormat))
        
        # 字符串格式 (橙色)
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(214, 157, 133))
        
        # 单引号字符串
        self.highlightingRules.append((QRegularExpression(r"'[^']*'"), stringFormat))
        # 双引号字符串
        self.highlightingRules.append((QRegularExpression(r'"[^"]*"'), stringFormat))
        # 三引号字符串
        self.highlightingRules.append((QRegularExpression(r'""".*"""'), stringFormat))
        self.highlightingRules.append((QRegularExpression(r"'''.*'''"), stringFormat))
        
        # 数字格式 (浅绿色)
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(181, 206, 168))
        self.highlightingRules.append((QRegularExpression(r'\b[0-9]+\b'), numberFormat))
        
        # 函数格式 (黄色)
        functionFormat = QTextCharFormat()
        functionFormat.setForeground(QColor(255, 204, 102))
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
    """PHP语法高亮器，适配深色背景"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 定义高亮规则
        self.highlightingRules = []
        
        # PHP关键字格式 (蓝色)
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(86, 156, 214))
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
            
        # PHP内置函数格式 (黄色)
        builtinFormat = QTextCharFormat()
        builtinFormat.setForeground(QColor(255, 204, 102))
        
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
            
        # 操作符格式 (浅橙色)
        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(QColor(214, 157, 133))
        
        operators = [
            r'=', r'==', r'!=', r'<', r'<=', r'>', r'>=',
            r'\+', r'-', r'\*', r'/', r'//', r'\%', r'\*\*',
            r'\+=', r'-=', r'\*=', r'/=', r'\%=', r'\^', r'\|', r'\&',
            r'\~', r'>>', r'<<'
        ]
        
        for operator in operators:
            pattern = QRegularExpression(operator)
            self.highlightingRules.append((pattern, operatorFormat))
            
        # 括号格式 (青色)
        braceFormat = QTextCharFormat()
        braceFormat.setForeground(QColor(106, 214, 214))
        braces = [r'\{', r'\}', r'\(', r'\)', r'\[', r'\]']
        
        for brace in braces:
            pattern = QRegularExpression(brace)
            self.highlightingRules.append((pattern, braceFormat))
            
        # 注释格式 (绿色)
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(96, 194, 102))
        commentFormat.setFontItalic(True)
        # 单行注释
        self.highlightingRules.append((QRegularExpression(r'//[^\n]*'), commentFormat))
        # 多行注释
        self.highlightingRules.append((QRegularExpression(r'#[^\n]*'), commentFormat))
        # PHPDoc注释
        self.highlightingRules.append((QRegularExpression(r'/\*.*\*/'), commentFormat))
        
        # 字符串格式 (橙色)
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(214, 157, 133))
        
        # 单引号字符串
        self.highlightingRules.append((QRegularExpression(r"'[^']*'"), stringFormat))
        # 双引号字符串
        self.highlightingRules.append((QRegularExpression(r'"[^"]*"'), stringFormat))
        
        # 数字格式 (浅绿色)
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(181, 206, 168))
        self.highlightingRules.append((QRegularExpression(r'\b[0-9]+\b'), numberFormat))
        
        # PHP标签格式 (浅蓝色)
        phpTagFormat = QTextCharFormat()
        phpTagFormat.setForeground(QColor(156, 220, 254))
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
    """JavaScript语法高亮器，适配深色背景"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 定义高亮规则
        self.highlightingRules = []
        
        # 关键字格式 (蓝色)
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(86, 156, 214))
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
            
        # 操作符格式 (浅橙色)
        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(QColor(214, 157, 133))
        
        operators = [
            r'=', r'==', r'!=', r'<', r'<=', r'>', r'>=',
            r'\+', r'-', r'\*', r'/', r'//', r'\%', r'\*\*',
            r'\+=', r'-=', r'\*=', r'/=', r'\%=', r'\^', r'\|', r'\&',
            r'\~', r'>>', r'<<'
        ]
        
        for operator in operators:
            pattern = QRegularExpression(operator)
            self.highlightingRules.append((pattern, operatorFormat))
            
        # 括号格式 (青色)
        braceFormat = QTextCharFormat()
        braceFormat.setForeground(QColor(106, 214, 214))
        braces = [r'\{', r'\}', r'\(', r'\)', r'\[', r'\]']
        
        for brace in braces:
            pattern = QRegularExpression(brace)
            self.highlightingRules.append((pattern, braceFormat))
            
        # 注释格式 (绿色)
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(96, 194, 102))
        commentFormat.setFontItalic(True)
        # 单行注释
        self.highlightingRules.append((QRegularExpression(r'//[^\n]*'), commentFormat))
        # 多行注释
        self.highlightingRules.append((QRegularExpression(r'/\*.*\*/'), commentFormat))
        
        # 字符串格式 (橙色)
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(214, 157, 133))
        
        # 单引号字符串
        self.highlightingRules.append((QRegularExpression(r"'[^']*'"), stringFormat))
        # 双引号字符串
        self.highlightingRules.append((QRegularExpression(r'"[^"]*"'), stringFormat))
        # 模板字符串
        self.highlightingRules.append((QRegularExpression(r'`[^`]*`'), stringFormat))
        
        # 数字格式 (浅绿色)
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor(181, 206, 168))
        self.highlightingRules.append((QRegularExpression(r'\b[0-9]+\b'), numberFormat))
        
        # 函数格式 (黄色)
        functionFormat = QTextCharFormat()
        functionFormat.setForeground(QColor(255, 204, 102))
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

class LineNumberArea(QWidget):
    """行号区域"""
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    """带语法高亮和行号的代码编辑器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = None
        self.lineNumberArea = LineNumberArea(self)
        
        # 可自定义的颜色属性
        self.background_color = QColor(30, 30, 30)  # 默认深色背景
        self.line_number_background_color = QColor(255, 255, 255)  # 行号区域背景色
        self.line_number_text_color = Qt.black  # 行号文字颜色
        self.current_line_color = QColor(53, 53, 53)  # 当前行高亮色
        
        # 设置编辑器背景色
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.background_color)
        self.setPalette(palette)
        
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
    
    def set_background_color(self, color):
        """设置编辑器背景颜色"""
        self.background_color = color
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.background_color)
        self.setPalette(palette)
    
    def set_line_number_colors(self, background_color=None, text_color=None):
        """设置行号区域颜色"""
        if background_color:
            self.line_number_background_color = background_color
        if text_color:
            self.line_number_text_color = text_color
        self.update()
    
    def set_current_line_color(self, color):
        """设置当前行高亮颜色"""
        self.current_line_color = color
        self.highlightCurrentLine()
        
    def lineNumberAreaWidth(self):
        """计算行号区域宽度"""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def updateLineNumberAreaWidth(self, _):
        """更新行号区域宽度"""
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
    
    def updateLineNumberArea(self, rect, dy):
        """更新行号区域"""
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)
    
    def resizeEvent(self, event):
        """处理大小调整事件"""
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))
    
    def lineNumberAreaPaintEvent(self, event):
        """行号区域绘制事件"""
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), self.line_number_background_color)  # 使用可自定义的背景色
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self.line_number_text_color)  # 使用可自定义的文字颜色
                painter.drawText(0, top, self.lineNumberArea.width(), 
                                self.fontMetrics().height(),
                                Qt.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1
    
    def highlightCurrentLine(self):
        """高亮当前行"""
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            
            line_color = self.current_line_color  # 使用可自定义的当前行颜色
            
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)
    
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