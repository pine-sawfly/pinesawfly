import QtQuick
import "../Styles" as Styles

Item {
    id: root

    property color rippleColor: Styles.Theme.color.onSurface

    anchors.fill: parent
    clip: true
    z: 20

    function play(x, y) {
        circle.x = x - circle.width / 2
        circle.y = y - circle.height / 2
        circle.width = 0
        circle.height = 0
        circle.opacity = 0.18
        rippleAnim.restart()
    }

    Rectangle {
        id: circle
        radius: width / 2
        color: root.rippleColor
        opacity: 0
    }

    ParallelAnimation {
        id: rippleAnim
        NumberAnimation { target: circle; property: "width"; to: Math.max(root.width, root.height) * 2.2; duration: 260; easing.type: Easing.OutCubic }
        NumberAnimation { target: circle; property: "height"; to: Math.max(root.width, root.height) * 2.2; duration: 260; easing.type: Easing.OutCubic }
        NumberAnimation { target: circle; property: "opacity"; to: 0; duration: 360; easing.type: Easing.OutCubic }
    }
}
