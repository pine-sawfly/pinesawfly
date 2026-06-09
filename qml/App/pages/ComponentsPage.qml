import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "Components"

    property bool switchValue: true
    property bool checkboxValue: true

    Flow {
        width: parent.width
        spacing: 18

        MD.Card {
            width: 330
            height: 220
            Text { text: "Buttons"; font.pixelSize: 18; font.weight: Font.DemiBold; color: Styles.Theme.color.onSurface }
            Row {
                spacing: 10
                MD.Button { text: "Filled"; icon: "check" }
                MD.Button { text: "Tonal"; icon: "tune"; type: "tonal" }
                MD.Button { text: "Outlined"; icon: "open_in_new"; type: "outlined" }
            }
        }

        MD.Card {
            width: 330
            height: 220
            Text { text: "Selection"; font.pixelSize: 18; font.weight: Font.DemiBold; color: Styles.Theme.color.onSurface }
            Row {
                spacing: 24
                MD.Switch { checked: true; onToggled: switchValue = checked }
                MD.Checkbox { text: "启用规则"; checked: true; onToggled: checkboxValue = checked }
            }
        }

        MD.Card {
            width: 330
            height: 220
            Text { text: "Input"; font.pixelSize: 18; font.weight: Font.DemiBold; color: Styles.Theme.color.onSurface }
            MD.TextField { width: 260; placeholderText: "规则名称或 CWE" }
            MD.Slider { width: 260; value: 64 }
        }

        MD.Card {
            width: 330
            height: 220
            Text { text: "Tabs"; font.pixelSize: 18; font.weight: Font.DemiBold; color: Styles.Theme.color.onSurface }
            MD.Tabs { tabs: ["源码", "漏洞", "报告"] }
        }

        MD.Card {
            width: 330
            height: 220
            Text { text: "Dialog"; font.pixelSize: 18; font.weight: Font.DemiBold; color: Styles.Theme.color.onSurface }
            MD.Button { text: "打开对话框"; icon: "open_in_new"; onClicked: demoDialog.open() }
            MD.Dialog {
                id: demoDialog
                title: "审计提示"
                body: "这里可以承载规则说明、漏洞详情或导出确认。"
            }
        }

        Item {
            width: 330
            height: 220
            MD.FAB {
                anchors.centerIn: parent
                icon: "add"
            }
        }
    }
}
