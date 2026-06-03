import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "审计工作台"

    property var bridge: auditBridge
    property var reportFormats: ["Markdown", "HTML", "PDF", "JSON", "TXT"]

    FileDialog {
        id: reportFileDialog
        title: "选择报告保存位置"
        fileMode: FileDialog.SaveFile
        nameFilters: ["报告文件 (*.md *.html *.pdf *.json *.txt)", "所有文件 (*)"]
        onAccepted: reportPathField.text = selectedFile.toString()
    }

    Popup {
        id: exportPopup
        modal: true
        focus: true
        width: 520
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        anchors.centerIn: Overlay.overlay

        background: Rectangle {
            radius: Styles.Theme.shape.large
            color: Styles.Theme.color.surfaceContainerHigh
            border.color: Styles.Theme.color.outlineVariant
            border.width: 1
        }

        contentItem: Item {
            implicitWidth: 520
            implicitHeight: exportContent.implicitHeight + 48

            Column {
                id: exportContent
                anchors.fill: parent
                anchors.margins: 24
                spacing: 18

                Text {
                    text: "导出报告"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 22
                    font.weight: Font.DemiBold
                    color: Styles.Theme.color.onSurface
                }

                Column {
                    width: parent.width
                    spacing: 8

                    Text {
                        text: "保存类型"
                        font.family: Styles.Theme.typography.family
                        font.pixelSize: 13
                        color: Styles.Theme.color.onSurfaceVariant
                    }

                    MD.ComboBox {
                        id: exportFormatCombo
                        width: parent.width
                        model: reportFormats
                        currentText: "Markdown"
                    }
                }

                Column {
                    width: parent.width
                    spacing: 8

                    Text {
                        text: "保存地址"
                        font.family: Styles.Theme.typography.family
                        font.pixelSize: 13
                        color: Styles.Theme.color.onSurfaceVariant
                    }

                    Row {
                        width: parent.width
                        spacing: 8

                        MD.TextField {
                            id: reportPathField
                            width: parent.width - browseButton.width - 8
                            placeholderText: "选择或输入报告保存路径"
                        }

                        MD.Button {
                            id: browseButton
                            text: "浏览"
                            icon: "folder_open"
                            type: "tonal"
                            onClicked: reportFileDialog.open()
                        }
                    }
                }

                Text {
                    width: parent.width
                    text: bridge ? bridge.status : ""
                    wrapMode: Text.WordWrap
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 12
                    color: Styles.Theme.color.primary
                }

                Row {
                    anchors.right: parent.right
                    spacing: 8

                    MD.Button {
                        text: "取消"
                        icon: "close"
                        type: "text"
                        onClicked: exportPopup.close()
                    }

                    MD.Button {
                        text: "保存"
                        icon: "save"
                        enabled: bridge && reportPathField.text.length > 0
                        onClicked: {
                            if (bridge && bridge.exportReport(exportFormatCombo.currentText, reportPathField.text))
                                exportPopup.close()
                        }
                    }
                }
            }
        }
    }

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
                    id: fileRow
                    width: ListView.view.width
                    height: 36
                    radius: Styles.Theme.shape.medium
                    property bool selected: bridge && bridge.currentFile === modelData.absolutePath
                    color: selected
                           ? Styles.Theme.color.primaryContainer
                           : (mouse.containsMouse ? Styles.Theme.color.surfaceContainerHigh : "transparent")

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
                            color: fileRow.selected ? Styles.Theme.color.onPrimaryContainer : Styles.Theme.color.primary
                        }

                        Text {
                            text: modelData.relativePath
                            width: parent.width - 32
                            elide: Text.ElideMiddle
                            font.family: Styles.Theme.typography.family
                            font.pixelSize: 13
                            color: fileRow.selected ? Styles.Theme.color.onPrimaryContainer : Styles.Theme.color.onSurface
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
                    onClicked: bridge.startScan()
                }

                MD.Button {
                    text: "AI分析"
                    icon: "psychology"
                    type: "tonal"
                    enabled: bridge && !bridge.scanning
                    onClicked: bridge.startAiAnalysis()
                }

                MD.Button {
                    text: "导出报告"
                    icon: "file_download"
                    type: "outlined"
                    enabled: bridge
                    onClicked: {
                        exportFormatCombo.currentText = "Markdown"
                        reportPathField.text = ""
                        exportPopup.open()
                    }
                }
            }

            MD.CodeEditor {
                width: parent.width
                height: 368
                text: bridge ? bridge.currentContent : ""
                highlightedText: bridge ? bridge.currentHighlightedContent : ""
                filePath: bridge ? bridge.currentFile : ""
                targetLine: bridge ? bridge.currentLine : 0
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
                radius: Styles.Theme.shape.medium
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
