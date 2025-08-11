import sys
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QTreeView, QFileSystemModel, \
    QTableView, QStatusBar, QVBoxLayout, QWidget, QSplitter, QLabel
from PySide6.QtCore import Qt

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    主窗口类
    """
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_logging()
        
    def init_ui(self):
        """
        初始化用户界面
        """
        self.setWindowTitle("pinesawfly - 代码审计工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 创建项目文件树
        self.create_file_tree(splitter)
        
        # 创建右侧区域（标签页）
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 创建多标签代码编辑器区域
        self.create_code_editor(right_layout)
        
        # 创建漏洞结果表
        self.create_vulnerability_table(right_layout)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 900])  # 设置初始大小
        
        # 创建状态栏
        self.create_status_bar()
        
    def create_file_tree(self, parent):
        """
        创建项目文件树
        """
        self.file_tree = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index("."))
        # 修复：QTreeView没有setHeaderLabel方法，应该通过模型设置标题
        self.file_model.setHeaderData(0, Qt.Horizontal, "项目文件")
        parent.addWidget(self.file_tree)
        
    def create_code_editor(self, parent_layout):
        """
        创建多标签代码编辑器
        """
        # 暂时使用QLabel作为占位符，后续会替换为QScintilla
        self.editor_placeholder = QLabel("代码编辑器区域")
        self.editor_placeholder.setAlignment(Qt.AlignCenter)
        self.editor_placeholder.setStyleSheet("QLabel { background-color: #f0f0f0; border: 1px solid #ccc; }")
        parent_layout.addWidget(self.editor_placeholder)
        
    def create_vulnerability_table(self, parent_layout):
        """
        创建漏洞结果表
        """
        self.vuln_table = QTableView()
        self.vuln_table.setSortingEnabled(True)
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