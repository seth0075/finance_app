pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "components"
import "pages"
import "themes"

ApplicationWindow {
    id: window

    required property QtObject taskViewModel
    required property QtObject calendarViewModel
    property QtObject googleViewModel
    property QtObject financeViewModel
    property QtObject plaidViewModel

    visible: true
    width: 1200
    height: 800
    minimumWidth: 1000
    minimumHeight: 720

    title: "Personal Dashboard"
    color: Theme.background
    font.family: Theme.fontFamily

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
            Finances { financeViewModel: window.financeViewModel; plaidViewModel: window.plaidViewModel }
        }

        Component {
            id: wishlistPage
            Wishlist {}
        }

        Component {
            id: calendarPage
            CalendarPage {
                taskViewModel: window.taskViewModel
                calendarViewModel: window.calendarViewModel
                googleViewModel: window.googleViewModel
            }
        }

        Component {
            id: settingsPage
            Settings { googleViewModel: window.googleViewModel; plaidViewModel: window.plaidViewModel }
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
                    case "Calendar":
                        return calendarPage
                    case "Settings":
                        return settingsPage
                    default:
                        return null
                }
            }
        }
    }
}