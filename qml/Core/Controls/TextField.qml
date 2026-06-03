import QtQuick
import QtQuick.Controls.Basic as Controls
import "../Styles" as Styles

Controls.TextField {
    id: root

    property string label: ""
    property bool dense: false

    implicitHeight: dense ? 44 : 56
    color: Styles.Theme.color.onSurface
    placeholderTextColor: Styles.Theme.color.onSurfaceVariant
    font.family: Styles.Theme.typography.family
    font.pixelSize: 14
    leftPadding: 16
    rightPadding: 16
    topPadding: 0
    bottomPadding: 0
    verticalAlignment: TextInput.AlignVCenter

    background: Rectangle {
        radius: Styles.Theme.shape.medium
        color: Styles.Theme.color.surfaceContainer
        border.color: root.activeFocus ? Styles.Theme.color.primary : Styles.Theme.color.outline
        border.width: root.activeFocus ? 2 : 1
    }
}
