import QtQuick
import QtQuick.Controls
import "../../Core/Styles" as Styles

Flickable {
    id: root

    default property alias content: contentColumn.data
    property string title: ""
    property string subtitle: ""

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight + 64

    Column {
        id: contentColumn
        width: root.width - 64
        x: 32
        y: 28
        spacing: 20

        Text {
            text: root.title
            font.family: Styles.Theme.typography.family
            font.pixelSize: 32
            font.weight: Font.DemiBold
            color: Styles.Theme.color.onSurface
        }

        Text {
            visible: root.subtitle.length > 0
            text: root.subtitle
            width: parent.width
            wrapMode: Text.WordWrap
            font.family: Styles.Theme.typography.family
            font.pixelSize: 14
            color: Styles.Theme.color.onSurfaceVariant
        }
    }
}
