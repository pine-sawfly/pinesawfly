pragma Singleton

import QtQuick

QtObject {
    id: fonts

    readonly property string uiFamily: "Segoe UI"
    readonly property string monoFamily: "Cascadia Mono"
    readonly property string iconFamily: materialIcons.status === FontLoader.Ready ? materialIcons.name : uiFamily
    readonly property bool materialIconsReady: materialIcons.status === FontLoader.Ready

    property FontLoader materialIcons: FontLoader {
        id: materialIcons
        source: typeof materialIconsFontUrl === "string" ? materialIconsFontUrl : ""
    }
}
