import QtQuick
import "../Styles" as Styles

Rectangle {
    id: root

    property string text: ""
    property string highlightedText: ""
    property string filePath: ""
    property int targetLine: 0
    property string editorFontFamily: Styles.Fonts.monoFamily
    property real naturalContentWidth: codeText.implicitWidth + gutter.width + 20
    property real naturalContentHeight: codeText.implicitHeight + 8
    property real baseViewportWidth: Math.max(1, width - 24)
    property real baseViewportHeight: Math.max(1, height - 24)
    property bool needsHorizontalScroll: naturalContentWidth > baseViewportWidth
                                        || (naturalContentWidth > baseViewportWidth - 18 && naturalContentHeight > baseViewportHeight)
    property bool needsVerticalScroll: naturalContentHeight > baseViewportHeight
                                      || (naturalContentHeight > baseViewportHeight - 18 && naturalContentWidth > baseViewportWidth)

    onEditorFontFamilyChanged: {
        codeText.font.family = editorFontFamily
    }

    color: Styles.Theme.manager && Styles.Theme.manager.isDarkTheme ? "#111318" : "#FAF9FD"
    radius: Styles.Theme.shape.large
    border.color: Styles.Theme.color.outlineVariant
    clip: true

    Item {
        anchors.fill: parent

        Flickable {
            id: flick
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.right: root.needsVerticalScroll ? verticalTrack.left : parent.right
            anchors.bottom: root.needsHorizontalScroll ? horizontalTrack.top : parent.bottom
            anchors.margins: 12
            anchors.rightMargin: root.needsVerticalScroll ? 8 : 12
            anchors.bottomMargin: root.needsHorizontalScroll ? 8 : 12
            contentWidth: Math.max(width, root.naturalContentWidth)
            contentHeight: Math.max(height, root.naturalContentHeight)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            flickDeceleration: 3500
            maximumFlickVelocity: 5200

            Row {
                y: 0

                Column {
                    id: gutter
                    width: Math.max(44, String(lines.length).length * 10 + 24)

                    Repeater {
                        model: lines.length
                        delegate: Text {
                            width: gutter.width - 10
                            height: 20
                            text: index + 1
                            horizontalAlignment: Text.AlignRight
                            font.family: root.editorFontFamily
                            font.pixelSize: 13
                            color: Styles.Theme.color.onSurfaceVariant
                        }
                    }
                }

                Text {
                    id: codeText
                    text: root.highlightedText.length ? root.highlightedText : root.text
                    textFormat: root.highlightedText.length ? Text.RichText : Text.PlainText
                    font.family: root.editorFontFamily
                    font.pixelSize: 13
                    lineHeightMode: Text.FixedHeight
                    lineHeight: 20
                    color: Styles.Theme.color.onSurface
                    wrapMode: Text.NoWrap
                }
            }
        }

        Rectangle {
            id: verticalTrack
            width: 10
            radius: 999
            anchors.right: parent.right
            anchors.rightMargin: 4
            anchors.top: parent.top
            anchors.topMargin: 12
            anchors.bottom: root.needsHorizontalScroll ? horizontalTrack.top : parent.bottom
            anchors.bottomMargin: root.needsHorizontalScroll ? 8 : 12
            visible: root.needsVerticalScroll
            color: Qt.rgba(0, 0, 0, verticalMouse.containsMouse || verticalDrag.active ? 0.08 : 0.03)

            Rectangle {
                id: verticalThumb
                x: 2
                width: 6
                radius: 999
                height: Math.max(36, verticalTrack.height * flick.height / Math.max(flick.contentHeight, 1))
                y: flick.contentY <= 0 ? 2 : Math.min(verticalTrack.height - height - 2, 2 + (verticalTrack.height - height - 4) * flick.contentY / Math.max(1, flick.contentHeight - flick.height))
                color: verticalDrag.active ? Styles.Theme.color.primary : Qt.rgba(0, 0, 0, Styles.Theme.manager && Styles.Theme.manager.isDarkTheme ? 0.55 : 0.30)

                DragHandler {
                    id: verticalDrag
                    property real previousY: 0
                    target: null
                    yAxis.enabled: true
                    xAxis.enabled: false
                    onActiveChanged: previousY = active ? translation.y : 0
                    onTranslationChanged: {
                        var available = Math.max(1, verticalTrack.height - verticalThumb.height - 4)
                        var delta = translation.y - previousY
                        previousY = translation.y
                        flick.contentY = Math.max(0, Math.min(flick.contentHeight - flick.height, flick.contentY + delta * (flick.contentHeight - flick.height) / available))
                    }
                }
            }

            MouseArea {
                id: verticalMouse
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }
        }

        Rectangle {
            id: horizontalTrack
            height: 10
            radius: 999
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: root.needsVerticalScroll ? verticalTrack.left : parent.right
            anchors.rightMargin: root.needsVerticalScroll ? 8 : 12
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 4
            visible: root.needsHorizontalScroll
            color: Qt.rgba(0, 0, 0, horizontalMouse.containsMouse || horizontalDrag.active ? 0.08 : 0.03)

            Rectangle {
                id: horizontalThumb
                y: 2
                height: 6
                radius: 999
                width: Math.max(36, horizontalTrack.width * flick.width / Math.max(flick.contentWidth, 1))
                x: flick.contentX <= 0 ? 2 : Math.min(horizontalTrack.width - width - 2, 2 + (horizontalTrack.width - width - 4) * flick.contentX / Math.max(1, flick.contentWidth - flick.width))
                color: horizontalDrag.active ? Styles.Theme.color.primary : Qt.rgba(0, 0, 0, Styles.Theme.manager && Styles.Theme.manager.isDarkTheme ? 0.55 : 0.30)

                DragHandler {
                    id: horizontalDrag
                    property real previousX: 0
                    target: null
                    xAxis.enabled: true
                    yAxis.enabled: false
                    onActiveChanged: previousX = active ? translation.x : 0
                    onTranslationChanged: {
                        var available = Math.max(1, horizontalTrack.width - horizontalThumb.width - 4)
                        var delta = translation.x - previousX
                        previousX = translation.x
                        flick.contentX = Math.max(0, Math.min(flick.contentWidth - flick.width, flick.contentX + delta * (flick.contentWidth - flick.width) / available))
                    }
                }
            }

            MouseArea {
                id: horizontalMouse
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }
        }
    }

    property var lines: text.length ? text.split(/\r\n|\r|\n/) : [""]
}
