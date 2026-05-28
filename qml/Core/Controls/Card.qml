import QtQuick
import "../Styles" as Styles

Rectangle {
    id: root

    default property alias content: body.data
    property string title: ""
    property string subtitle: ""

    radius: Styles.Theme.shape.small
    color: Styles.Theme.color.surfaceContainer
    border.color: Styles.Theme.color.outlineVariant
    border.width: 1
    implicitHeight: body.implicitHeight + 32

    Column {
        id: body
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10
    }
}
