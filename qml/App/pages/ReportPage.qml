import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "报告"
    subtitle: "通过模板和占位符控制导出报告的结构。"

    property var bridge: auditBridge
    property var templateFormatOptions: ["Markdown", "HTML", "PDF"]

    function loadTemplate(format) {
        if (bridge)
            templateEditor.text = bridge.loadReportTemplate(format)
    }

    function insertSymbol(symbol) {
        templateEditor.insert(templateEditor.cursorPosition, symbol)
        templateEditor.forceActiveFocus()
    }

    Component.onCompleted: loadTemplate("Markdown")

    MD.Card {
        width: parent.width
        height: 238

        Text {
            text: "报告信息"
            font.pixelSize: 18
            font.weight: Font.DemiBold
            font.family: Styles.Theme.typography.family
            color: Styles.Theme.color.onSurface
        }

        Row {
            width: parent.width
            spacing: 16

            Column {
                width: Math.min(460, parent.width * 0.48)
                spacing: 8

                Text {
                    text: "报告标题"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 13
                    color: Styles.Theme.color.onSurfaceVariant
                }

                MD.TextField {
                    width: parent.width
                    text: bridge ? bridge.reportTitle : ""
                    placeholderText: "PineSawFly 审计报告"
                    onEditingFinished: if (bridge) bridge.setReportTitle(text)
                }
            }

            Column {
                width: Math.min(340, parent.width * 0.36)
                spacing: 8

                Text {
                    text: "作者"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 13
                    color: Styles.Theme.color.onSurfaceVariant
                }

                MD.TextField {
                    width: parent.width
                    text: bridge ? bridge.reportAuthor : ""
                    placeholderText: "可选"
                    onEditingFinished: if (bridge) bridge.setReportAuthor(text)
                }
            }
        }

        Flow {
            width: parent.width
            spacing: 10

            MD.Checkbox { text: "项目路径"; checked: bridge ? bridge.reportIncludeProjectPath : true; onToggled: if (bridge) bridge.setReportIncludeProjectPath(checked) }
            MD.Checkbox { text: "时间"; checked: bridge ? bridge.reportIncludeGeneratedAt : true; onToggled: if (bridge) bridge.setReportIncludeGeneratedAt(checked) }
            MD.Checkbox { text: "概览"; checked: bridge ? bridge.reportIncludeSummary : true; onToggled: if (bridge) bridge.setReportIncludeSummary(checked) }
            MD.Checkbox { text: "Logo"; checked: bridge ? bridge.reportIncludeLogo : true; onToggled: if (bridge) bridge.setReportIncludeLogo(checked) }
            MD.Checkbox { text: "受影响位置"; checked: bridge ? bridge.reportIncludeAffectedLocation : true; onToggled: if (bridge) bridge.setReportIncludeAffectedLocation(checked) }
            MD.Checkbox { text: "匹配证据"; checked: bridge ? bridge.reportIncludeEvidence : true; onToggled: if (bridge) bridge.setReportIncludeEvidence(checked) }
            MD.Checkbox { text: "高亮代码片段"; checked: bridge ? bridge.reportIncludeCodeSnippet : true; onToggled: if (bridge) bridge.setReportIncludeCodeSnippet(checked) }
        }
    }

    MD.Card {
        width: parent.width
        height: 584

        Row {
            width: parent.width
            spacing: 16

            Column {
                width: 260
                spacing: 10

                Text {
                    text: "模板"
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    font.family: Styles.Theme.typography.family
                    color: Styles.Theme.color.onSurface
                }

                MD.ComboBox {
                    id: templateFormat
                    width: parent.width
                    model: templateFormatOptions
                    currentText: "Markdown"
                    onActivated: loadTemplate(text)
                }

                Text {
                    width: parent.width
                    text: "插入符号"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 13
                    color: Styles.Theme.color.onSurfaceVariant
                }

                Flow {
                    width: parent.width
                    spacing: 8

                    Repeater {
                        model: bridge ? bridge.reportTemplateSymbols : []
                        delegate: MD.Button {
                            text: modelData
                            type: "tonal"
                            onClicked: insertSymbol(modelData)
                        }
                    }
                }

                Row {
                    spacing: 8

                    MD.Button {
                        text: "保存"
                        icon: "save"
                        onClicked: if (bridge) bridge.saveReportTemplate(templateFormat.currentText, templateEditor.text)
                    }

                    MD.Button {
                        text: "重置"
                        icon: "restart_alt"
                        type: "outlined"
                        onClicked: if (bridge) templateEditor.text = bridge.resetReportTemplate(templateFormat.currentText)
                    }
                }
            }

            Column {
                width: parent.width - 276
                spacing: 8

                Text {
                    text: "模板内容"
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    font.family: Styles.Theme.typography.family
                    color: Styles.Theme.color.onSurface
                }

                MD.TextArea {
                    id: templateEditor
                    width: parent.width
                    height: 490
                    mono: true
                    placeholderText: "在这里编辑报告模板，可以插入 {{ title }} 这类占位符。"
                }
            }
        }
    }
}
