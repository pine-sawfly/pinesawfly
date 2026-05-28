import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "审计工作台"
    // subtitle: "选择项目、查看源码并运行规则扫描。前端使用 Qt Quick/QML，编辑器不依赖 QScintilla。"
    property var bridge: auditBridge

    Row {
        width: parent.width
        height: 430
        spacing: 20

        MD.Card {
            width: 300
            height: parent.height

            Text {
                text: "项目文件"
                font.pixelSize: 18
                font.weight: Font.DemiBold
                font.family: Styles.Theme.typography.family
                color: Styles.Theme.color.onSurface
            }

            ListView {
                width: parent.width
                height: 330
                clip: true
                model: bridge ? bridge.files : []

                delegate: Rectangle {
                    width: ListView.view.width
                    height: 36
                    radius: 8
                    color: mouse.containsMouse ? Styles.Theme.color.surfaceContainerHigh : "transparent"

                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        Text {
                            text: "description"
                            font.family: Styles.Fonts.iconFamily
                            font.pixelSize: 18
                            color: Styles.Theme.color.primary
                        }

                        Text {
                            text: modelData.relativePath
                            width: parent.width - 32
                            elide: Text.ElideMiddle
                            font.family: Styles.Theme.typography.family
                            font.pixelSize: 13
                            color: Styles.Theme.color.onSurface
                        }
                    }

                    MouseArea {
                        id: mouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bridge.openFile(modelData.absolutePath)
                    }
                }
            }
        }

        Column {
            width: parent.width - 320
            height: parent.height
            spacing: 14

            Row {
                spacing: 10
                MD.Button {
                    text: bridge && bridge.scanning ? "扫描中" : "扫描项目"
                    icon: "play_arrow"
                    enabled: bridge && !bridge.scanning
                    onClicked: bridge.startScan(false)
                }
                MD.Button {
                    text: "深度扫描"
                    icon: "travel_explore"
                    type: "tonal"
                    enabled: bridge && !bridge.scanning
                    onClicked: bridge.startScan(true)
                }
            }

            MD.CodeEditor {
                width: parent.width
                height: 368
                text: bridge ? bridge.currentContent : ""
                highlightedText: bridge ? bridge.currentHighlightedContent : ""
                filePath: bridge ? bridge.currentFile : ""
            }
        }
    }

    MD.Card {
        width: parent.width
        height: 260

        Text {
            text: "扫描结果"
            font.pixelSize: 18
            font.weight: Font.DemiBold
            font.family: Styles.Theme.typography.family
            color: Styles.Theme.color.onSurface
        }

        ListView {
            width: parent.width
            height: 190
            clip: true
            model: bridge ? bridge.findings : []

            delegate: Rectangle {
                width: ListView.view.width
                height: 46
                radius: 8
                color: mouse2.containsMouse ? Styles.Theme.color.surfaceContainerHigh : "transparent"

                Row {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 12

                    Text {
                        width: 86
                        text: modelData.severity
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                        color: modelData.severity === "HIGH" ? Styles.Theme.color.error : Styles.Theme.color.primary
                    }

                    Text {
                        width: 180
                        text: modelData.ruleName
                        elide: Text.ElideRight
                        color: Styles.Theme.color.onSurface
                        font.pixelSize: 13
                    }

                    Text {
                        width: 230
                        text: modelData.file + ":" + modelData.line
                        elide: Text.ElideMiddle
                        color: Styles.Theme.color.onSurfaceVariant
                        font.pixelSize: 13
                    }

                    Text {
                        width: parent.width - 520
                        text: modelData.description
                        elide: Text.ElideRight
                        color: Styles.Theme.color.onSurfaceVariant
                        font.pixelSize: 13
                    }
                }

                MouseArea {
                    id: mouse2
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bridge.openFinding(modelData.absolutePath, modelData.line)
                }
            }
        }
    }
}
