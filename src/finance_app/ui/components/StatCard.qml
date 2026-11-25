import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../themes"

Rectangle {
    id: root

    required property string title
    required property string value

    property color accentColor: Theme.primary

    implicitWidth: 180
    implicitHeight: 112

    color: Theme.surface
    radius: Theme.radiusLarge

    border.color: Theme.border
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 8

        Rectangle {
            width: 24
            height: 4
            radius: 2
            color: root.accentColor
        }

        Label {
            text: root.value
            color: Theme.textPrimary

            font.family: Theme.fontFamily
            font.pixelSize: 30
            font.bold: true
        }

        Label {
            text: root.title
            color: Theme.textSecondary

            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
        }
    }
}