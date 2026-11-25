pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import "../themes"

Rectangle {
    id: sidebar

    property string selectedPage: "Dashboard"

    signal pageSelected(string page)

    implicitWidth: 220
    color: Theme.surface

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8

        Label {
            text: "Personal Dashboard"
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSubtitle
            font.bold: true
            Layout.bottomMargin: 20
        }

        Repeater {
            model: [
                "Dashboard",
                "Finances",
                "Wishlist",
                "Tasks",
                "Calendar",
                "Notes",
                "Settings"
            ]

            delegate: Button {
                id: pageButton
                required property string modelData
                objectName: "navigation" + modelData

                text: modelData
                Layout.fillWidth: true
                implicitHeight: 48
                checkable: true
                checked: sidebar.selectedPage === modelData
                leftPadding: 16
                rightPadding: 16
                font.family: Theme.fontFamily
                font.pixelSize: 16
                font.bold: checked

                onClicked: {
                    sidebar.pageSelected(modelData)
                }

                contentItem: Text {
                    text: pageButton.text
                    font: pageButton.font
                    color: pageButton.checked ? Theme.textPrimary : Theme.textSecondary
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                background: Rectangle {
                    radius: Theme.radiusSmall
                    color: pageButton.checked ? Theme.surfaceHover : pageButton.hovered ? Theme.inputBackground : "transparent"
                    border.width: pageButton.visualFocus ? 1 : 0
                    border.color: Theme.primary

                    Rectangle {
                        visible: pageButton.checked
                        width: 3
                        height: parent.height - 18
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        radius: 2
                        color: Theme.primary
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}