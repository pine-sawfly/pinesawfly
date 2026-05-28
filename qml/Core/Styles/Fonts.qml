pragma Singleton

import QtQuick

QtObject {
    id: fonts

    property var manager: null

    property int revision: 0
    property string uiFamily: manager ? manager.uiFontFamily : "Segoe UI"
    property string monoFamily: manager ? manager.editorFontFamily : "Cascadia Mono"
    readonly property string iconFamily: materialIcons.status === FontLoader.Ready ? materialIcons.name : uiFamily
    readonly property bool materialIconsReady: materialIcons.status === FontLoader.Ready

    property FontLoader materialIcons: FontLoader {
        id: materialIcons
        source: typeof materialIconsFontUrl === "string" ? materialIconsFontUrl : ""
    }

    onManagerChanged: {
        uiFamily = manager ? manager.uiFontFamily : "Segoe UI"
        monoFamily = manager ? manager.editorFontFamily : "Cascadia Mono"
    }

    onRevisionChanged: {
        uiFamily = manager ? manager.uiFontFamily : "Segoe UI"
        monoFamily = manager ? manager.editorFontFamily : "Cascadia Mono"
    }
}
