import QtQuick
import "../Styles" as Styles

Item {
    id: root

    property bool checked: false
    signal toggled(bool checked)

    width: 52
    height: 32

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.checked ? Styles.Theme.color.primary : Styles.Theme.color.surfaceVariant
        border.color: root.checked ? Styles.Theme.color.primary : Styles.Theme.color.outline
    }

    Rectangle {
        width: root.checked ? 24 : 16
        height: width
        radius: width / 2
        x: root.checked ? root.width - width - 4 : 8
        anchors.verticalCenter: parent.verticalCenter
        color: root.checked ? Styles.Theme.color.onPrimary : Styles.Theme.color.outline
        Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            root.checked = !root.checked
            root.toggled(root.checked)
        }
    }
}
