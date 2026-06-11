import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "Settings"

    property var seeds: ["#006A60", "#6750A4", "#8C1D18", "#00639B"]
    property var availableFonts: []
    property var style: styleManager

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
                checked: style ? style.isDarkTheme : false
                onToggled: function(checked) {
                    if (style) style.setDarkTheme(checked)
                }
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
                    border.width: style && style.seedColor.toUpperCase() === modelData ? 3 : 1
                    border.color: style && style.seedColor.toUpperCase() === modelData ? Styles.Theme.color.onSurface : Styles.Theme.color.outline

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: if (style) style.setSeedColor(modelData)
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
            currentText: style ? style.uiFontFamily : ""
            placeholderText: "例如 Microsoft YaHei UI"
            useCurrentFontPreview: true
            onAboutToOpen: if (availableFonts.length === 0) availableFonts = Qt.fontFamilies().sort()
            onActivated: function(text) { if (style) style.setUiFontFamily(text) }
        }

        Text {
            text: "编辑器字体"
            font.pixelSize: 16
            color: Styles.Theme.color.onSurface
        }

        MD.ComboBox {
            width: 360
            model: availableFonts
            currentText: style ? style.editorFontFamily : ""
            placeholderText: "例如 JetBrains Mono"
            useCurrentFontPreview: true
            onAboutToOpen: if (availableFonts.length === 0) availableFonts = Qt.fontFamilies().sort()
            onActivated: function(text) { if (style) style.setEditorFontFamily(text) }
        }
    }
}
