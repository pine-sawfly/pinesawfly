from __future__ import annotations

from PySide6.QtCore import QObject, Property, QSettings, Signal, Slot


class StyleManager(QObject):
    """Expose Material-like color schemes to QML."""

    themeChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings("PineSawFly", "PineSawFly")
        self._seed_color = self._settings.value("theme/seedColor", "#006A60", str)
        self._is_dark_theme = self._settings.value("theme/isDarkTheme", False, bool)
        self._ui_font_family = self._settings.value("fonts/uiFamily", "Segoe UI", str)
        self._editor_font_family = self._settings.value("fonts/editorFamily", "Cascadia Mono", str)
        self._light_scheme = self._build_scheme(False, self._seed_color)
        self._dark_scheme = self._build_scheme(True, self._seed_color)

    def _build_scheme(self, dark: bool, seed: str) -> dict[str, str]:
        palettes = {
            "#6750A4": {
                "primary": "#6750A4",
                "secondary": "#625B71",
                "tertiary": "#7D5260",
                "error": "#B3261E",
                "lightPrimaryContainer": "#EADDFF",
                "lightOnPrimaryContainer": "#21005D",
                "lightSurface": "#FFFBFE",
                "lightSurfaceContainer": "#F3EDF7",
                "lightSurfaceContainerHigh": "#ECE6F0",
                "lightSurfaceVariant": "#E7E0EC",
                "darkPrimaryContainer": "#4F378B",
                "darkOnPrimaryContainer": "#EADDFF",
            },
            "#006A60": {
                "primary": "#006A60",
                "secondary": "#4A635F",
                "tertiary": "#456179",
                "error": "#B3261E",
                "lightPrimaryContainer": "#9FF2E5",
                "lightOnPrimaryContainer": "#00201C",
                "lightSurface": "#F4FFFC",
                "lightSurfaceContainer": "#DCEDEA",
                "lightSurfaceContainerHigh": "#D1E5E1",
                "lightSurfaceVariant": "#DAE5E1",
                "darkPrimaryContainer": "#005047",
                "darkOnPrimaryContainer": "#9FF2E5",
            },
            "#8C1D18": {
                "primary": "#8C1D18",
                "secondary": "#775653",
                "tertiary": "#705C2E",
                "error": "#B3261E",
                "lightPrimaryContainer": "#FFDAD5",
                "lightOnPrimaryContainer": "#410001",
                "lightSurface": "#FFFBFF",
                "lightSurfaceContainer": "#F9E4E1",
                "lightSurfaceContainerHigh": "#F1D8D5",
                "lightSurfaceVariant": "#F5DDDA",
                "darkPrimaryContainer": "#73342D",
                "darkOnPrimaryContainer": "#FFDAD5",
            },
            "#00639B": {
                "primary": "#00639B",
                "secondary": "#526070",
                "tertiary": "#695779",
                "error": "#B3261E",
                "lightPrimaryContainer": "#CFE5FF",
                "lightOnPrimaryContainer": "#001D33",
                "lightSurface": "#FCFCFF",
                "lightSurfaceContainer": "#E3EEF8",
                "lightSurfaceContainerHigh": "#D8E6F2",
                "lightSurfaceVariant": "#DDE3EA",
                "darkPrimaryContainer": "#004A77",
                "darkOnPrimaryContainer": "#CFE5FF",
            },
        }
        base = palettes.get(seed.upper(), palettes["#006A60"])

        if dark:
            return {
                **base,
                "primary": self._darken_for_dark(base["primary"]),
                "onPrimary": "#1F1A24",
                "primaryContainer": base["darkPrimaryContainer"],
                "onPrimaryContainer": base["darkOnPrimaryContainer"],
                "secondary": "#CCC2DC",
                "onSecondary": "#332D41",
                "surface": "#141218",
                "surfaceContainer": "#211F26",
                "surfaceContainerHigh": "#2B2930",
                "surfaceVariant": "#49454F",
                "onSurface": "#E6E0E9",
                "onSurfaceVariant": "#CAC4D0",
                "outline": "#938F99",
                "outlineVariant": "#49454F",
                "background": "#141218",
                "scrim": "#000000",
                "error": "#F2B8B5",
                "onError": "#601410",
            }

        return {
            **base,
            "onPrimary": "#FFFFFF",
            "primaryContainer": base["lightPrimaryContainer"],
            "onPrimaryContainer": base["lightOnPrimaryContainer"],
            "secondary": base["secondary"],
            "onSecondary": "#FFFFFF",
            "surface": base["lightSurface"],
            "surfaceContainer": base["lightSurfaceContainer"],
            "surfaceContainerHigh": base["lightSurfaceContainerHigh"],
            "surfaceVariant": base["lightSurfaceVariant"],
            "onSurface": "#1D1B20",
            "onSurfaceVariant": "#49454F",
            "outline": "#79747E",
            "outlineVariant": "#CAC4D0",
            "background": base["lightSurface"],
            "scrim": "#000000",
            "error": base["error"],
            "onError": "#FFFFFF",
        }

    def _darken_for_dark(self, color: str) -> str:
        mapping = {
            "#6750A4": "#D0BCFF",
            "#006A60": "#80D5C8",
            "#8C1D18": "#FFB4AB",
            "#00639B": "#9DCAFF",
        }
        return mapping.get(color.upper(), "#D0BCFF")

    def _refresh(self) -> None:
        self._light_scheme = self._build_scheme(False, self._seed_color)
        self._dark_scheme = self._build_scheme(True, self._seed_color)
        self.themeChanged.emit()

    def get_current_scheme(self) -> dict[str, str]:
        return self._dark_scheme if self._is_dark_theme else self._light_scheme

    def get_light_scheme(self) -> dict[str, str]:
        return self._light_scheme

    def get_dark_scheme(self) -> dict[str, str]:
        return self._dark_scheme

    def get_seed_color(self) -> str:
        return self._seed_color

    def set_seed_color(self, value: str) -> None:
        if value and value != self._seed_color:
            self._seed_color = value
            self._settings.setValue("theme/seedColor", self._seed_color)
            self._refresh()

    def get_is_dark_theme(self) -> bool:
        return self._is_dark_theme

    def set_is_dark_theme(self, value: bool) -> None:
        if value != self._is_dark_theme:
            self._is_dark_theme = value
            self._settings.setValue("theme/isDarkTheme", self._is_dark_theme)
            self.themeChanged.emit()

    def get_ui_font_family(self) -> str:
        return self._ui_font_family

    def set_ui_font_family(self, value: str) -> None:
        value = value.strip() if value else "Segoe UI"
        if value != self._ui_font_family:
            self._ui_font_family = value
            self._settings.setValue("fonts/uiFamily", self._ui_font_family)
            self.themeChanged.emit()

    def get_editor_font_family(self) -> str:
        return self._editor_font_family

    def set_editor_font_family(self, value: str) -> None:
        value = value.strip() if value else "Cascadia Mono"
        if value != self._editor_font_family:
            self._editor_font_family = value
            self._settings.setValue("fonts/editorFamily", self._editor_font_family)
            self.themeChanged.emit()

    @Slot(str)
    def setSeedColor(self, value: str) -> None:
        self.set_seed_color(value)

    @Slot(bool)
    def setDarkTheme(self, value: bool) -> None:
        self.set_is_dark_theme(value)

    @Slot(str)
    def setUiFontFamily(self, value: str) -> None:
        self.set_ui_font_family(value)

    @Slot(str)
    def setEditorFontFamily(self, value: str) -> None:
        self.set_editor_font_family(value)

    currentScheme = Property("QVariantMap", get_current_scheme, notify=themeChanged)
    lightScheme = Property("QVariantMap", get_light_scheme, notify=themeChanged)
    darkScheme = Property("QVariantMap", get_dark_scheme, notify=themeChanged)
    seedColor = Property(str, get_seed_color, set_seed_color, notify=themeChanged)
    isDarkTheme = Property(bool, get_is_dark_theme, set_is_dark_theme, notify=themeChanged)
    uiFontFamily = Property(str, get_ui_font_family, set_ui_font_family, notify=themeChanged)
    editorFontFamily = Property(str, get_editor_font_family, set_editor_font_family, notify=themeChanged)
