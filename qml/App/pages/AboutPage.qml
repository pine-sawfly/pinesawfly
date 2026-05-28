import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "About"
    subtitle: "PineSawFly 是一个面向 PHP 项目的桌面安全审计工具。"

    MD.Card {
        width: parent.width
        height: 220

        Text {
            text: "架构"
            font.pixelSize: 18
            font.weight: Font.DemiBold
            color: Styles.Theme.color.onSurface
        }

        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            text: "Python 负责应用启动、主题状态和扫描桥接；QML 负责界面、控件、动画和页面切换。代码查看器改为 QML 原生实现，避免 QScintilla 在 Windows 上的安装和兼容性问题。"
            font.pixelSize: 14
            color: Styles.Theme.color.onSurfaceVariant
        }
    }
}
