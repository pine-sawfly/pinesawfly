import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../Core/Styles" as Styles
import "../Core/Controls" as MD

Rectangle {
    id: root

    color: Styles.Theme.color.surface

    property int currentIndex: 0
    property var bridge: auditBridge
    property real windowRadius: 0
    property var pages: [
        { label: "首页", icon: "home", source: "pages/HomePage.qml" },
        { label: "组件", icon: "widgets", source: "pages/ComponentsPage.qml" },
        { label: "颜色", icon: "palette", source: "pages/ColorPage.qml" },
        { label: "字体", icon: "text_fields", source: "pages/TypographyPage.qml" },
        { label: "规则", icon: "rule", source: "pages/RulesPage.qml" },
        { label: "设置", icon: "settings", source: "pages/SettingsPage.qml" },
        { label: "关于", icon: "info", source: "pages/AboutPage.qml" }
    ]

    FolderDialog {
        id: folderDialog
        title: "选择项目目录"
        onAccepted: root.bridge.setProjectPath(selectedFolder)
    }

    Row {
        anchors.fill: parent

        Rectangle {
            id: drawer
            width: 272
            height: parent.height
            color: Styles.Theme.color.surfaceContainer
            radius: root.windowRadius

            Rectangle {
                anchors.right: parent.right
                anchors.top: parent.top
                width: parent.radius
                height: parent.height
                color: parent.color
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.width
                height: parent.radius
                color: parent.color
            }

            Column {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                Row {
                    spacing: 12
                    height: 48

                    Rectangle {
                        width: 42
                        height: 42
                        radius: 12
                        color: Styles.Theme.color.primary

                        Text {
                            anchors.centerIn: parent
                            text: "bug_report"
                            font.family: Styles.Fonts.iconFamily
                            font.pixelSize: 24
                            color: Styles.Theme.color.onPrimary
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        Text {
                            text: "PineSawFly"
                            color: Styles.Theme.color.onSurface
                            font.family: Styles.Theme.typography.family
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                        }

                        Text {
                            text: "PHP 安全审计工作台"
                            color: Styles.Theme.color.onSurfaceVariant
                            font.family: Styles.Theme.typography.family
                            font.pixelSize: 12
                        }
                    }
                }

                MD.Button {
                    width: parent.width
                    text: "打开项目"
                    icon: "folder_open"
                    type: "filled"
                    onClicked: folderDialog.open()
                }

                Column {
                    width: parent.width
                    spacing: 4

                    Repeater {
                        model: root.pages
                        delegate: Rectangle {
                            width: parent.width
                            height: 44
                            radius: 22
                            color: root.currentIndex === index ? Styles.Theme.color.primaryContainer : "transparent"

                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 16
                                spacing: 12

                                Text {
                                    text: modelData.icon
                                    font.family: Styles.Fonts.iconFamily
                                    font.pixelSize: 20
                                    color: root.currentIndex === index ? Styles.Theme.color.onPrimaryContainer : Styles.Theme.color.onSurfaceVariant
                                }

                                Text {
                                    text: modelData.label
                                    font.family: Styles.Theme.typography.family
                                    font.pixelSize: 14
                                    font.weight: root.currentIndex === index ? Font.DemiBold : Font.Normal
                                    color: root.currentIndex === index ? Styles.Theme.color.onPrimaryContainer : Styles.Theme.color.onSurfaceVariant
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.currentIndex = index
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Styles.Theme.color.outlineVariant
                }

                Text {
                    text: root.bridge ? root.bridge.projectPath : ""
                    width: parent.width
                    wrapMode: Text.WrapAnywhere
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 12
                    color: Styles.Theme.color.onSurfaceVariant
                }

                Text {
                    text: root.bridge ? root.bridge.status : ""
                    width: parent.width
                    wrapMode: Text.WordWrap
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 12
                    color: Styles.Theme.color.primary
                }

                Item { width: 1; height: 1 }
            }
        }

        Rectangle {
            width: parent.width - drawer.width
            height: parent.height
            color: Styles.Theme.color.surface
            radius: root.windowRadius

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.radius
                height: parent.height
                color: parent.color
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.width
                height: parent.radius
                color: parent.color
            }

            Loader {
                id: pageLoader
                anchors.fill: parent
                source: root.pages[root.currentIndex].source

                onLoaded: {
                    if (item && item.hasOwnProperty("bridge"))
                        item.bridge = root.bridge
                    item.opacity = 0
                    item.y = 14
                    transitionIn.restart()
                }
            }

            ParallelAnimation {
                id: transitionIn
                NumberAnimation { target: pageLoader.item; property: "opacity"; to: 1; duration: 180; easing.type: Easing.OutCubic }
                NumberAnimation { target: pageLoader.item; property: "y"; to: 0; duration: 180; easing.type: Easing.OutCubic }
            }
        }
    }

}
