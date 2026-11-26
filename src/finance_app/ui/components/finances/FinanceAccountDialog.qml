import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import ".."
import "../../themes"

Dialog {
    id: root
    objectName: "financeAccountDialog"
    required property QtObject financeViewModel
    property string editingId: ""
    property bool plaidImport: false
    property var plaidAccount: null
    signal accountCreated(string accountId)
    modal: true
    anchors.centerIn: parent
    width: Math.min(470, parent.width - 32)
    padding: 24
    Overlay.modal: Rectangle { color: "#99000000" }
    background: Rectangle { color: Theme.surface; radius: Theme.radiusLarge; border.color: Theme.border }

    component Field: TextField {
        implicitHeight: 40
        leftPadding: 10
        rightPadding: 10
        color: Theme.textPrimary
        placeholderTextColor: Theme.textMuted
        selectByMouse: true
        background: Rectangle { color: Theme.inputBackground; radius: Theme.radiusSmall; border.color: parent.activeFocus ? Theme.primary : Theme.border }
    }
    component Caption: Label { color: Theme.textPrimary; font.pixelSize: Theme.fontSmall; font.bold: true }
    component Action: Button {
        id: button
        implicitHeight: 40
        leftPadding: 14
        rightPadding: 14
        contentItem: Text { text: button.text; color: Theme.textPrimary; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { color: button.hovered ? Theme.surfaceHover : Theme.inputBackground; radius: Theme.radiusSmall; border.color: button.visualFocus ? Theme.primary : Theme.border }
    }

    function openNew(day, name, kind, account) {
        editingId = "";
        plaidAccount = account || null;
        nameInput.text = name || "";
        kindInput.currentIndex = kind === "credit" ? 1 : 0;
        openingDate.text = day;
        openingAmount.text = plaidImport ? "" : "0.00";
        creditLimit.text = plaidAccount ? plaidAccount.creditLimitAmount : "";
        error.text = "";
        open();
    }
    function openEdit(account) {
        editingId = account.id;
        nameInput.text = account.name;
        kindInput.currentIndex = account.kind === "credit" ? 1 : 0;
        openingDate.text = account.openedOn;
        openingAmount.text = account.openingAmount;
        creditLimit.text = account.creditLimit;
        error.text = "";
        open();
    }
    function save() {
        const existingIds = editingId ? [] : financeViewModel.accounts.map(account => account.id);
        const message = financeViewModel.saveAccount(editingId, nameInput.text,
            kindInput.currentIndex === 0 ? "bank" : "credit", openingDate.text,
            openingAmount.text, creditLimit.text);
        if (message.length) error.text = message;
        else {
            if (!editingId) {
                const created = financeViewModel.accounts.find(account => !existingIds.includes(account.id));
                accountCreated(created.id);
            }
            close();
        }
    }

    contentItem: ColumnLayout {
        spacing: 8
        Label { text: root.editingId ? "Edit account" : "New account"; color: Theme.textPrimary; font.pixelSize: Theme.fontSubtitle; font.bold: true; Layout.bottomMargin: 8 }
        Caption { text: "Account name" }
        Field { id: nameInput; objectName: "financeAccountName"; Layout.fillWidth: true; maximumLength: 100; placeholderText: "Checking, savings, credit card..." }
        Caption { text: "Account type" }
        ThemedComboBox { id: kindInput; objectName: "financeAccountKind"; Layout.fillWidth: true; model: ["Bank / cash", "Credit card"] }
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "Opening date" }
                Field { id: openingDate; objectName: "financeAccountDate"; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: kindInput.currentIndex === 1 ? "Opening amount owed" : "Opening balance" }
                Field { id: openingAmount; objectName: "financeOpeningAmount"; Layout.fillWidth: true; placeholderText: "0.00" }
            }
        }
        Caption { visible: kindInput.currentIndex === 1; text: "Credit limit" }
        Field { id: creditLimit; objectName: "financeCreditLimit"; visible: kindInput.currentIndex === 1; Layout.fillWidth: true; placeholderText: "0.00" }
        Label {
            objectName: "financePlaidBalance"
            visible: root.plaidImport && root.plaidAccount !== null
            text: root.plaidAccount ? "Plaid current balance: " + root.plaidAccount.balance + " (may be cached)" : ""
            textFormat: Text.PlainText
            color: Theme.textSecondary
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Label {
            objectName: "financePlaidCreditLimit"
            visible: root.plaidImport && root.plaidAccount !== null && root.plaidAccount.kind === "credit"
            text: root.plaidAccount ? "Plaid credit limit: " + root.plaidAccount.creditLimit : ""
            textFormat: Text.PlainText
            color: Theme.textSecondary
            Layout.fillWidth: true
        }
        Action {
            objectName: "financeUsePlaidSnapshot"
            visible: root.plaidImport && root.plaidAccount !== null
            enabled: root.plaidAccount !== null && root.plaidAccount.balanceAmount !== ""
                && (kindInput.currentIndex === 1 ? "credit" : "bank") === root.plaidAccount.kind
            opacity: enabled ? 1 : 0.45
            text: "Use current balance as tomorrow's opening"
            onClicked: {
                const tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                openingDate.text = Qt.formatDate(tomorrow, "yyyy-MM-dd");
                openingAmount.text = root.plaidAccount.balanceAmount;
            }
        }
        Label {
            text: "Opening balance is the balance at the start of the opening date. Earlier transactions reconstruct earlier balances. Credit-card balances represent amounts owed."
                + (root.plaidImport ? " Using Plaid's current balance as tomorrow's opening is an approximation: it may be cached or include pending activity. Earlier transactions reconstruct history; later transactions change the balance. Without earlier transactions, the account appears not open until tomorrow. Saving creates the account even if you cancel the import." : "")
            color: Theme.textSecondary
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
        Label { id: error; objectName: "financeAccountError"; visible: text.length > 0; color: Theme.danger; wrapMode: Text.Wrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 8
            Action { objectName: "financeDeleteAccount"; visible: root.editingId.length > 0; text: "Delete"; onClicked: confirmDelete.open() }
            Item { Layout.fillWidth: true }
            Action { objectName: "financeCancelAccount"; text: "Cancel"; onClicked: root.close() }
            PrimaryButton { objectName: "financeSaveAccount"; text: "Save"; onClicked: root.save() }
        }
    }
    Dialog {
        id: confirmDelete
        modal: true
        anchors.centerIn: parent
        title: "Delete this account?"
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: {
            const message = root.financeViewModel.deleteAccount(root.editingId);
            if (message.length) error.text = message;
            else root.close();
        }
    }
}
