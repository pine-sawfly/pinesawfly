import QtQuick
import QtQuick.Controls
import "../Styles" as Styles
import "." as MD

Popup {
    id: root

    property string title: "Dialog"
    property string body: ""

    modal: true
    focus: true
    width: 360
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        radius: Styles.Theme.shape.large
        color: Styles.Theme.color.surfaceContainerHigh
    }

    contentItem: Item {
        implicitWidth: dialogContent.implicitWidth + 48
        implicitHeight: dialogContent.implicitHeight + 48

        Column {
            id: dialogContent
            anchors.fill: parent
            anchors.margins: 24
            spacing: 18

            Text {
                text: root.title
                font.family: Styles.Theme.typography.family
                font.pixelSize: 22
                color: Styles.Theme.color.onSurface
            }

            Text {
                text: root.body
                width: 312
                wrapMode: Text.WordWrap
                font.family: Styles.Theme.typography.family
                font.pixelSize: 14
                color: Styles.Theme.color.onSurfaceVariant
            }

            Row {
                anchors.right: parent.right
                spacing: 8
                MD.Button { text: "关闭"; type: "text"; onClicked: root.close() }
            }
        }
    }
}
