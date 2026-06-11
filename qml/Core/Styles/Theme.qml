pragma Singleton

import QtQuick

QtObject {
    id: theme

    property var manager: null
    property int revision: 0
    property var color: manager ? manager.currentScheme : fallbackScheme
    property var fallbackScheme: ({
        primary: "#006A60",
        onPrimary: "#FFFFFF",
        primaryContainer: "#9FF2E5",
        onPrimaryContainer: "#00201C",
        secondary: "#4A635F",
        onSecondary: "#FFFFFF",
        surface: "#F4FFFC",
        surfaceContainer: "#DCEDEA",
        surfaceContainerHigh: "#D1E5E1",
        surfaceVariant: "#DAE5E1",
        onSurface: "#1D1B20",
        onSurfaceVariant: "#49454F",
        outline: "#79747E",
        outlineVariant: "#CAC4D0",
        background: "#F4FFFC",
        error: "#B3261E",
        onError: "#FFFFFF"
    })

    property var typography: ({
        display: 40,
        headline: 28,
        title: 20,
        body: 14,
        label: 12,
        family: manager ? manager.uiFontFamily : "Segoe UI"
    })

    property var shape: ({
        extraSmall: 4,
        small: 8,
        medium: 12,
        large: 16,
        full: 999
    })

    property var elevation: ({
        level0: 0,
        level1: 1,
        level2: 3,
        level3: 6
    })

    property var state: ({
        hover: 0.08,
        focus: 0.12,
        pressed: 0.12,
        disabledContent: 0.38,
        disabledContainer: 0.12
    })

    onRevisionChanged: color = manager ? manager.currentScheme : fallbackScheme
}
