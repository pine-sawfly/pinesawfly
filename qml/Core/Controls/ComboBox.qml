import QtQuick
import QtQuick.Controls
import "../Styles" as Styles

Item {
    id: root

    property var model: []
    property string currentText: ""
    property string placeholderText: ""
    signal activated(string text)

    width: 320
    height: 56

    onCurrentTextChanged: {
        if (popup.opened && list.currentIndex !== root.model.indexOf(root.currentText))
            list.currentIndex = Math.max(0, root.model.indexOf(root.currentText))
    }

    Rectangle {
        anchors.fill: parent
        radius: Styles.Theme.shape.small
        color: Styles.Theme.color.surfaceContainer
        border.width: popup.opened ? 2 : 1
        border.color: popup.opened ? Styles.Theme.color.primary : Styles.Theme.color.outline
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.right: arrow.left
        anchors.verticalCenter: parent.verticalCenter
        text: root.currentText.length ? root.currentText : root.placeholderText
        elide: Text.ElideRight
        font.family: Styles.Theme.typography.family
        font.pixelSize: 14
        color: root.currentText.length ? Styles.Theme.color.onSurface : Styles.Theme.color.onSurfaceVariant
    }

    Text {
        id: arrow
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        text: popup.opened ? "expand_less" : "expand_more"
        font.family: Styles.Fonts.iconFamily
        font.pixelSize: 22
        color: Styles.Theme.color.onSurfaceVariant
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: popup.opened ? popup.close() : popup.open()
    }

    Popup {
        id: popup
        x: 0
        y: root.height + 6
        width: root.width
        height: Math.min(320, list.contentHeight + 12)
        padding: 6
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Styles.Theme.shape.medium
            color: Styles.Theme.color.surfaceContainerHigh
            border.color: Styles.Theme.color.outlineVariant
            border.width: 1
        }

        contentItem: ListView {
            id: list
            clip: true
            model: root.model
            currentIndex: Math.max(0, root.model.indexOf(root.currentText))

            delegate: Rectangle {
                width: list.width
                height: 40
                radius: 8
                color: modelData === root.currentText ? Styles.Theme.color.primaryContainer : (hover.containsMouse ? Styles.Theme.color.surfaceVariant : "transparent")

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData
                    elide: Text.ElideRight
                    font.family: modelData
                    font.pixelSize: 14
                    color: modelData === root.currentText ? Styles.Theme.color.onPrimaryContainer : Styles.Theme.color.onSurface
                }

                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.currentText = modelData
                        root.activated(modelData)
                        popup.close()
                    }
                }
            }
        }
    }
}
