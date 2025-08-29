import sys
import logging
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QTreeView, QFileSystemModel, \
    QTableView, QStatusBar, QVBoxLayout, QWidget, QSplitter, QPushButton, QFileDialog, QMessageBox, \
    QMenuBar, QMenu, QToolBar, QHBoxLayout, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt, QDir
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem

# 导入模块
from modules.editor_module import EditorModule
from modules.file_module import FileModule

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    主窗口类
    """
    def __init__(self):
        super().__init__()
        self.project_path = "."
        self.init_ui()
        self.setup_logging()
        
    def init_ui(self):
        """
        初始化用户界面
        """
        self.setWindowTitle("pinesawfly - 代码审计工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 创建项目文件树
        self.create_file_tree(splitter)
        
        # 创建右侧区域（标签页）
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建顶部按钮区域
        self.create_top_buttons(right_layout)
        
        # 创建分割器
        self.editor_splitter = QSplitter(Qt.Vertical)
        
        # 创建多标签代码编辑器区域
        self.create_code_editor(self.editor_splitter)
        
        # 创建漏洞结果表
        self.create_vulnerability_table(self.editor_splitter)
        
        right_layout.addWidget(self.editor_splitter)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 900])  # 设置初始大小
        
        # 创建状态栏
        self.create_status_bar()
        
    def create_menu_bar(self):
        """
        创建菜单栏
        """
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        open_action = QAction('打开项目', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_report_action = QAction('保存报告', self)
        save_report_action.setShortcut('Ctrl+S')
        save_report_action.triggered.connect(self.save_report)
        file_menu.addAction(save_report_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
    def create_toolbar(self):
        """
        创建工具栏
        """
        toolbar = self.addToolBar('工具栏')
        
        # 扫描按钮
        self.scan_button = QPushButton("扫描")
        self.scan_button.clicked.connect(self.start_scan)
        toolbar.addWidget(self.scan_button)
        
        # 添加插件按钮
        plugin_action = QAction('插件管理', self)
        plugin_action.triggered.connect(self.manage_plugins)
        toolbar.addAction(plugin_action)
        
        # 自定义规则按钮
        rule_action = QAction('自定义规则', self)
        rule_action.triggered.connect(self.customize_rules)
        toolbar.addAction(rule_action)
        
    def create_top_buttons(self, parent_layout):
        """
        创建顶部按钮区域
        """
        button_layout = QHBoxLayout()
        
        # 添加一些示例按钮
        self.scan_btn = QPushButton("扫描项目")
        self.scan_btn.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_btn)
        
        self.report_btn = QPushButton("生成报告")
        self.report_btn.clicked.connect(self.generate_report)
        button_layout.addWidget(self.report_btn)
        
        button_layout.addStretch()  # 添加弹性空间
        parent_layout.addLayout(button_layout)
        
    def create_file_tree(self, parent):
        """
        创建项目文件树
        """
        self.file_tree = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(self.project_path)
        self.file_model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.AllDirs)
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(self.project_path))
        # 正确设置列标题
        self.file_model.setHeaderData(0, Qt.Horizontal, "项目文件")
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.clicked.connect(self.on_file_clicked)
        parent.addWidget(self.file_tree)
        
    def create_code_editor(self, parent_layout):
        """
        创建多标签代码编辑器
        """
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # 使用模块创建编辑器
        self.editor = EditorModule.create_editor()
        self.tab_widget.addTab(self.editor, "代码查看与审计")
        parent_layout.addWidget(self.tab_widget)
        
    def create_vulnerability_table(self, parent_layout):
        """
        创建漏洞结果表
        """
        self.vuln_table = QTableView()
        self.vuln_table.setSortingEnabled(True)
        
        # 设置数据模型
        self.table_model = QStandardItemModel(0, 6)  # 6列
        self.table_model.setHorizontalHeaderLabels(["规则ID", "规则名称", "严重性", "文件", "行号", "描述"])
        self.vuln_table.setModel(self.table_model)
        
        # 设置选择行为
        self.vuln_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.vuln_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # 设置列宽度
        header = self.vuln_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 规则ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 规则名称
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 严重性
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # 文件
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 行号
        header.setSectionResizeMode(5, QHeaderView.Stretch)           # 描述
        
        # 连接点击事件
        self.vuln_table.clicked.connect(self.on_vuln_clicked)
        
        parent_layout.addWidget(self.vuln_table)
        
    def create_status_bar(self):
        """
        创建状态栏
        """
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
    def setup_logging(self):
        """
        设置日志记录
        """
        logger.info("应用程序启动")
        
    def open_project(self):
        """
        打开项目文件夹
        """
        directory = QFileDialog.getExistingDirectory(self, "选择项目文件夹", "")
        if directory:
            self.project_path = directory
            self.file_model.setRootPath(self.project_path)
            self.file_tree.setRootIndex(self.file_model.index(self.project_path))
            self.status_bar.showMessage(f"已打开项目: {self.project_path}")
            logger.info(f"打开项目文件夹: {self.project_path}")
            
    def save_report(self):
        """
        保存审计报告
        """
        QMessageBox.information(self, "提示", "保存报告功能将在后续实现")
        logger.info("用户点击了保存报告菜单项")
        
    def start_scan(self):
        """
        开始扫描
        """
        self.status_bar.showMessage("开始扫描...")
        self.scan_button.setEnabled(False)
        self.scan_button.setText("扫描中...")
        
        # 清空现有的漏洞数据
        self.table_model.removeRows(0, self.table_model.rowCount())
        
        # 导入插件系统
        try:
            from core.plugin_loader import PluginLoader
            from pathlib import Path
            
            # 加载插件
            plugin_loader = PluginLoader()
            plugins = plugin_loader.load_all_plugins()
            
            # 获取PHP插件
            php_plugin_module = plugin_loader.get_plugin("php_plugin")
            if php_plugin_module:
                php_plugin = php_plugin_module.PluginInterface()
                initialized = php_plugin.initialize()
                
                if initialized:
                    # 遍历项目中的PHP文件进行扫描
                    project_path = Path(self.project_path)
                    php_files = list(project_path.rglob("*.php"))
                    
                    total_vulns = 0
                    for php_file in php_files:
                        try:
                            # 执行扫描
                            vulns = php_plugin.scan(str(php_file))
                            # 将漏洞添加到表格中
                            for vuln in vulns:
                                row = [
                                    QStandardItem(vuln.get("rule_id", "未知")),
                                    QStandardItem(vuln.get("rule_name", "未知")),
                                    QStandardItem(vuln.get("severity", "未知")),
                                    QStandardItem(str(php_file.relative_to(project_path))),
                                    QStandardItem(str(vuln.get("line", "未知"))),
                                    QStandardItem(vuln.get("description", ""))
                                ]
                                self.table_model.appendRow(row)
                                total_vulns += 1
                        except Exception as e:
                            logger.error(f"扫描文件 {php_file} 时出错: {str(e)}")
                    
                    self.status_bar.showMessage(f"扫描完成，发现 {total_vulns} 个漏洞")
                else:
                    self.status_bar.showMessage("PHP插件初始化失败")
            else:
                self.status_bar.showMessage("未找到PHP插件")
                
        except Exception as e:
            logger.error(f"扫描过程中出错: {str(e)}")
            self.status_bar.showMessage("扫描出错，请查看日志")
        
        self.scan_button.setEnabled(True)
        self.scan_button.setText("扫描")
        logger.info("扫描完成")
    
    def manage_plugins(self):
        """
        管理插件
        """
        QMessageBox.information(self, "提示", "插件管理功能将在后续实现")
        logger.info("用户点击了插件管理按钮")
        
    def customize_rules(self):
        """
        自定义规则
        """
        QMessageBox.information(self, "提示", "自定义规则功能将在后续实现")
        logger.info("用户点击了自定义规则按钮")
        
    def generate_report(self):
        """
        生成报告
        """
        QMessageBox.information(self, "提示", "生成报告功能将在后续实现")
        logger.info("用户点击了生成报告按钮")
        
    def on_file_clicked(self, index):
        """
        文件树点击事件
        """
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            try:
                # 使用模块读取文件
                content = FileModule.read_file_with_encoding(file_path)
                    
                if hasattr(self.editor, 'setText'):  # QScintilla编辑器
                    # 根据文件扩展名设置语法高亮
                    EditorModule.set_editor_lexer(self.editor, file_path)
                    self.editor.setText(content)
                    if hasattr(self.editor, 'highlighter') and self.editor.highlighter:
                        self.editor.highlighter.rehighlight()
                else:  # QTextEdit
                    self.editor.setPlainText(content)
                    # 根据文件扩展名设置语法高亮
                    EditorModule.set_editor_lexer(self.editor, file_path)
                    if hasattr(self.editor, 'highlighter') and self.editor.highlighter:
                        self.editor.highlighter.rehighlight()
                    
                self.status_bar.showMessage(f"已加载文件: {file_path}")
            except Exception as e:
                self.status_bar.showMessage(f"无法读取文件: {str(e)}")
                logger.error(f"读取文件失败 {file_path}: {str(e)}")
    def on_vuln_clicked(self, index):
        """
        漏洞表点击事件
        """
        # 这里应该实现点击漏洞项时跳转到对应代码位置的功能
        row = index.row()
        if row < self.table_model.rowCount():
            file_item = self.table_model.item(row, 3)  # 文件列
            line_item = self.table_model.item(row, 4)  # 行号列
            
            if file_item and line_item:
                file_path = file_item.text()
                line_number = line_item.text()
                
                # 构造完整文件路径
                full_file_path = os.path.join(self.project_path, file_path)
                
                # 检查文件是否存在
                if os.path.exists(full_file_path):
                    # 在文件树中定位文件
                    file_index = self.file_model.index(full_file_path)
                    if file_index.isValid():
                        self.file_tree.setCurrentIndex(file_index)
                    
                    # 打开文件并在编辑器中显示
                    self.open_file_in_editor(full_file_path, line_number)
                    
                    self.status_bar.showMessage(f"定位到文件: {file_path}, 行: {line_number}")
                    logger.info(f"用户点击漏洞项，定位到文件: {file_path}, 行: {line_number}")
                else:
                    self.status_bar.showMessage(f"文件不存在: {file_path}")
                    logger.error(f"点击漏洞项时文件不存在: {full_file_path}")

    def open_file_in_editor(self, file_path, line_number=None):
        """
        在编辑器中打开文件并跳转到指定行
        """
        try:
            # 使用模块读取文件
            content = FileModule.read_file_with_encoding(file_path)
                
            # 创建新的标签页或使用现有标签页
            tab_name = os.path.basename(file_path)
            
            # 检查文件是否已经打开
            existing_tab_index = None
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == tab_name:
                    existing_tab_index = i
                    break
            
            if existing_tab_index is not None:
                # 文件已打开，切换到该标签页
                self.tab_widget.setCurrentIndex(existing_tab_index)
                editor = self.tab_widget.widget(existing_tab_index)
            else:
                # 创建新的标签页
                editor = EditorModule.create_editor()
                EditorModule.set_editor_lexer(editor, file_path)
                    
                self.tab_widget.addTab(editor, tab_name)
                self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
            
            # 设置文件内容
            if hasattr(editor, 'setText'):  # QScintilla编辑器
                editor.setText(content)
                # 如果指定了行号，则跳转到该行
                if line_number and line_number.isdigit():
                    line_num = int(line_number)
                    editor.setCursorPosition(line_num - 1, 0)  # 行号从0开始
                    editor.ensureLineVisible(line_num - 1)     # 确保该行可见
            else:  # QTextEdit
                editor.setPlainText(content)
                
            self.status_bar.showMessage(f"已加载文件: {file_path}")
        except Exception as e:
            self.status_bar.showMessage(f"无法读取文件: {str(e)}")
            logger.error(f"读取文件失败 {file_path}: {str(e)}")

    def close_tab(self, index):
        """
        关闭标签页
        """
        if self.tab_widget.count() > 1:  # 至少保留一个标签页
            self.tab_widget.removeTab(index)

def main():
    """
    主函数
    """
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()