import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "Color"

    property var swatches: [
        "primary", "onPrimary", "primaryContainer", "onPrimaryContainer",
        "secondary", "surface", "surfaceContainer", "surfaceVariant",
        "onSurface", "onSurfaceVariant", "outline", "error"
    ]

    Flow {
        width: parent.width
        spacing: 14

        Repeater {
            model: swatches
            delegate: MD.Card {
                width: 210
                height: 132

                Rectangle {
                    width: parent.width
                    height: 54
                    radius: Styles.Theme.shape.medium
                    color: Styles.Theme.color[modelData]
                    border.color: Styles.Theme.color.outlineVariant
                    border.width: 1
                }

                Text {
                    text: modelData
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    color: Styles.Theme.color.onSurface
                }

                Text {
                    text: Styles.Theme.color[modelData]
                    font.pixelSize: 12
                    color: Styles.Theme.color.onSurfaceVariant
                }
            }
        }
    }
}
