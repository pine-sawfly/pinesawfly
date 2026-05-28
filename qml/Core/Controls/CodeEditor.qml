import QtQuick
import QtQuick.Controls
import "../Styles" as Styles

Rectangle {
    id: root

    property string text: ""
    property string highlightedText: ""
    property string filePath: ""
    property int targetLine: 0
    property string editorFontFamily: Styles.Fonts.monoFamily

    onEditorFontFamilyChanged: {
        codeText.font.family = editorFontFamily
    }

    color: Styles.Theme.manager && Styles.Theme.manager.isDarkTheme ? "#111318" : "#FAF9FD"
    radius: Styles.Theme.shape.small
    border.color: Styles.Theme.color.outlineVariant
    clip: true

    Column {
        anchors.fill: parent

        Rectangle {
            width: parent.width
            height: 40
            color: Styles.Theme.color.surfaceContainer

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 14
                width: parent.width - 28
                text: root.filePath.length ? root.filePath : "代码查看器"
                elide: Text.ElideMiddle
                font.family: Styles.Theme.typography.family
                font.pixelSize: 13
                color: Styles.Theme.color.onSurfaceVariant
            }
        }

        Flickable {
            id: flick
            width: parent.width
            height: parent.height - 40
            contentWidth: Math.max(width, codeText.implicitWidth + gutter.width + 32)
            contentHeight: Math.max(height, codeText.implicitHeight + 24)
            clip: true

            Row {
                y: 12

                Column {
                    id: gutter
                    width: Math.max(44, String(lines.length).length * 10 + 24)

                    Repeater {
                        model: lines.length
                        delegate: Text {
                            width: gutter.width - 10
                            height: 20
                            text: index + 1
                            horizontalAlignment: Text.AlignRight
                            font.family: root.editorFontFamily
                            font.pixelSize: 13
                            color: Styles.Theme.color.onSurfaceVariant
                        }
                    }
                }

                Text {
                    id: codeText
                    text: root.highlightedText.length ? root.highlightedText : root.text
                    textFormat: root.highlightedText.length ? Text.RichText : Text.PlainText
                    font.family: root.editorFontFamily
                    font.pixelSize: 13
                    lineHeightMode: Text.FixedHeight
                    lineHeight: 20
                    color: Styles.Theme.color.onSurface
                    wrapMode: Text.NoWrap
                }
            }
        }
    }

    property var lines: text.length ? text.split(/\r\n|\r|\n/) : [""]
}
