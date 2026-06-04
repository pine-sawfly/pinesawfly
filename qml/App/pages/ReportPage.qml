import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "报告"
    property var bridge: auditBridge
    property var templateFormatOptions: ["Markdown", "HTML", "PDF"]

    function loadTemplate(format) {
        if (bridge)
            templateEditor.text = bridge.loadReportTemplate(format)
    }

    function insertSelectedSymbol() {
        if (symbolPicker.currentText.length > 0)
            insertSymbol(symbolPicker.currentText)
    }

    function insertSymbol(symbol) {
        templateEditor.insert(templateEditor.cursorPosition, symbol)
        templateEditor.forceActiveFocus()
    }

    Component.onCompleted: loadTemplate("Markdown")

    MD.Card {
        width: parent.width
        height: 154

        Text {
            text: "报告信息"
            font.pixelSize: 18
            font.weight: Font.DemiBold
            font.family: Styles.Theme.typography.family
            color: Styles.Theme.color.onSurface
        }

        Row {
            width: parent.width
            spacing: 12

            Column {
                width: Math.max(220, Math.min(340, (parent.width - 24) * 0.38))
                spacing: 7

                Text {
                    text: "报告标题"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 13
                    color: Styles.Theme.color.onSurfaceVariant
                }

                MD.TextField {
                    width: parent.width
                    dense: true
                    text: bridge ? bridge.reportTitle : ""
                    placeholderText: "Pinesawfly审计报告"
                    onEditingFinished: if (bridge) bridge.setReportTitle(text)
                }
            }

            Column {
                width: Math.max(160, Math.min(240, (parent.width - 24) * 0.28))
                spacing: 7

                Text {
                    text: "作者"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 13
                    color: Styles.Theme.color.onSurfaceVariant
                }

                MD.TextField {
                    width: parent.width
                    dense: true
                    text: bridge ? bridge.reportAuthor : ""
                    placeholderText: "可选"
                    onEditingFinished: if (bridge) bridge.setReportAuthor(text)
                }
            }

            Column {
                width: Math.max(160, parent.width - 24 -  Math.max(220, Math.min(340, (parent.width - 24) * 0.38)) - Math.max(160, Math.min(240, (parent.width - 24) * 0.28)))
                spacing: 7

                Text {
                    text: "单位"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 13
                    color: Styles.Theme.color.onSurfaceVariant
                }

                MD.TextField {
                    width: parent.width
                    dense: true
                    text: bridge ? bridge.reportUnit : ""
                    placeholderText: "可选"
                    onEditingFinished: if (bridge) bridge.setReportUnit(text)
                }
            }
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

                Row {
                    width: parent.width
                    spacing: 8

                    MD.ComboBox {
                        id: symbolPicker
                        width: parent.width - insertSymbolButton.width - 8
                        dense: true
                        model: bridge ? bridge.reportTemplateSymbols : []
                        currentText: bridge && bridge.reportTemplateSymbols.length > 0 ? bridge.reportTemplateSymbols[0] : ""
                    }

                    MD.Button {
                        id: insertSymbolButton
                        text: "插入"
                        icon: "add"
                        type: "tonal"
                        onClicked: insertSelectedSymbol()
                    }
                }

                Text {
                    width: parent.width
                    text: "在 {{# findings }} 与 {{/ findings }} 之间排列发现字段，多个发现会按顺序重复这一块。"
                    wrapMode: Text.WordWrap
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 12
                    color: Styles.Theme.color.onSurfaceVariant
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
                    wrapText: false
                    placeholderText: "在这里编辑报告模板，可以插入 {{ title }} 这类占位符。"
                }
            }
        }
    }
}
