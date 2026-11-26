pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import ".."
import "../finances"
import "../../themes"

Dialog {
    id: root
    objectName: "plaidImportDialog"
    property QtObject plaidViewModel
    property QtObject financeViewModel
    property bool reviewing: false
    property int selectedCount: 0
    property int validCount: 0
    property string errorText: ""
    signal imported(int count)
    modal: true
    anchors.centerIn: parent
    width: Math.min(800, parent.width - 32)
    height: Math.min(700, parent.height - 32)
    padding: 20
    background: Rectangle { color: Theme.surface; radius: Theme.radiusLarge; border.color: Theme.border }
    Overlay.modal: Rectangle { color: "#99000000" }

    component Action: Button {
        id: button
        implicitHeight: 40
        leftPadding: 14
        rightPadding: 14
        opacity: enabled ? 1 : 0.45
        contentItem: Text { text: button.text; color: Theme.textPrimary; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { color: button.hovered ? Theme.surfaceHover : Theme.inputBackground; radius: Theme.radiusSmall; border.color: button.visualFocus ? Theme.primary : Theme.border }
    }
    ListModel { id: rows }
    FinanceAccountDialog {
        id: newAccount
        financeViewModel: root.financeViewModel
        plaidImport: true
        onAccountCreated: accountId => {
            local.currentIndex = root.financeViewModel.accounts.findIndex(account => account.id === accountId);
        }
    }
    function openImport() {
        reviewing = false;
        errorText = "";
        remote.currentIndex = -1;
        local.currentIndex = -1;
        rows.clear();
        open();
    }
    function preview() {
        const remoteAccounts = plaidViewModel.accounts;
        const localAccounts = financeViewModel.accounts;
        const result = plaidViewModel.preview(
            remote.currentIndex >= 0 ? remoteAccounts[remote.currentIndex].id : "",
            local.currentIndex >= 0 ? localAccounts[local.currentIndex].id : "");
        errorText = result.error;
        if (result.error) return;
        rows.clear();
        validCount = 0;
        for (const row of result.rows) {
            rows.append({ rowDate: row.date, title: row.title, amount: row.amount, kind: row.kind,
                valid: row.valid, chosen: row.selected, status: row.status });
            if (row.valid) validCount++;
        }
        updateCount();
        reviewing = true;
    }
    function updateCount() {
        let count = 0;
        for (let i = 0; i < rows.count; i++) if (rows.get(i).chosen) count++;
        selectedCount = count;
    }
    function toggleAll() {
        const choose = selectedCount < validCount;
        for (let i = 0; i < rows.count; i++) if (rows.get(i).valid) rows.setProperty(i, "chosen", choose);
        updateCount();
    }
    function save() {
        const selected = [];
        for (let i = 0; i < rows.count; i++) if (rows.get(i).chosen) selected.push(i);
        const result = plaidViewModel.importSelected(selected);
        errorText = result.error;
        if (!result.error) { imported(result.imported); close(); }
    }
    contentItem: ColumnLayout {
        spacing: 10
        Label { text: root.reviewing ? "Review Plaid transactions" : "Import from Plaid"; color: Theme.textPrimary; font.pixelSize: Theme.fontSubtitle; font.bold: true }
        Label {
            Layout.fillWidth: true
            text: root.reviewing
                ? "Possible duplicates are initially unchecked. Select all valid includes them. Pending, previously imported, and invalid transactions cannot be selected."
                : "Choose a linked account and its matching local account. Opening balances are not changed. Imported transactions are snapshots; transfers are not inferred."
            color: Theme.textSecondary
            wrapMode: Text.Wrap
        }
        ColumnLayout {
            visible: !root.reviewing
            Layout.fillWidth: true
            Label { text: "Linked account"; color: Theme.textPrimary; font.bold: true }
            ThemedComboBox { id: remote; objectName: "plaidRemoteAccount"; Layout.fillWidth: true; model: root.plaidViewModel ? root.plaidViewModel.accounts : []; textRole: "displayName"; displayText: currentIndex < 0 ? "Choose a linked account" : currentText }
            Label { text: "Import into local account"; color: Theme.textPrimary; font.bold: true }
            ThemedComboBox { id: local; objectName: "plaidLocalAccount"; Layout.fillWidth: true; model: root.financeViewModel ? root.financeViewModel.accounts : []; textRole: "name"; displayText: currentIndex < 0 ? "Choose a local account" : currentText }
            Action {
                objectName: "plaidNewAccount"
                text: "+ New local account"
                enabled: remote.currentIndex >= 0
                onClicked: {
                    const account = root.plaidViewModel.accounts[remote.currentIndex];
                    newAccount.openNew(Qt.formatDate(new Date(), "yyyy-MM-dd"), account.displayName, account.kind, account);
                }
            }
            Label { objectName: "plaidAccountHelp"; text: "Choose a linked account first, then select or create a matching local account. Review its opening balance to avoid double counting."; color: Theme.textSecondary; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
        Item { visible: !root.reviewing; Layout.fillHeight: true }
        Label {
            objectName: "plaidEmptyHistory"
            visible: root.reviewing && rows.count === 0
            text: "Plaid returned no transactions for this account. Close this dialog and refresh on Finances; history may still be loading."
            color: Theme.textSecondary
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        ListView {
            id: rowList
            objectName: "plaidImportRows"
            visible: root.reviewing
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: rows
            clip: true
            spacing: 4
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                id: row
                required property int index
                required property string rowDate
                required property string title
                required property string amount
                required property string kind
                required property bool valid
                required property bool chosen
                required property string status
                width: ListView.view.width
                height: Math.max(50, rowContent.implicitHeight + 12)
                radius: Theme.radiusSmall
                color: Theme.inputBackground
                RowLayout {
                    id: rowContent
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    ThemedCheckBox {
                        objectName: "plaidImportRowCheck"
                        checked: row.chosen
                        enabled: row.valid
                        onClicked: { rows.setProperty(row.index, "chosen", checked); root.updateCount(); }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: row.rowDate; textFormat: Text.PlainText; color: Theme.textSecondary }
                            Label { text: row.title; textFormat: Text.PlainText; color: Theme.textPrimary; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                            Label { text: row.kind; color: Theme.textSecondary }
                            Label { text: row.amount; textFormat: Text.PlainText; color: Theme.textPrimary }
                        }
                        Label { visible: row.status.length > 0; text: row.status; textFormat: Text.PlainText; color: row.valid ? Theme.warning : Theme.danger; font.pixelSize: Theme.fontSmall; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    }
                }
            }
        }
        RowLayout {
            visible: root.reviewing
            Layout.fillWidth: true
            Label { objectName: "plaidImportSelection"; text: root.selectedCount + " of " + rows.count + " rows selected"; color: Theme.textSecondary; Layout.fillWidth: true }
            Action { objectName: "plaidSelectAll"; text: root.selectedCount === root.validCount && root.validCount > 0 ? "Clear selection" : "Select all valid"; enabled: root.validCount > 0; onClicked: root.toggleAll() }
        }
        Label { objectName: "plaidImportError"; visible: root.errorText.length > 0; text: root.errorText; textFormat: Text.PlainText; color: Theme.danger; wrapMode: Text.Wrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Action { visible: root.reviewing; text: "Back"; onClicked: { root.reviewing = false; root.errorText = ""; } }
            Action { text: "Cancel"; onClicked: root.close() }
            PrimaryButton { objectName: "plaidPreview"; visible: !root.reviewing; text: "Preview"; onClicked: root.preview() }
            PrimaryButton { objectName: "plaidImport"; visible: root.reviewing; enabled: root.selectedCount > 0; text: "Import selected"; onClicked: root.save() }
        }
    }
}
