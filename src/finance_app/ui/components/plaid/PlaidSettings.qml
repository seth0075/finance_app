import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import ".."
import "../../themes"

Rectangle {
    id: root
    property QtObject plaidViewModel
    implicitHeight: content.implicitHeight + 40
    color: Theme.surface
    radius: Theme.radiusLarge
    border.color: Theme.border

    component Action: Button {
        id: button
        implicitHeight: 40
        leftPadding: 16
        rightPadding: 16
        opacity: enabled ? 1 : 0.45
        contentItem: Text { text: button.text; color: Theme.textPrimary; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { color: button.hovered ? Theme.surfaceHover : Theme.inputBackground; radius: Theme.radiusSmall; border.color: button.visualFocus ? Theme.primary : Theme.border }
    }
    component Field: TextField {
        implicitHeight: 40
        leftPadding: 10
        color: Theme.textPrimary
        placeholderTextColor: Theme.textMuted
        selectByMouse: true
        background: Rectangle { color: Theme.inputBackground; radius: Theme.radiusSmall; border.color: parent.activeFocus ? Theme.primary : Theme.border }
    }

    Dialog {
        id: credentialsDialog
        objectName: "plaidCredentialsDialog"
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(500, parent.width - 32)
        padding: 20
        background: Rectangle { color: Theme.surface; radius: Theme.radiusLarge; border.color: Theme.border }
        onClosed: { clientId.text = ""; secret.text = ""; }
        contentItem: ColumnLayout {
            spacing: 10
            Label { text: "Connect with Plaid"; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSubtitle }
            Label { text: "Plaid receives account data you authorize. Production use may incur charges. Never enter your bank password here."; color: Theme.textSecondary; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Label { text: "Environment"; color: Theme.textPrimary }
            ThemedComboBox { id: environment; objectName: "plaidEnvironment"; Layout.fillWidth: true; model: ["Sandbox", "Production"] }
            Label { text: "Plaid client ID"; color: Theme.textPrimary }
            Field { id: clientId; objectName: "plaidClientId"; Layout.fillWidth: true }
            Label { text: "Plaid secret for selected environment"; color: Theme.textPrimary }
            Field { id: secret; objectName: "plaidSecret"; Layout.fillWidth: true; echoMode: TextInput.Password }
            Label { text: "Credentials are saved in the system credential store. See the README for setup."; color: Theme.textSecondary; wrapMode: Text.Wrap; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Action { text: "Cancel"; onClicked: credentialsDialog.close() }
                PrimaryButton {
                    objectName: "plaidStartLink"
                    text: "Open Plaid Link"
                    enabled: clientId.text.trim().length > 0 && secret.text.trim().length > 0
                    onClicked: {
                        root.plaidViewModel.link(environment.currentIndex === 0 ? "sandbox" : "production", clientId.text, secret.text);
                        credentialsDialog.close();
                    }
                }
            }
        }
    }
    Dialog {
        id: disconnectDialog
        modal: true
        anchors.centerIn: Overlay.overlay
        padding: 20
        background: Rectangle { color: Theme.surface; radius: Theme.radiusLarge; border.color: Theme.border }
        contentItem: ColumnLayout {
            Label { text: "Disconnect Plaid?"; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSubtitle }
            Label { text: "This removes the Plaid item. Imported transactions remain in the app."; color: Theme.textSecondary; wrapMode: Text.Wrap; Layout.maximumWidth: 380 }
            RowLayout {
                Item { Layout.fillWidth: true }
                Action { text: "Cancel"; onClicked: disconnectDialog.close() }
                Action { objectName: "plaidConfirmDisconnect"; text: "Disconnect"; onClicked: { disconnectDialog.close(); root.plaidViewModel.disconnect(); } }
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
                objectName: "plaidFinanceIcon"
                Layout.preferredWidth: 36
                Layout.preferredHeight: 36
                radius: 5
                color: "#F8F9FA"
                Canvas {
                    anchors.fill: parent
                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.fillStyle = "#22675B";
                        ctx.beginPath();
                        ctx.moveTo(6, 14);
                        ctx.lineTo(18, 7);
                        ctx.lineTo(30, 14);
                        ctx.closePath();
                        ctx.fill();
                        ctx.fillRect(7, 15, 22, 2);
                        for (let x = 9; x <= 25; x += 8)
                            ctx.fillRect(x, 18, 3, 8);
                        ctx.fillRect(6, 27, 24, 2);
                    }
                }
            }
            Label { text: "Plaid bank accounts"; color: Theme.textPrimary; font.pixelSize: Theme.fontSubtitle; font.bold: true }
        }
        Label { text: "Link accounts through Plaid, then review and import transactions on Finances."; color: Theme.textSecondary; wrapMode: Text.Wrap; Layout.fillWidth: true }
        Label { objectName: "plaidStatus"; text: root.plaidViewModel ? root.plaidViewModel.status : "Plaid is unavailable."; textFormat: Text.PlainText; color: Theme.textPrimary; wrapMode: Text.Wrap; Layout.fillWidth: true }
        RowLayout {
            PrimaryButton { objectName: "plaidConnect"; visible: root.plaidViewModel && !root.plaidViewModel.connected && !root.plaidViewModel.linkPending; enabled: root.plaidViewModel && !root.plaidViewModel.busy; text: "Connect Plaid"; onClicked: credentialsDialog.open() }
            Action { objectName: "plaidFinishLink"; visible: root.plaidViewModel && root.plaidViewModel.linkPending; enabled: root.plaidViewModel && !root.plaidViewModel.busy; text: "Finish linking"; onClicked: root.plaidViewModel.finishLink() }
            Action { visible: root.plaidViewModel && root.plaidViewModel.linkPending; enabled: root.plaidViewModel && !root.plaidViewModel.busy; text: "Cancel link"; onClicked: root.plaidViewModel.cancelLink() }
            Action { objectName: "plaidRefresh"; visible: root.plaidViewModel && root.plaidViewModel.connected; enabled: root.plaidViewModel && !root.plaidViewModel.busy; text: "Refresh"; onClicked: root.plaidViewModel.refresh() }
            Action { objectName: "plaidDisconnect"; visible: root.plaidViewModel && root.plaidViewModel.connected; enabled: root.plaidViewModel && !root.plaidViewModel.busy; text: "Disconnect"; onClicked: disconnectDialog.open() }
        }
    }
}
