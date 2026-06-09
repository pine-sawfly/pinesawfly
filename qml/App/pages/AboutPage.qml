import QtQuick
import "../../Core/Styles" as Styles
import "../../Core/Controls" as MD

PageFrame {
    title: "About"

    MD.Card {
        width: parent.width
        height: 440

        Row {
            spacing: 18

            Image {
                width: 72
                height: 72
                source: "../../../assets/icons/app.ico"
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            Column {
                spacing: 4
                Text {
                    text: "PineSawFly"
                    font.pixelSize: 26
                    font.weight: Font.DemiBold
                    color: Styles.Theme.color.onSurface
                }

                Text {
                    text: "WEB 安全桌面审计应用"
                    font.pixelSize: 14
                    color: Styles.Theme.color.onSurfaceVariant
                }
            }
        }

        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            text: "PineSawFly是一个WEB安全桌面审计应用，用于扫描整个项目中的后端代码、规则命中和污点传播路径，并将发现整理为可复查、可导出的安全审计报告。"
            font.pixelSize: 14
            lineHeight: 1.35
            color: Styles.Theme.color.onSurfaceVariant
        }

        Text {
            text: "架构"
            font.pixelSize: 18
            font.weight: Font.DemiBold
            color: Styles.Theme.color.onSurface
        }

        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            text: "应用由 PySide6/QML 前端、Python 桥接层、规则引擎、PHP AST/污点分析插件和报告模板系统组成。前端负责项目打开、扫描触发、结果查看、规则管理和模板编辑；桥接层负责线程调度、文件读取、结果归一化和导出；扫描引擎结合 JSON 规则、tree-sitter 语法分析、污点传播和 CodeGraph 初始化结果生成发现；报告模块将漏洞位置、传递链路和证据代码片段渲染为 Markdown、HTML、PDF、JSON 或 TXT。"
            font.pixelSize: 14
            lineHeight: 1.35
            color: Styles.Theme.color.onSurfaceVariant
        }
    }
}
