pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "components"
import "pages"

ApplicationWindow {
    id: window

    required property QtObject taskViewModel

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

        Component {
            id: dashboardPage
            Dashboard {}
        }

        Component {
            id: financesPage
            Finances {}
        }

        Component {
            id: wishlistPage
            Wishlist {}
        }

        Component {
            id: tasksPage

            Tasks {
                taskViewModel: window.taskViewModel
            }
        }

        Loader {
             id: pageLoader

            Layout.fillWidth: true
            Layout.fillHeight: true

            sourceComponent: {
                switch (window.currentPage) {
                    case "Dashboard":
                        return dashboardPage
                    case "Finances":
                        return financesPage
                    case "Wishlist":
                        return wishlistPage
                    case "Tasks":
                        return tasksPage
                    default:
                        return null
                }
            }
        }
    }
}