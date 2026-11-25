import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "components"

ApplicationWindow {
    id: window

    visible: true
    width: 1200
    height: 800
    minimumWidth: 800
    minimumHeight: 500

    title: "Personal Dashboard"
    color: "#15171C"

    property string currentPage: "Dashboard"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Sidebar {
            Layout.preferredWidth: 220
            Layout.fillHeight: true

            selectedPage: window.currentPage

            onPageSelected: function(page) {
                window.currentPage = page
            }
        }

        Loader {
            Layout.fillWidth: true
            Layout.fillHeight: true

            source: {
                switch (window.currentPage) {
                    case "Dashboard":
                        return "pages/Dashboard.qml"
                    case "Finances":
                        return "pages/Finances.qml"
                    case "Wishlist":
                        return "pages/Wishlist.qml"
                    case "Tasks":
                        return "pages/Tasks.qml"
                    default:
                        return ""
                }
            }
        }
    }
}