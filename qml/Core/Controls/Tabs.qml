import QtQuick
import "../Styles" as Styles

Row {
    id: root

    property var tabs: ["Overview", "Details"]
    property int currentIndex: 0
    signal selected(int index)

    spacing: 0

    Repeater {
        model: root.tabs
        delegate: Item {
            width: 120
            height: 48

            Text {
                anchors.centerIn: parent
                text: modelData
                color: index === root.currentIndex ? Styles.Theme.color.primary : Styles.Theme.color.onSurfaceVariant
                font.family: Styles.Theme.typography.family
                font.pixelSize: 14
                font.weight: Font.DemiBold
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                width: 56
                height: 3
                radius: 2
                visible: index === root.currentIndex
                color: Styles.Theme.color.primary
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    root.currentIndex = index
                    root.selected(index)
                }
            }
        }
    }
}
