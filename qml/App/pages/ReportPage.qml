import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "报告"
    subtitle: "配置导出报告的默认格式和内容。"

    property var bridge: auditBridge
    property var formatOptions: ["Markdown", "HTML", "JSON", "TXT"]

    MD.Card {
        width: parent.width
        height: 280

        Text {
            text: "导出格式"
            font.pixelSize: 18
            font.weight: Font.DemiBold
            font.family: Styles.Theme.typography.family
            color: Styles.Theme.color.onSurface
        }

        Row {
            width: parent.width
            spacing: 16

            Column {
                width: Math.min(420, parent.width * 0.45)
                spacing: 8

                Text {
                    text: "报告标题"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 13
                    color: Styles.Theme.color.onSurfaceVariant
                }

                MD.TextField {
                    id: titleField
                    width: parent.width
                    text: bridge ? bridge.reportTitle : ""
                    placeholderText: "PineSawFly 审计报告"
                    onEditingFinished: if (bridge) bridge.setReportTitle(text)
                }
            }

            Column {
                width: 260
                spacing: 8

                Text {
                    text: "默认格式"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 13
                    color: Styles.Theme.color.onSurfaceVariant
                }

                MD.ComboBox {
                    width: parent.width
                    model: formatOptions
                    currentText: bridge ? bridge.defaultReportFormat : "Markdown"
                    onActivated: if (bridge) bridge.setDefaultReportFormat(text)
                }
            }
        }

        Column {
            spacing: 8

            MD.Checkbox {
                text: "包含概览统计"
                checked: bridge ? bridge.reportIncludeSummary : true
                onToggled: if (bridge) bridge.setReportIncludeSummary(checked)
            }

            MD.Checkbox {
                text: "包含匹配证据"
                checked: bridge ? bridge.reportIncludeEvidence : true
                onToggled: if (bridge) bridge.setReportIncludeEvidence(checked)
            }
        }
    }

    MD.Card {
        width: parent.width
        height: 260

        Text {
            text: "格式说明"
            font.pixelSize: 18
            font.weight: Font.DemiBold
            font.family: Styles.Theme.typography.family
            color: Styles.Theme.color.onSurface
        }

        Column {
            width: parent.width
            spacing: 8

            Text {
                width: parent.width
                text: "Markdown：适合二次编辑和提交到文档仓库。"
                font.family: Styles.Theme.typography.family
                font.pixelSize: 14
                color: Styles.Theme.color.onSurfaceVariant
            }

            Text {
                width: parent.width
                text: "HTML：适合直接在浏览器查看。"
                font.family: Styles.Theme.typography.family
                font.pixelSize: 14
                color: Styles.Theme.color.onSurfaceVariant
            }

            Text {
                width: parent.width
                text: "JSON：适合交给其他工具继续处理。"
                font.family: Styles.Theme.typography.family
                font.pixelSize: 14
                color: Styles.Theme.color.onSurfaceVariant
            }

            Text {
                width: parent.width
                text: "TXT：适合快速保存纯文本摘要。"
                font.family: Styles.Theme.typography.family
                font.pixelSize: 14
                color: Styles.Theme.color.onSurfaceVariant
            }
        }
    }
}
