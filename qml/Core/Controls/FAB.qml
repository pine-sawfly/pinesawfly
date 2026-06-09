import QtQuick
import "../Styles" as Styles
import "." as MD

Rectangle {
    id: root

    property string icon: "add"
    signal clicked()

    width: 56
    height: 56
    radius: Styles.Theme.shape.large
    color: Styles.Theme.color.primaryContainer

    Text {
        anchors.centerIn: parent
        text: root.icon
        font.family: Styles.Fonts.iconFamily
        font.pixelSize: 26
        color: Styles.Theme.color.onPrimaryContainer
    }

    MD.Ripple { id: ripple; rippleColor: Styles.Theme.color.onPrimaryContainer }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onPressed: function(mouse) {
            ripple.play(mouse.x, mouse.y)
        }
        onClicked: root.clicked()
    }
}
