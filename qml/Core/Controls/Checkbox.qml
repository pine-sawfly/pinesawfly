import QtQuick
import "../Styles" as Styles

Item {
    id: root

    property bool checked: false
    property string text: ""
    signal toggled(bool checked)

    implicitWidth: row.implicitWidth
    implicitHeight: 32

    Row {
        id: row
        spacing: 10
        anchors.verticalCenter: parent.verticalCenter

        Rectangle {
            width: 20
            height: 20
            radius: 3
            color: root.checked ? Styles.Theme.color.primary : "transparent"
            border.color: root.checked ? Styles.Theme.color.primary : Styles.Theme.color.outline

            Text {
                anchors.centerIn: parent
                visible: root.checked
                text: "check"
                font.family: Styles.Fonts.iconFamily
                font.pixelSize: 17
                color: Styles.Theme.color.onPrimary
            }
        }

        Text {
            text: root.text
            font.family: Styles.Theme.typography.family
            font.pixelSize: 14
            color: Styles.Theme.color.onSurface
            anchors.verticalCenter: parent.verticalCenter
        }
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
