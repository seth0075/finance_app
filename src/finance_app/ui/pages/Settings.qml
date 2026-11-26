import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import "../components/google_calendar"
import "../components/plaid"
import "../themes"

Item {
    id: root
    required property QtObject googleViewModel
    property QtObject plaidViewModel
    objectName: "settingsPage"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingPage
        spacing: 20

        Label {
            text: "Settings"
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontTitle
            font.bold: true
        }

        GoogleCalendarSettings { Layout.fillWidth: true; googleViewModel: root.googleViewModel }
        PlaidSettings { objectName: "plaidSettings"; Layout.fillWidth: true; plaidViewModel: root.plaidViewModel }
        Item { Layout.fillHeight: true }
    }
}
