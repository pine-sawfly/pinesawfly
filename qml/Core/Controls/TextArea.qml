import QtQuick
import QtQuick.Controls.Basic as Controls
import "../Styles" as Styles

Controls.ScrollView {
    id: root

    property bool mono: false
    property alias text: editor.text
    property alias placeholderText: editor.placeholderText
    property alias cursorPosition: editor.cursorPosition

    function insert(position, value) {
        editor.insert(position, value)
    }

    function forceActiveFocus() {
        editor.forceActiveFocus()
    }

    clip: true
    contentWidth: availableWidth
    contentHeight: Math.max(availableHeight, editor.implicitHeight)

    background: Rectangle {
        radius: Styles.Theme.shape.medium
        color: Styles.Theme.color.surfaceContainer
        border.color: editor.activeFocus ? Styles.Theme.color.primary : Styles.Theme.color.outline
        border.width: editor.activeFocus ? 2 : 1
    }

    Controls.TextArea {
        id: editor

        width: root.availableWidth
        height: Math.max(root.availableHeight, implicitHeight)
        color: Styles.Theme.color.onSurface
        placeholderTextColor: Styles.Theme.color.onSurfaceVariant
        selectedTextColor: Styles.Theme.color.onPrimary
        selectionColor: Styles.Theme.color.primary
        font.family: root.mono ? Styles.Fonts.monoFamily : Styles.Theme.typography.family
        font.pixelSize: 14
        leftPadding: 14
        rightPadding: 20
        topPadding: 12
        bottomPadding: 12
        wrapMode: TextEdit.Wrap

        background: Item {}
    }

    Controls.ScrollBar.vertical: Controls.ScrollBar {
        id: verticalBar
        policy: Controls.ScrollBar.AsNeeded
        width: 12
        padding: 2

        background: Rectangle {
            radius: 999
            color: verticalBar.hovered || verticalBar.pressed
                   ? (Styles.Theme.manager && Styles.Theme.manager.isDarkTheme ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(0, 0, 0, 0.07))
                   : "transparent"
        }

        contentItem: Rectangle {
            implicitWidth: 6
            radius: 999
            color: verticalBar.pressed || verticalBar.hovered
                   ? Styles.Theme.color.primary
                   : (Styles.Theme.manager && Styles.Theme.manager.isDarkTheme ? Qt.rgba(1, 1, 1, 0.34) : Qt.rgba(0, 0, 0, 0.28))
        }
    }
}
