from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot


class StyleManager(QObject):
    """Expose Material-like color schemes to QML."""

    themeChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._seed_color = "#6750A4"
        self._is_dark_theme = False
        self._light_scheme = self._build_scheme(False, self._seed_color)
        self._dark_scheme = self._build_scheme(True, self._seed_color)

    def _build_scheme(self, dark: bool, seed: str) -> dict[str, str]:
        palettes = {
            "#6750A4": {
                "primary": "#6750A4",
                "secondary": "#625B71",
                "tertiary": "#7D5260",
                "error": "#B3261E",
            },
            "#006A60": {
                "primary": "#006A60",
                "secondary": "#4A635F",
                "tertiary": "#456179",
                "error": "#B3261E",
            },
            "#8C1D18": {
                "primary": "#8C1D18",
                "secondary": "#775653",
                "tertiary": "#705C2E",
                "error": "#B3261E",
            },
            "#00639B": {
                "primary": "#00639B",
                "secondary": "#526070",
                "tertiary": "#695779",
                "error": "#B3261E",
            },
        }
        base = palettes.get(seed.upper(), palettes["#6750A4"])

        if dark:
            return {
                **base,
                "primary": self._darken_for_dark(base["primary"]),
                "onPrimary": "#1F1A24",
                "primaryContainer": "#4F378B",
                "onPrimaryContainer": "#EADDFF",
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
            "primaryContainer": "#EADDFF",
            "onPrimaryContainer": "#21005D",
            "secondary": base["secondary"],
            "onSecondary": "#FFFFFF",
            "surface": "#FFFBFE",
            "surfaceContainer": "#F3EDF7",
            "surfaceContainerHigh": "#ECE6F0",
            "surfaceVariant": "#E7E0EC",
            "onSurface": "#1D1B20",
            "onSurfaceVariant": "#49454F",
            "outline": "#79747E",
            "outlineVariant": "#CAC4D0",
            "background": "#FFFBFE",
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
            self._refresh()

    def get_is_dark_theme(self) -> bool:
        return self._is_dark_theme

    def set_is_dark_theme(self, value: bool) -> None:
        if value != self._is_dark_theme:
            self._is_dark_theme = value
            self.themeChanged.emit()

    @Slot(str)
    def setSeedColor(self, value: str) -> None:
        self.set_seed_color(value)

    @Slot(bool)
    def setDarkTheme(self, value: bool) -> None:
        self.set_is_dark_theme(value)

    currentScheme = Property("QVariantMap", get_current_scheme, notify=themeChanged)
    lightScheme = Property("QVariantMap", get_light_scheme, notify=themeChanged)
    darkScheme = Property("QVariantMap", get_dark_scheme, notify=themeChanged)
    seedColor = Property(str, get_seed_color, set_seed_color, notify=themeChanged)
    isDarkTheme = Property(bool, get_is_dark_theme, set_is_dark_theme, notify=themeChanged)
