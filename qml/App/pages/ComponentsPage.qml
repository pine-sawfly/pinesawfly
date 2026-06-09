import QtQuick
import QtQuick.Controls
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "插件"

    property var bridge: auditBridge

    Popup {
        id: aiConfigPopup
        modal: true
        focus: true
        width: 700
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
            implicitWidth: 700
            implicitHeight: 560

            Column {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 14

                Row {
                    width: parent.width
                    spacing: 12

                    Text {
                        width: parent.width - closeButton.width - 12
                        text: "AI API 配置"
                        font.family: Styles.Theme.typography.family
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        color: Styles.Theme.color.onSurface
                    }

                    MD.Button {
                        id: closeButton
                        text: "关闭"
                        icon: "close"
                        type: "text"
                        onClicked: aiConfigPopup.close()
                    }
                }

                ListView {
                    id: apiList
                    width: parent.width
                    height: 410
                    spacing: 10
                    clip: true
                    model: bridge ? bridge.aiApiConfigs : []

                    delegate: Rectangle {
                        width: apiList.width
                        height: modelData.maskedKey.length > 0 ? 198 : 162
                        radius: Styles.Theme.shape.large
                        color: Styles.Theme.color.surfaceContainer
                        border.color: Styles.Theme.color.outlineVariant
                        border.width: 1

                        Column {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6

                            Row {
                                width: parent.width
                                spacing: 8

                                MD.TextField {
                                    id: apiNameField
                                    width: 160
                                    dense: true
                                    placeholderText: "API 名称"
                                    text: modelData.apiName
                                    onEditingFinished: bridge.updateAiApiConfig(modelData.index, text, apiUrlField.text, modelNameField.text, keyNameField.text, newKeyField.text)
                                }

                                MD.TextField {
                                    id: apiUrlField
                                    width: parent.width - 168
                                    dense: true
                                    placeholderText: "API URL"
                                    text: modelData.apiUrl
                                    onEditingFinished: bridge.updateAiApiConfig(modelData.index, apiNameField.text, text, modelNameField.text, keyNameField.text, newKeyField.text)
                                }
                            }

                            Row {
                                width: parent.width
                                spacing: 8

                                MD.TextField {
                                    id: modelNameField
                                    width: 250
                                    dense: true
                                    placeholderText: "模型名"
                                    text: modelData.modelName
                                    onEditingFinished: bridge.updateAiApiConfig(modelData.index, apiNameField.text, apiUrlField.text, text, keyNameField.text, newKeyField.text)
                                }

                                MD.TextField {
                                    id: keyNameField
                                    width: parent.width - modelNameField.width - 8
                                    dense: true
                                    placeholderText: "Key 名称"
                                    text: modelData.keyName
                                    onEditingFinished: bridge.updateAiApiConfig(modelData.index, apiNameField.text, apiUrlField.text, modelNameField.text, text, newKeyField.text)
                                }
                            }

                            Row {
                                width: parent.width
                                spacing: 8

                                MD.TextField {
                                    id: newKeyField
                                    width: parent.width - saveButton.width - deleteButton.width - 16
                                    dense: true
                                    placeholderText: "输入新 Key 后替换"
                                    echoMode: TextInput.Password
                                    onAccepted: saveButton.clicked()
                                }

                                MD.Button {
                                    id: saveButton
                                    width: 82
                                    text: "保存"
                                    icon: "save"
                                    type: "tonal"
                                    onClicked: {
                                        bridge.updateAiApiConfig(modelData.index, apiNameField.text, apiUrlField.text, modelNameField.text, keyNameField.text, newKeyField.text)
                                        newKeyField.text = ""
                                    }
                                }

                                MD.Button {
                                    id: deleteButton
                                    width: 82
                                    text: "删除"
                                    icon: "delete"
                                    type: "outlined"
                                    onClicked: bridge.deleteAiApiConfig(modelData.index)
                                }
                            }

                            Row {
                                width: parent.width
                                visible: modelData.maskedKey.length > 0
                                height: visible ? 28 : 0

                                Text {
                                    width: parent.width
                                    height: 28
                                    text: "当前 Key  " + modelData.maskedKey + (modelData.keyFingerprint.length > 0 ? "  指纹 " + modelData.keyFingerprint : "")
                                    verticalAlignment: Text.AlignVCenter
                                    font.family: "Cascadia Mono"
                                    font.pixelSize: 12
                                    color: Styles.Theme.color.onSurfaceVariant
                                    elide: Text.ElideMiddle
                                }
                            }
                        }
                    }
                }

                Row {
                    anchors.right: parent.right
                    spacing: 8

                    MD.Button {
                        text: "增加 API"
                        icon: "add"
                        type: "tonal"
                        onClicked: if (bridge) bridge.addAiApiConfig()
                    }
                }
            }
        }
    }

    Row {
        width: parent.width
        spacing: 12

        MD.Card {
            width: 252
            height: 132

            Column {
                width: parent.width
                spacing: 10

                Row {
                    width: parent.width
                    spacing: 10

                    MD.LogoIcon {
                        width: 30
                        height: 30
                        iconColor: Styles.Theme.color.primary
                    }

                    Text {
                        width: parent.width - 40
                        height: 30
                        text: "PHP 污点分析"
                        font.family: Styles.Theme.typography.family
                        font.pixelSize: 17
                        font.weight: Font.DemiBold
                        verticalAlignment: Text.AlignVCenter
                        color: Styles.Theme.color.onSurface
                    }
                }

                Text {
                    text: "已启用 · 内置"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 13
                    color: Styles.Theme.color.primary
                }
            }
        }

        MD.Card {
            width: 252
            height: 132

            Column {
                width: parent.width
                spacing: 10

                Row {
                    width: parent.width
                    spacing: 10

                    Text {
                        width: parent.width - switchControl.width - 10
                        height: 32
                        text: "AI 分析"
                        font.family: Styles.Theme.typography.family
                        font.pixelSize: 17
                        font.weight: Font.DemiBold
                        verticalAlignment: Text.AlignVCenter
                        color: Styles.Theme.color.onSurface
                    }

                    MD.Switch {
                        id: switchControl
                        checked: bridge ? bridge.aiPluginEnabled : false
                        onToggled: function(checked) {
                            if (bridge) bridge.setAiPluginEnabled(checked)
                        }
                    }
                }

                Row {
                    width: parent.width
                    spacing: 10

                    Text {
                        width: parent.width - editButton.width - 10
                        height: 40
                        text: bridge && bridge.aiPluginEnabled ? "已启用 · " + bridge.aiApiConfigs.length + " 个 API" : "已关闭"
                        verticalAlignment: Text.AlignVCenter
                        font.family: Styles.Theme.typography.family
                        font.pixelSize: 13
                        color: Styles.Theme.color.onSurfaceVariant
                    }

                    MD.Button {
                        id: editButton
                        width: 74
                        text: "编辑"
                        icon: "edit"
                        type: "tonal"
                        enabled: bridge && bridge.aiPluginEnabled
                        onClicked: aiConfigPopup.open()
                    }
                }
            }
        }
    }
}
