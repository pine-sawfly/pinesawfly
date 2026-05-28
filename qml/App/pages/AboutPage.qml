import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "About"
    subtitle: "PineSawFly 是一个面向 PHP 项目的桌面安全审计工具。"

    MD.Card {
        width: parent.width
        height: 280

        Row {
            spacing: 18

            Image {
                width: 72
                height: 72
                source: "../../../assets/icons/app.ico"
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            Column {
                spacing: 4
                Text {
                    text: "PineSawFly"
                    font.pixelSize: 26
                    font.weight: Font.DemiBold
                    color: Styles.Theme.color.onSurface
                }

                Text {
                    text: "PHP 安全审计桌面应用"
                    font.pixelSize: 14
                    color: Styles.Theme.color.onSurfaceVariant
                }
            }
        }

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
