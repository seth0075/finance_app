import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import ".."
import "../../themes"

Dialog {
    id: root
    objectName: "financeTransactionDialog"
    required property QtObject financeViewModel
    property string editingId: ""
    readonly property bool isExpense: kindInput.currentIndex === 1
    readonly property bool isTransfer: kindInput.currentIndex === 2
    readonly property var categoryOptions: financeViewModel ? financeViewModel.categories.concat(["+ New category"]) : ["+ New category"]
    modal: true
    anchors.centerIn: parent
    width: Math.min(500, parent.width - 32)
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

    function openNew(day) {
        editingId = "";
        titleInput.text = "";
        dateInput.text = day;
        kindInput.currentIndex = 1;
        amountInput.text = "";
        accountInput.currentIndex = -1;
        destinationInput.currentIndex = financeViewModel.accounts.length > 1 ? 1 : 0;
        categoryInput.currentIndex = categoryOptions.indexOf("Uncategorized");
        customCategory.text = "";
        repeatInput.currentIndex = 0;
        activeInput.checked = true;
        error.text = "";
        open();
    }
    function openEdit(transaction) {
        editingId = transaction.id;
        titleInput.text = transaction.title;
        dateInput.text = transaction.date;
        kindInput.currentIndex = ["income", "expense", "transfer"].indexOf(transaction.kind);
        amountInput.text = transaction.amount;
        accountInput.currentIndex = financeViewModel.accounts.findIndex(account => account.id === transaction.accountId);
        destinationInput.currentIndex = financeViewModel.accounts.findIndex(account => account.id === transaction.destinationId);
        categoryInput.currentIndex = categoryOptions.indexOf(transaction.category);
        customCategory.text = "";
        repeatInput.currentIndex = ["none", "monthly", "yearly"].indexOf(transaction.recurrence);
        activeInput.checked = transaction.recurrence === "none" || transaction.subscriptionActive;
        error.text = "";
        open();
    }
    function save() {
        const accounts = financeViewModel.accounts;
        const category = categoryInput.currentIndex === categoryOptions.length - 1
            ? customCategory.text : (categoryInput.currentIndex >= 0 ? categoryOptions[categoryInput.currentIndex] : "");
        const message = financeViewModel.saveTransaction(editingId, dateInput.text, titleInput.text,
            ["income", "expense", "transfer"][kindInput.currentIndex], amountInput.text,
            accountInput.currentIndex >= 0 ? accounts[accountInput.currentIndex].id : "",
            destinationInput.currentIndex >= 0 ? accounts[destinationInput.currentIndex].id : "",
            category, isExpense ? ["none", "monthly", "yearly"][repeatInput.currentIndex] : "none",
            activeInput.checked);
        if (message.length) error.text = message;
        else close();
    }

    contentItem: ColumnLayout {
        spacing: 7
        Label { text: root.editingId ? "Edit transaction" : "New transaction"; color: Theme.textPrimary; font.pixelSize: Theme.fontSubtitle; font.bold: true; Layout.bottomMargin: 6 }
        Caption { text: "Description" }
        Field { id: titleInput; objectName: "financeTransactionTitle"; Layout.fillWidth: true; maximumLength: 200; placeholderText: "Description" }
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "Date" }
                Field { id: dateInput; objectName: "financeTransactionDate"; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "Type" }
                ThemedComboBox { id: kindInput; objectName: "financeTransactionKind"; Layout.fillWidth: true; model: ["Income", "Expense", "Transfer"] }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "Amount (USD)" }
                Field { id: amountInput; objectName: "financeTransactionAmount"; Layout.fillWidth: true; placeholderText: "0.00" }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: root.isTransfer ? "From account" : "Account" }
                ThemedComboBox { id: accountInput; objectName: "financeTransactionAccount"; Layout.fillWidth: true; model: root.financeViewModel ? root.financeViewModel.accounts : []; textRole: "name"; displayText: currentIndex < 0 ? "Choose an account" : currentText }
            }
        }
        Caption { visible: root.isTransfer; text: "To account" }
        ThemedComboBox { id: destinationInput; objectName: "financeTransactionDestination"; visible: root.isTransfer; Layout.fillWidth: true; model: root.financeViewModel ? root.financeViewModel.accounts : []; textRole: "name" }
        Caption { visible: !root.isTransfer; text: "Category" }
        ThemedComboBox { id: categoryInput; objectName: "financeTransactionCategory"; visible: !root.isTransfer; Layout.fillWidth: true; model: root.categoryOptions }
        Field { id: customCategory; objectName: "financeCustomCategory"; visible: !root.isTransfer && categoryInput.currentIndex === root.categoryOptions.length - 1; Layout.fillWidth: true; maximumLength: 100; placeholderText: "New category name" }
        RowLayout {
            visible: root.isExpense
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "Subscription" }
                ThemedComboBox { id: repeatInput; objectName: "financeTransactionRepeat"; Layout.fillWidth: true; model: ["None", "Monthly", "Yearly"] }
            }
            ThemedCheckBox {
                id: activeInput
                objectName: "financeSubscriptionActive"
                visible: repeatInput.currentIndex > 0
                text: "Active"
                Layout.alignment: Qt.AlignBottom
            }
        }
        Label { id: error; objectName: "financeTransactionError"; visible: text.length > 0; color: Theme.danger; wrapMode: Text.Wrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 8
            Action { objectName: "financeDeleteTransaction"; visible: root.editingId.length > 0; text: "Delete"; onClicked: confirmDelete.open() }
            Item { Layout.fillWidth: true }
            Action { text: "Cancel"; onClicked: root.close() }
            PrimaryButton { objectName: "financeSaveTransaction"; text: "Save"; onClicked: root.save() }
        }
    }
    Dialog {
        id: confirmDelete
        objectName: "financeConfirmDeleteTransaction"
        modal: true
        anchors.centerIn: parent
        title: "Delete this transaction and its subscription?"
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: {
            const message = root.financeViewModel.deleteTransaction(root.editingId);
            if (message.length) error.text = message;
            else root.close();
        }
    }
}
