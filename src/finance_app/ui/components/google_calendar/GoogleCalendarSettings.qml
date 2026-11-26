import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs as QuickDialogs
import QtQuick.Layouts

import ".."
import "../../themes"

Rectangle {
    id: root
    objectName: "googleCalendarSettings"
    property QtObject googleViewModel
    implicitHeight: content.implicitHeight + 40
    color: Theme.surface
    radius: Theme.radiusLarge
    border.color: Theme.border

    QuickDialogs.FileDialog {
        id: clientPicker
        objectName: "googleClientPicker"
        title: "Choose your Google desktop OAuth client JSON"
        nameFilters: ["JSON files (*.json)"]
        onAccepted: root.googleViewModel.connectAccount(selectedFile)
    }

    component Action: Button {
        id: button
        implicitHeight: 40
        leftPadding: 16
        rightPadding: 16
        opacity: enabled ? 1 : 0.45
        contentItem: Text {
            text: button.text
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: button.hovered ? Theme.surfaceHover : Theme.inputBackground
            radius: Theme.radiusSmall
            border.color: button.visualFocus ? Theme.primary : Theme.border
        }
    }

    Dialog {
        id: confirmDisconnect
        modal: true
        anchors.centerIn: Overlay.overlay
        padding: 20
        background: Rectangle { color: Theme.surface; radius: Theme.radiusLarge; border.color: Theme.border }
        contentItem: ColumnLayout {
            spacing: 16
            Label {
                text: root.googleViewModel && root.googleViewModel.connected ? "Disconnect Google Calendar?" : "Remove cached Google data?"
                color: Theme.textPrimary
                font.bold: true
                font.pixelSize: Theme.fontSubtitle
            }
            Label {
                text: "Cached Google calendars and events will be removed from this app."
                color: Theme.textSecondary
                wrapMode: Text.Wrap
                Layout.maximumWidth: 380
            }
            RowLayout {
                Item { Layout.fillWidth: true }
                Action { objectName: "cancelGoogleDisconnect"; text: "Cancel"; onClicked: confirmDisconnect.close() }
                Action {
                    objectName: "confirmGoogleDisconnect"
                    text: "Disconnect"
                    onClicked: { confirmDisconnect.close(); root.googleViewModel.disconnectAccount(); }
                }
            }
        }
    }

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12
        RowLayout {
            spacing: 10
            Rectangle {
                objectName: "googleCalendarIcon"
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                radius: 5
                color: "#F8F9FA"

                Rectangle {
                    width: parent.width
                    height: 10
                    radius: 5
                    color: "#4285F4"
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 5
                        color: parent.color
                    }
                }
                Text {
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: 2
                    text: "31"
                    color: "#4285F4"
                    font.pixelSize: 14
                    font.bold: true
                }
                Row {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 2
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 2
                    Rectangle { width: 3; height: 3; radius: 1.5; color: "#EA4335" }
                    Rectangle { width: 3; height: 3; radius: 1.5; color: "#FBBC04" }
                    Rectangle { width: 3; height: 3; radius: 1.5; color: "#34A853" }
                }
            }
            Label {
                text: "Google Calendar"
                color: Theme.textPrimary
                font.pixelSize: Theme.fontSubtitle
                font.bold: true
            }
        }
        Label {
            text: "View your Google calendars and events here. Changes must be made in Google Calendar."
            color: Theme.textSecondary
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Label {
            objectName: "googleStatus"
            text: root.googleViewModel ? root.googleViewModel.status : "Google Calendar is unavailable."
            color: Theme.textPrimary
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Label {
            visible: root.googleViewModel !== null && (root.googleViewModel.connected || root.googleViewModel.hasCache)
            text: root.googleViewModel ? root.googleViewModel.cacheCoverage : ""
            color: Theme.textSecondary
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Label {
            visible: root.googleViewModel !== null && !root.googleViewModel.connected
            text: "Create a Google Cloud desktop OAuth client first; see the setup instructions in the README."
            color: Theme.textSecondary
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        RowLayout {
            PrimaryButton {
                objectName: "connectGoogleButton"
                visible: root.googleViewModel !== null && !root.googleViewModel.connected
                enabled: root.googleViewModel !== null && !root.googleViewModel.busy
                text: "Connect Google Calendar"
                onClicked: clientPicker.open()
            }
            Action {
                objectName: "refreshGoogleButton"
                visible: root.googleViewModel !== null && root.googleViewModel.connected
                enabled: root.googleViewModel !== null && !root.googleViewModel.busy
                text: "Refresh"
                onClicked: root.googleViewModel.refresh()
            }
            Action {
                objectName: "disconnectGoogleButton"
                visible: root.googleViewModel !== null && (root.googleViewModel.connected || root.googleViewModel.hasCache)
                enabled: root.googleViewModel !== null && !root.googleViewModel.busy
                text: root.googleViewModel && root.googleViewModel.connected ? "Disconnect" : "Clear cache"
                onClicked: confirmDisconnect.open()
            }
        }
    }
}
