import QtQuick
import QtQuick.Window
import "../Core/Styles" as Styles

Window {
    width: 1280
    height: 800
    minimumWidth: 1040
    minimumHeight: 680
    visible: true
    title: "PineSawFly"
    color: Styles.Theme.color.background

    Component.onCompleted: Styles.Theme.manager = styleManager

    AppRoot {
        anchors.fill: parent
    }
}
