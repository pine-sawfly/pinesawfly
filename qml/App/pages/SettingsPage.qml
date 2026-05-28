import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "Settings"
    subtitle: "主题状态由 Python StyleManager 暴露给 QML。"

    property var seeds: ["#006A60", "#6750A4", "#8C1D18", "#00639B"]
    property var availableFonts: Qt.fontFamilies().sort()

    MD.Card {
        width: 520
        height: 430

        Row {
            spacing: 14
            Text {
                text: "暗色模式"
                width: 180
                font.pixelSize: 16
                color: Styles.Theme.color.onSurface
            }
            MD.Switch {
                checked: styleManager.isDarkTheme
                onToggled: styleManager.setDarkTheme(checked)
            }
        }

        Text {
            text: "种子色"
            font.pixelSize: 16
            color: Styles.Theme.color.onSurface
        }

        Row {
            spacing: 12
            Repeater {
                model: seeds
                delegate: Rectangle {
                    width: 44
                    height: 44
                    radius: 22
                    color: modelData
                    border.width: styleManager.seedColor.toUpperCase() === modelData ? 3 : 1
                    border.color: styleManager.seedColor.toUpperCase() === modelData ? Styles.Theme.color.onSurface : Styles.Theme.color.outline

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: styleManager.setSeedColor(modelData)
                    }
                }
            }
        }

        Text {
            text: "界面字体"
            font.pixelSize: 16
            color: Styles.Theme.color.onSurface
        }

        MD.ComboBox {
            width: 360
            model: availableFonts
            currentText: styleManager.uiFontFamily
            placeholderText: "例如 Microsoft YaHei UI"
            onActivated: styleManager.setUiFontFamily(text)
        }

        Text {
            text: "编辑器字体"
            font.pixelSize: 16
            color: Styles.Theme.color.onSurface
        }

        MD.ComboBox {
            width: 360
            model: availableFonts
            currentText: styleManager.editorFontFamily
            placeholderText: "例如 JetBrains Mono"
            onActivated: styleManager.setEditorFontFamily(text)
        }
    }
}
