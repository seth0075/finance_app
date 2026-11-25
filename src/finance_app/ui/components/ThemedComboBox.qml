import QtQuick
import QtQuick.Controls.Basic

import "../themes"

ComboBox {
    id: control

    implicitHeight: 40
    leftPadding: 12
    rightPadding: 32
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBody

    contentItem: Text {
        text: control.displayText
        color: control.enabled ? Theme.textPrimary : Theme.textMuted
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Text {
        x: control.width - width - 14
        y: (control.height - height) / 2
        text: "▾"
        color: Theme.textSecondary
        font.pixelSize: Theme.fontBody
    }

    background: Rectangle {
        radius: Theme.radiusSmall
        color: control.hovered ? Theme.surfaceHover : Theme.inputBackground
        border.color: control.activeFocus ? Theme.primary : Theme.border
    }

    delegate: ItemDelegate {
        id: option
        objectName: "comboOption"
        required property int index
        required property var modelData

        width: ListView.view.width
        height: 36
        highlighted: control.highlightedIndex === index

        contentItem: Text {
            objectName: "comboOptionText"
            text: control.textRole ? option.modelData[control.textRole] : option.modelData
            color: Theme.textPrimary
            font: control.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            color: option.highlighted || option.hovered ? Theme.surfaceHover : Theme.inputBackground
        }
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 4
        implicitHeight: contentItem.implicitHeight + 8

        contentItem: ListView {
            clip: true
            implicitHeight: Math.min(contentHeight, 240)
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }

        background: Rectangle {
            radius: Theme.radiusSmall
            color: Theme.inputBackground
            border.color: Theme.border
        }
    }
}
