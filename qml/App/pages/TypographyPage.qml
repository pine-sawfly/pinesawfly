import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "Typography"
    subtitle: "类型 token 集中在 Theme.qml，页面和控件统一读取。"

    MD.Card {
        width: parent.width
        height: 340

        Text { text: "Display"; font.pixelSize: Styles.Theme.typography.display; font.family: Styles.Theme.typography.family; color: Styles.Theme.color.onSurface }
        Text { text: "Headline / 审计结果概览"; font.pixelSize: Styles.Theme.typography.headline; font.family: Styles.Theme.typography.family; color: Styles.Theme.color.onSurface }
        Text { text: "Title / SQL Injection"; font.pixelSize: Styles.Theme.typography.title; font.weight: Font.DemiBold; font.family: Styles.Theme.typography.family; color: Styles.Theme.color.onSurface }
        Text { text: "Body / 污点从 $_GET['id'] 传播至 mysqli_query。"; font.pixelSize: Styles.Theme.typography.body; font.family: Styles.Theme.typography.family; color: Styles.Theme.color.onSurfaceVariant }
        Text { text: "Label / CWE-89"; font.pixelSize: Styles.Theme.typography.label; font.weight: Font.DemiBold; font.family: Styles.Theme.typography.family; color: Styles.Theme.color.primary }
    }
}
