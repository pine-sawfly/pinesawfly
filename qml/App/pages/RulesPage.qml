import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "规则"
    subtitle: "管理通用 REGEX 扫描规则。规则会保存到 rules 目录，扫描时由 Python 合并为 JSON 后加载。"

    property var rulesBridge: ruleManager
    property string ruleLanguage: "php"
    property string ruleSeverity: "High"
    property string languageFilter: "all"
    property string editingKey: ""
    property bool editing: editingKey.length > 0

    function clearForm() {
        editingKey = ""
        ruleLanguage = "php"
        ruleSeverity = "High"
        ruleIdField.text = ""
        ruleNameField.text = ""
        patternField.text = ""
        descriptionField.text = ""
    }

    function editRule(rule) {
        editingKey = rule.key
        ruleLanguage = rule.language
        ruleSeverity = rule.severity
        ruleIdField.text = rule.id
        ruleNameField.text = rule.name
        patternField.text = rule.pattern
        descriptionField.text = rule.description
    }

    MD.Card {
        width: parent.width
        height: 240

        Text {
            text: editing ? "编辑规则" : "新增规则"
            font.pixelSize: 18
            font.weight: Font.DemiBold
            color: Styles.Theme.color.onSurface
        }

        Row {
            width: parent.width
            spacing: 12

            MD.ComboBox {
                width: 140
                model: ["php", "python", "java"]
                currentText: ruleLanguage
                onActivated: ruleLanguage = text
            }

            MD.ComboBox {
                width: 150
                model: ["Critical", "High", "Medium", "Low"]
                currentText: ruleSeverity
                onActivated: ruleSeverity = text
            }

            MD.TextField {
                id: ruleIdField
                width: 150
                placeholderText: "规则ID"
            }

            MD.TextField {
                id: ruleNameField
                width: Math.max(220, parent.width - 490)
                placeholderText: "规则名称"
            }
        }

        MD.TextField {
            id: patternField
            width: parent.width
            placeholderText: "正则表达式，例如 \\beval\\s*\\("
        }

        Row {
            width: parent.width
            spacing: 12

            MD.TextField {
                id: descriptionField
                width: Math.max(360, parent.width - 136)
                placeholderText: "规则描述"
            }

            MD.Button {
                width: 120
                text: editing ? "保存" : "新增"
                icon: editing ? "save" : "add"
                onClicked: {
                    if (!rulesBridge)
                        return
                    if (editing) {
                        if (rulesBridge.updateRule(editingKey, ruleLanguage, ruleIdField.text, ruleNameField.text, patternField.text, ruleSeverity, descriptionField.text))
                            clearForm()
                    } else {
                        if (rulesBridge.addRule(ruleLanguage, ruleIdField.text, ruleNameField.text, patternField.text, ruleSeverity, descriptionField.text))
                            clearForm()
                    }
                }
            }

            MD.Button {
                visible: editing
                width: 86
                text: "取消"
                icon: "close"
                type: "outlined"
                onClicked: clearForm()
            }
        }
    }

    MD.Card {
        width: parent.width
        height: 520

        Row {
            width: parent.width
            spacing: 12

            Text {
                text: "规则列表"
                width: parent.width - 360
                font.pixelSize: 18
                font.weight: Font.DemiBold
                color: Styles.Theme.color.onSurface
            }

            MD.ComboBox {
                width: 150
                model: ["all", "php", "python", "java"]
                currentText: languageFilter
                onActivated: languageFilter = text
            }

            MD.Button {
                width: 120
                text: "刷新"
                icon: "refresh"
                type: "tonal"
                onClicked: if (rulesBridge) rulesBridge.reload()
            }
        }

        Text {
            text: rulesBridge ? rulesBridge.status : ""
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 13
            color: Styles.Theme.color.onSurfaceVariant
        }

        ListView {
            width: parent.width
            height: 420
            clip: true
            model: rulesBridge ? rulesBridge.rules : []

            delegate: Rectangle {
                width: ListView.view.width
                height: languageFilter === "all" || modelData.language === languageFilter ? 66 : 0
                visible: height > 0
                radius: 8
                color: hover.containsMouse ? Styles.Theme.color.surfaceContainerHigh : "transparent"

                Row {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 10

                    MD.Checkbox {
                        width: 32
                        checked: modelData.enabled
                        onToggled: if (rulesBridge) rulesBridge.setRuleEnabled(modelData.key, checked)
                    }

                    Column {
                        width: Math.max(220, parent.width - 300)
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        Text {
                            width: parent.width
                            text: "[" + modelData.language + "] " + modelData.id + "  " + modelData.name
                            elide: Text.ElideRight
                            color: Styles.Theme.color.onSurface
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                        }

                        Text {
                            width: parent.width
                            text: modelData.severity + " · " + modelData.pattern
                            elide: Text.ElideRight
                            color: Styles.Theme.color.primary
                            font.pixelSize: 12
                            font.family: Styles.Fonts.monoFamily
                        }

                        Text {
                            width: parent.width
                            text: modelData.description
                            elide: Text.ElideRight
                            color: Styles.Theme.color.onSurfaceVariant
                            font.pixelSize: 12
                        }
                    }

                    MD.Button {
                        width: 88
                        text: "编辑"
                        icon: "edit"
                        type: "tonal"
                        onClicked: editRule(modelData)
                    }

                    MD.Button {
                        width: 88
                        text: "删除"
                        icon: "delete"
                        type: "outlined"
                        onClicked: if (rulesBridge) rulesBridge.deleteRule(modelData.key)
                    }
                }

                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }
        }
    }
}
