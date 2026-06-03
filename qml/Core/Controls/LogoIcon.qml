import QtQuick
import Qt5Compat.GraphicalEffects

Item {
    id: root

    property alias source: sourceImage.source
    property color iconColor: "black"
    property bool enableSmooth: true

    implicitWidth: 24
    implicitHeight: 24

    Image {
        id: sourceImage
        anchors.fill: parent
        source: "../../../assets/icons/app.svg"
        fillMode: Image.PreserveAspectFit
        smooth: root.enableSmooth
        mipmap: root.enableSmooth
        visible: false
    }

    ColorOverlay {
        anchors.fill: sourceImage
        source: sourceImage
        color: root.iconColor
    }
}
