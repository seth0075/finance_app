import QtQuick
import QtQuick.Controls.Basic

import "../themes"

CheckBox {
    id: control

    implicitWidth: Math.max(36, contentItem.implicitWidth)
    implicitHeight: Math.max(36, contentItem.implicitHeight)
    padding: 0
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBody

    indicator: Rectangle {
        objectName: "checkIndicator"
        width: 22
        height: 22
        x: control.text.length ? 0 : (control.width - width) / 2
        y: (control.height - height) / 2
        radius: width / 2
        color: control.hovered ? Theme.surfaceHover : Theme.inputBackground
        border.width: control.visualFocus ? 2 : 1
        border.color: control.visualFocus ? Theme.primary : control.checked ? Theme.success : Theme.textSecondary

        Text {
            anchors.centerIn: parent
            text: "✓"
            color: Theme.success
            font.pixelSize: 15
            font.bold: true
            visible: control.checked
        }
    }

    contentItem: Text {
        text: control.text
        leftPadding: control.text.length ? 32 : 0
        font: control.font
        color: control.enabled ? Theme.textPrimary : Theme.textMuted
        verticalAlignment: Text.AlignVCenter
    }
}
