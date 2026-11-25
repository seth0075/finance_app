import QtQuick
import QtQuick.Controls.Basic

import "../themes"

Button {
    id: control

    implicitHeight: 44
    implicitWidth: Math.max(110, contentItem.implicitWidth + leftPadding + rightPadding)

    leftPadding: 20
    rightPadding: 20

    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBody
    font.bold: true

    opacity: enabled ? 1.0 : 0.45

    contentItem: Text {
        text: control.text
        font: control.font

        color: "#FFFFFF"

        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: Theme.radiusMedium

        color: control.down
            ? Qt.darker(Theme.primary, 1.15)
            : control.hovered
                ? Theme.primaryHover
                : Theme.primary

        border.width: control.activeFocus ? 2 : 0
        border.color: Theme.textPrimary

        Behavior on color {
            ColorAnimation {
                duration: 120
            }
        }
    }
}