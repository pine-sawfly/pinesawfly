import QtQuick
import QtQuick.Controls
import "../Styles" as Styles

TextField {
    id: root

    property string label: ""

    implicitHeight: 56
    color: Styles.Theme.color.onSurface
    placeholderTextColor: Styles.Theme.color.onSurfaceVariant
    font.family: Styles.Theme.typography.family
    font.pixelSize: 14
    leftPadding: 16
    rightPadding: 16
    topPadding: 14

    background: Rectangle {
        radius: Styles.Theme.shape.small
        color: Styles.Theme.color.surfaceContainer
        border.color: root.activeFocus ? Styles.Theme.color.primary : Styles.Theme.color.outline
        border.width: root.activeFocus ? 2 : 1
    }
}
