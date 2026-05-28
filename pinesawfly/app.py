from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from .audit_bridge import AuditBridge
from .rule_manager import RuleManager
from .stylemanager import StyleManager


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("PineSawFly")
    app.setOrganizationName("PineSawFly")

    project_root = Path(__file__).resolve().parent.parent
    icon_path = project_root / "assets" / "icons" / "app.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    qml_root = project_root / "qml"

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(qml_root))

    style_manager = StyleManager()
    audit_bridge = AuditBridge()
    rule_manager = RuleManager(project_root / "rules")
    engine.rootContext().setContextProperty("styleManager", style_manager)
    engine.rootContext().setContextProperty("auditBridge", audit_bridge)
    engine.rootContext().setContextProperty("ruleManager", rule_manager)
    material_icons_path = project_root / "assets" / "fonts" / "MaterialIcons-Regular.ttf"
    engine.rootContext().setContextProperty(
        "materialIconsFontUrl",
        QUrl.fromLocalFile(str(material_icons_path)).toString() if material_icons_path.exists() else "",
    )

    engine.load(QUrl.fromLocalFile(str(qml_root / "App" / "Main.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
