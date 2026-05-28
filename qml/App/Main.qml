import QtQuick
import QtQuick.Window
import "../Core/Styles" as Styles

Window {
    id: window

    width: 1280
    height: 800
    minimumWidth: 1040
    minimumHeight: 680
    visible: true
    flags: Qt.FramelessWindowHint | Qt.Window
    title: "PineSawFly"
    color: Styles.Theme.color.surface

    Component.onCompleted: {
        Styles.Theme.manager = styleManager
        Styles.Fonts.manager = styleManager
    }

    Connections {
        target: styleManager
        function onThemeChanged() {
            Styles.Theme.revision += 1
            Styles.Fonts.revision += 1
        }
    }

    Rectangle {
        id: shell
        anchors.fill: parent
        property real windowRadius: window.visibility === Window.Maximized ? 0 : Styles.Theme.shape.large
        color: Styles.Theme.color.surface

        Rectangle {
            id: titleBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 44
            color: Styles.Theme.color.surfaceContainer

            DragHandler {
                target: null
                onActiveChanged: if (active) window.startSystemMove()
            }

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                Image {
                    width: 24
                    height: 24
                    source: "../../assets/icons/app.ico"
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                Text {
                    text: "PineSawFly"
                    font.family: Styles.Theme.typography.family
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    color: Styles.Theme.color.onSurface
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                anchors.right: parent.right
                anchors.top: parent.top
                height: parent.height

                Repeater {
                    model: [
                        { icon: "remove", action: "min" },
                        { icon: window.visibility === Window.Maximized ? "filter_none" : "crop_square", action: "max" },
                        { icon: "close", action: "close" }
                    ]

                    delegate: Rectangle {
                        width: 48
                        height: titleBar.height
                        color: "transparent"

                        Rectangle {
                            anchors.fill: parent
                            color: mouse.containsMouse
                                   ? (modelData.action === "close" ? Styles.Theme.color.error : Styles.Theme.color.surfaceVariant)
                                   : "transparent"
                        }

                        Text {
                            anchors.centerIn: parent
                            text: modelData.icon
                            font.family: Styles.Fonts.iconFamily
                            font.pixelSize: 18
                            color: mouse.containsMouse && modelData.action === "close"
                                   ? Styles.Theme.color.onError
                                   : Styles.Theme.color.onSurfaceVariant
                        }

                        MouseArea {
                            id: mouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (modelData.action === "min") {
                                    window.showMinimized()
                                } else if (modelData.action === "max") {
                                    window.visibility === Window.Maximized ? window.showNormal() : window.showMaximized()
                                } else {
                                    window.close()
                                }
                            }
                        }
                    }
                }
            }
        }

        AppRoot {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: titleBar.bottom
            anchors.bottom: parent.bottom
            windowRadius: shell.windowRadius
        }
    }
}
