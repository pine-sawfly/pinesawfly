import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import Qt5Compat.GraphicalEffects
import "../Core/Styles" as Styles
import "../Core/Controls" as MD

Rectangle {
    id: root

    color: Styles.Theme.color.surface

    property int currentIndex: 0
    property var bridge: auditBridge
    property real windowRadius: 0
    property bool drawerCollapsed: false
    property int drawerExpandedWidth: 272
    property int drawerCollapsedWidth: 72
    property color pendingSeedColor: "#006A60"
    property real themeWaveStartX: 0
    property real themeWaveStartY: 0
    property real themeMaskRadius: 0
    property real themeMaskMaxRadius: 0
    property url themeMaskImage: ""
    property bool themeMaskPending: false
    property var pages: [
        { label: "首页", icon: "home", source: "pages/HomePage.qml" },
        { label: "插件", icon: "extension", source: "pages/ComponentsPage.qml" },
        { label: "颜色", icon: "palette", source: "pages/ColorPage.qml" },
        { label: "字体", icon: "text_fields", source: "pages/TypographyPage.qml" },
        { label: "规则", icon: "rule", source: "pages/RulesPage.qml" },
        { label: "报告", icon: "summarize", source: "pages/ReportPage.qml" },
        { label: "设置", icon: "settings", source: "pages/SettingsPage.qml" },
        { label: "关于", icon: "info", source: "pages/AboutPage.qml" }
    ]

    function playThemeWave(seedColor, sourceItem, localX, localY) {
        var point = sourceItem.mapToItem(root, localX, localY)
        pendingSeedColor = seedColor
        themeWaveStartX = point.x
        themeWaveStartY = point.y
        themeMaskMaxRadius = Math.max(
                    Math.sqrt(point.x * point.x + point.y * point.y),
                    Math.sqrt((width - point.x) * (width - point.x) + point.y * point.y),
                    Math.sqrt(point.x * point.x + (height - point.y) * (height - point.y)),
                    Math.sqrt((width - point.x) * (width - point.x) + (height - point.y) * (height - point.y)))
        themeMaskRadius = 0
        themeMaskPending = true
        root.grabToImage(function(result) {
            themeMaskImage = result.url
            oldThemeImage.source = themeMaskImage
            themeTransitionLayer.visible = true
            if (styleManager)
                styleManager.setSeedColor(root.pendingSeedColor)
            themeMaskPending = false
            themeMaskAnimation.restart()
        })
    }

    FolderDialog {
        id: folderDialog
        title: "选择项目目录"
        onAccepted: root.bridge.setProjectPath(selectedFolder)
    }

    Row {
        id: appContent
        anchors.fill: parent

        Rectangle {
            id: drawer
            width: root.drawerCollapsed ? root.drawerCollapsedWidth : root.drawerExpandedWidth
            height: parent.height
            color: Styles.Theme.color.surfaceContainer
            radius: root.windowRadius

            Behavior on width { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

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
                    width: parent.width
                    spacing: root.drawerCollapsed ? 0 : 12
                    height: 48

                    Rectangle {
                        id: drawerToggle
                        width: 42
                        height: 42
                        radius: 12
                        color: Styles.Theme.color.primary

                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            color: Styles.Theme.color.onPrimary
                            opacity: logoMouse.containsMouse ? Styles.Theme.state.hover : 0
                        }

                        MD.LogoIcon {
                            anchors.centerIn: parent
                            iconColor: Styles.Theme.color.onPrimary
                            width: 26
                            height: 26
                        }

                        MouseArea {
                            id: logoMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.drawerCollapsed = !root.drawerCollapsed
                        }

                        ToolTip.visible: logoMouse.containsMouse
                        ToolTip.text: root.drawerCollapsed ? "展开侧边栏" : "折叠侧边栏"
                    }

                    Column {
                        visible: !root.drawerCollapsed
                        opacity: root.drawerCollapsed ? 0 : 1
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
                            text: "WEB 安全审计工作台"
                            color: Styles.Theme.color.onSurfaceVariant
                            font.family: Styles.Theme.typography.family
                            font.pixelSize: 12
                        }
                    }
                }

                MD.Button {
                    visible: !root.drawerCollapsed
                    opacity: root.drawerCollapsed ? 0 : 1
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
                            id: navItem
                            width: parent.width
                            height: 44
                            radius: 22
                            color: root.currentIndex === index
                                   ? Styles.Theme.color.primaryContainer
                                   : (navMouse.containsMouse ? Styles.Theme.color.surfaceContainerHigh : "transparent")

                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: root.drawerCollapsed ? (parent.width - implicitWidth) / 2 : 16
                                spacing: 12

                                Text {
                                    text: modelData.icon
                                    font.family: Styles.Fonts.iconFamily
                                    font.pixelSize: 20
                                    color: root.currentIndex === index ? Styles.Theme.color.onPrimaryContainer : Styles.Theme.color.onSurfaceVariant
                                }

                                Text {
                                    visible: !root.drawerCollapsed
                                    text: modelData.label
                                    font.family: Styles.Theme.typography.family
                                    font.pixelSize: 14
                                    font.weight: root.currentIndex === index ? Font.DemiBold : Font.Normal
                                    color: root.currentIndex === index ? Styles.Theme.color.onPrimaryContainer : Styles.Theme.color.onSurfaceVariant
                                }
                            }

                            MouseArea {
                                id: navMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.currentIndex = index
                            }
                        }
                    }
                }

                Rectangle {
                    visible: !root.drawerCollapsed
                    width: parent.width
                    height: 1
                    color: Styles.Theme.color.outlineVariant
                }

                Text {
                    visible: !root.drawerCollapsed
                    text: root.bridge ? root.bridge.projectPath : ""
                    width: parent.width
                    wrapMode: Text.WrapAnywhere
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 12
                    color: Styles.Theme.color.onSurfaceVariant
                }

                Text {
                    visible: !root.drawerCollapsed
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
                    if (item) {
                        try { item.bridge = root.bridge } catch (error) {}
                        try { item.themeHost = root } catch (error) {}
                    }
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

    Item {
        id: themeTransitionLayer
        anchors.fill: parent
        visible: false
        z: 1000

        Image {
            id: oldThemeImage
            anchors.fill: parent
            fillMode: Image.Stretch
            cache: false
        }

        OpacityMask {
            anchors.fill: parent
            cached: false
            source: ShaderEffectSource {
                sourceItem: appContent
                live: true
                hideSource: false
            }
            maskSource: Item {
                width: root.width
                height: root.height

                Rectangle {
                    width: root.themeMaskRadius * 2
                    height: width
                    radius: width / 2
                    x: root.themeWaveStartX - root.themeMaskRadius
                    y: root.themeWaveStartY - root.themeMaskRadius
                    color: "black"
                    visible: root.themeMaskRadius > 0
                }
            }
        }
    }

    SequentialAnimation {
        id: themeMaskAnimation
        NumberAnimation {
            target: root
            property: "themeMaskRadius"
            to: root.themeMaskMaxRadius
            duration: 620
            easing.type: Easing.OutCubic
        }

        ScriptAction {
            script: {
                themeTransitionLayer.visible = false
                oldThemeImage.source = ""
                root.themeMaskImage = ""
                root.themeMaskRadius = 0
            }
        }
    }

}
