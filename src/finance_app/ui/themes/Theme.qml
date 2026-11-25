pragma Singleton

import QtQuick

QtObject {
    // Backgrounds
    readonly property color background: "#15171C"
    readonly property color surface: "#20232B"
    readonly property color surfaceHover: "#292D37"
    readonly property color inputBackground: "#191C23"

    // Borders
    readonly property color border: "#303540"

    // Text
    readonly property color textPrimary: "#E8EAF0"
    readonly property color textSecondary: "#949BA8"
    readonly property color textMuted: "#6B7280"

    // Accent colors
    readonly property color primary: "#7395F5"
    readonly property color primaryHover: "#8BA7FF"
    readonly property color success: "#62C6A0"
    readonly property color warning: "#E9B76B"
    readonly property color danger: "#F07878"

    // Typography
    readonly property string fontFamily: "Segoe UI"
    readonly property int fontSmall: 12
    readonly property int fontBody: 14
    readonly property int fontSubtitle: 18
    readonly property int fontTitle: 30

    // Spacing
    readonly property int spacingSmall: 8
    readonly property int spacingMedium: 16
    readonly property int spacingLarge: 24
    readonly property int spacingPage: 32

    // Corner radii
    readonly property int radiusSmall: 6
    readonly property int radiusMedium: 10
    readonly property int radiusLarge: 14
}