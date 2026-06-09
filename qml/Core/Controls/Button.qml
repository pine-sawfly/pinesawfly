import QtQuick
import QtQuick.Controls
import "../Styles" as Styles

Item {
    id: root

    property string text: ""
    property string icon: ""
    property string type: "filled"
    property bool enabled: true
    signal clicked()

    implicitWidth: Math.max(88, label.implicitWidth + (icon.length > 0 ? 28 : 0) + 32)
    implicitHeight: 40
    width: implicitWidth
    height: implicitHeight

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: Styles.Theme.shape.full
        color: root.containerColor()
        border.width: root.type === "outlined" ? 1 : 0
        border.color: Styles.Theme.color.outline

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: root.contentColor()
            opacity: root.isHovered ? Styles.Theme.state.hover : 0
        }

        Ripple { id: ripple; rippleColor: root.contentColor() }
    }

    Row {
        spacing: 8
        anchors.centerIn: parent
        height: parent.height

        Text {
            visible: root.icon.length > 0
            width: visible ? 20 : 0
            height: parent.height
            text: root.icon
            font.family: Styles.Fonts.iconFamily
            font.pixelSize: 18
            color: root.contentColor()
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            id: label
            height: parent.height
            text: root.text
            font.family: Styles.Theme.typography.family
            font.pixelSize: 14
            font.weight: Font.DemiBold
            color: root.contentColor()
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        enabled: root.enabled
        onEntered: root.isHovered = true
        onExited: root.isHovered = false
        onPressed: function(mouse) {
            ripple.play(mouse.x, mouse.y)
        }
        onClicked: root.clicked()
    }

    property bool isHovered: false

    function containerColor() {
        if (!enabled) return Qt.rgba(0, 0, 0, Styles.Theme.state.disabledContainer)
        if (type === "filled") return Styles.Theme.color.primary
        if (type === "tonal") return Styles.Theme.color.primaryContainer
        return "transparent"
    }

    function contentColor() {
        if (!enabled) return Qt.rgba(0, 0, 0, Styles.Theme.state.disabledContent)
        if (type === "filled") return Styles.Theme.color.onPrimary
        if (type === "tonal") return Styles.Theme.color.onPrimaryContainer
        if (type === "text") return Styles.Theme.color.primary
        return Styles.Theme.color.primary
    }
}
