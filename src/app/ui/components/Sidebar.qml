pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: sidebar

    property string selectedPage: "Dashboard"

    signal pageSelected(string page)

    implicitWidth: 220
    color: "#20232A"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8

        Label {
            text: "Personal Dashboard"
            color: "white"
            font.pixelSize: 18
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
                required property string modelData

                text: modelData
                Layout.fillWidth: true
                checkable: true
                checked: sidebar.selectedPage === modelData

                onClicked: {
                    sidebar.pageSelected(modelData)
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}