import QtQuick
import QtQuick.Controls.Basic as Controls
import "../Styles" as Styles

Controls.Slider {
    id: root

    from: 0
    to: 100
    value: 40

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        implicitWidth: 180
        implicitHeight: 4
        width: root.availableWidth
        height: implicitHeight
        radius: 2
        color: Styles.Theme.color.surfaceVariant

        Rectangle {
            width: root.visualPosition * parent.width
            height: parent.height
            radius: 2
            color: Styles.Theme.color.primary
        }
    }

    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: 20
        height: 20
        radius: 10
        color: Styles.Theme.color.primary
    }
}
