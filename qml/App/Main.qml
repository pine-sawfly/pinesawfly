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

    AppRoot {
        anchors.fill: parent
    }
}
