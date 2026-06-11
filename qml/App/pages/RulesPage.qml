import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "规则"

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
        height: 262

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
                dense: true
                model: ["php", "python", "java"]
                currentText: ruleLanguage
                onActivated: function(text) { ruleLanguage = text }
            }

            MD.ComboBox {
                width: 150
                dense: true
                model: ["Critical", "High", "Medium", "Low"]
                currentText: ruleSeverity
                onActivated: function(text) { ruleSeverity = text }
            }

            MD.TextField {
                id: ruleIdField
                width: 150
                dense: true
                placeholderText: "规则ID"
            }

            MD.TextField {
                id: ruleNameField
                width: Math.max(220, parent.width - 490)
                dense: true
                placeholderText: "规则名称"
            }
        }

        Item { width: 1; height: 4 }

        MD.TextField {
            id: patternField
            width: parent.width
            dense: true
            placeholderText: "正则表达式，例如 \\beval\\s*\\("
        }

        Item { width: 1; height: 6 }

        Item {
            id: descriptionRow
            width: parent.width
            height: 40
            property int gap: 12

            MD.TextField {
                id: descriptionField
                width: Math.max(260, parent.width - actionGroup.width - descriptionRow.gap)
                height: parent.height
                dense: true
                placeholderText: "规则描述"

                Behavior on width {
                    NumberAnimation { duration: 120; easing.type: Easing.OutCubic }
                }
            }

            Item {
                id: actionGroup
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                height: parent.height
                width: editing ? 218 : 120
                clip: true

                Behavior on width {
                    NumberAnimation { duration: 40; easing.type: Easing.OutCubic }
                }

                Row {
                    id: buttonsRow
                    spacing: 12
                    anchors.verticalCenter: parent.verticalCenter

                    MD.Button {
                        id: saveRuleButton
                        text: "保存"
                        icon: "save"
                        width: editing ? 120 : 0
                        opacity: editing ? 1 : 0
                        scale: editing ? 1 : 0.92
                        enabled: editing
                        onClicked: {
                            if (rulesBridge && rulesBridge.updateRule(editingKey, ruleLanguage, ruleIdField.text, ruleNameField.text, patternField.text, ruleSeverity, descriptionField.text))
                                clearForm()
                        }
                        Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
                        Behavior on opacity { NumberAnimation { duration: 210; easing.type: Easing.OutCubic } }
                        Behavior on scale { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
                    }

                    MD.Button {
                        id: cancelEditButton
                        text: "取消"
                        icon: "close"
                        type: "outlined"
                        width: editing ? 86 : 0
                        opacity: editing ? 1 : 0
                        enabled: editing
                        onClicked: clearForm()
                        Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
                        Behavior on opacity { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
                    }

                    MD.Button {
                        id: addRuleButton
                        text: "新增"
                        icon: "add"
                        width: editing ? 0 : 120
                        opacity: editing ? 0 : 1
                        scale: editing ? 0 : 1
                        enabled: !editing
                        onClicked: {
                            if (rulesBridge && rulesBridge.addRule(ruleLanguage, ruleIdField.text, ruleNameField.text, patternField.text, ruleSeverity, descriptionField.text))
                                clearForm()
                        }
                        Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.InOutCubic } }
                        Behavior on opacity { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }
                        Behavior on scale { NumberAnimation { duration: 220; easing.type: Easing.InOutCubic } }
                    }
                }
            }
        }

        Item { width: 1; height: 10 }
    }

    MD.Card {
        width: parent.width
        height: 520

        Item {
            width: parent.width
            height: parent.height

            Row {
                id: listHeader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 56
                spacing: 12

                Text {
                    text: "规则列表"
                    width: parent.width - 294
                    anchors.verticalCenter: parent.verticalCenter
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    color: Styles.Theme.color.onSurface
                }

                MD.ComboBox {
                    width: 150
                    dense: true
                    model: ["all", "php", "python", "java"]
                    currentText: languageFilter
                    onActivated: function(text) { languageFilter = text }
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
                id: statusText
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: listHeader.bottom
                height: 28
                text: rulesBridge ? rulesBridge.status : ""
                wrapMode: Text.WordWrap
                font.pixelSize: 13
                color: Styles.Theme.color.onSurfaceVariant
            }

            Rectangle {
                id: listFrame
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: statusText.bottom
                anchors.bottom: parent.bottom
                radius: Styles.Theme.shape.medium
                color: Styles.Theme.color.surfaceContainer
                border.width: 0
                clip: true

                ListView {
                    anchors.fill: parent
                    anchors.margins: 6
                    clip: true
                    model: rulesBridge ? rulesBridge.rules : []

                    delegate: Rectangle {
                        width: ListView.view.width
                        height: languageFilter === "all" || modelData.language === languageFilter ? 66 : 0
                        visible: height > 0
                        radius: Styles.Theme.shape.medium
                        color: hover.containsMouse ? Styles.Theme.color.surfaceContainerHigh : "transparent"

                        Row {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 10

                            MD.Checkbox {
                                width: 32
                                checked: modelData.enabled
                                onToggled: function(checked) {
                                    if (rulesBridge) rulesBridge.setRuleEnabled(modelData.key, checked)
                                }
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
    }
}
