pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs as QuickDialogs
import QtQuick.Layouts

import ".."
import "../../themes"

Dialog {
    id: root
    objectName: "financeCategoryDialog"
    required property QtObject financeViewModel
    property int selectedCount: 0
    property string period: ""
    readonly property var categoryOptions: financeViewModel
        ? financeViewModel.categoryDetails.concat([{name: "+ New category", color: ""}]) : []
    readonly property bool creating: category.currentIndex === categoryOptions.length - 1
    signal assigned(int count)
    modal: true
    anchors.centerIn: parent
    width: Math.min(800, parent.width - 32)
    height: Math.min(700, parent.height - 32)
    padding: 20
    background: Rectangle { color: Theme.surface; radius: Theme.radiusLarge; border.color: Theme.border }
    Overlay.modal: Rectangle { color: "#99000000" }

    component Field: TextField {
        implicitHeight: 40
        leftPadding: 10
        rightPadding: 10
        color: Theme.textPrimary
        placeholderTextColor: Theme.textMuted
        selectByMouse: true
        background: Rectangle { color: Theme.inputBackground; radius: Theme.radiusSmall; border.color: parent.activeFocus ? Theme.primary : Theme.border }
    }
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
    QuickDialogs.ColorDialog {
        id: picker
        objectName: "financeCategoryColorPicker"
        title: "Choose category color"
        selectedColor: colorInput.acceptableInput ? colorInput.text : "#7395F5"
        onAccepted: {
            const red = Math.round(selectedColor.r * 255).toString(16).padStart(2, "0");
            const green = Math.round(selectedColor.g * 255).toString(16).padStart(2, "0");
            const blue = Math.round(selectedColor.b * 255).toString(16).padStart(2, "0");
            colorInput.text = ("#" + red + green + blue).toUpperCase();
        }
    }
    function openFor(periodLabel, transactions) {
        period = periodLabel;
        rows.clear();
        for (const uncategorized of [true, false]) {
            for (const transaction of transactions) {
                const isUncategorized = !transaction.category || transaction.category.toLowerCase() === "uncategorized";
                if (transaction.kind !== "transfer" && isUncategorized === uncategorized)
                    rows.append({ transactionId: transaction.id, rowDate: transaction.date,
                        title: transaction.title, account: transaction.accountName,
                        amount: transaction.displayAmount, currentCategory: transaction.category,
                        currentColor: transaction.categoryColor, chosen: false });
            }
        }
        selectedCount = 0;
        category.currentIndex = -1;
        nameInput.text = "";
        colorInput.text = "#7395F5";
        error.text = "";
        open();
    }
    function updateCount() {
        let count = 0;
        for (let i = 0; i < rows.count; i++) if (rows.get(i).chosen) count++;
        selectedCount = count;
    }
    function toggleAll() {
        const choose = selectedCount < rows.count;
        for (let i = 0; i < rows.count; i++) rows.setProperty(i, "chosen", choose);
        updateCount();
    }
    function chooseCategory() {
        nameInput.text = "";
        colorInput.text = category.currentIndex >= 0 && !creating
            ? categoryOptions[category.currentIndex].color || "#7395F5" : "#7395F5";
    }
    function saveCategory() {
        if (category.currentIndex < 0) { error.text = "Choose a category."; return; }
        const name = creating ? nameInput.text.trim() : categoryOptions[category.currentIndex].name;
        const message = financeViewModel.saveCategory(name, colorInput.text, creating);
        if (message.length) { error.text = message; return; }
        category.currentIndex = categoryOptions.findIndex(item => item.name === name);
        for (let i = 0; i < rows.count; i++)
            if (rows.get(i).currentCategory === name) rows.setProperty(i, "currentColor", colorInput.text);
        error.text = "";
    }
    function assign() {
        if (category.currentIndex < 0 || creating) { error.text = "Choose a saved category."; return; }
        const savedColor = categoryOptions[category.currentIndex].color || "#7395F5";
        if (colorInput.text.toUpperCase() !== savedColor.toUpperCase()) {
            error.text = "Save the category color before assigning.";
            return;
        }
        const selected = [];
        for (let i = 0; i < rows.count; i++) if (rows.get(i).chosen) selected.push(rows.get(i).transactionId);
        const message = financeViewModel.assignCategory(selected, categoryOptions[category.currentIndex].name);
        if (message.length) error.text = message;
        else { assigned(selected.length); close(); }
    }

    contentItem: ColumnLayout {
        spacing: 8
        Label { text: "Assign categories"; color: Theme.textPrimary; font.pixelSize: Theme.fontSubtitle; font.bold: true }
        Label { text: root.period + " · Select income and expense transactions. Transfers cannot be categorized."; textFormat: Text.PlainText; color: Theme.textSecondary; wrapMode: Text.Wrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            Label { objectName: "financeCategorySelection"; text: root.selectedCount + " of " + rows.count + " selected"; color: Theme.textSecondary; Layout.fillWidth: true }
            Action { objectName: "financeCategorySelectAll"; text: root.selectedCount === rows.count && rows.count > 0 ? "Clear selection" : "Select all"; enabled: rows.count > 0; onClicked: root.toggleAll() }
        }
        Label { visible: rows.count === 0; text: "No income or expense transactions in this period."; color: Theme.textSecondary; Layout.fillWidth: true }
        ListView {
            id: transactionRows
            objectName: "financeCategoryRows"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            model: rows
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                id: row
                required property int index
                required property string transactionId
                required property string rowDate
                required property string title
                required property string account
                required property string amount
                required property string currentCategory
                required property string currentColor
                required property bool chosen
                width: ListView.view.width
                height: 50
                radius: Theme.radiusSmall
                color: Theme.inputBackground
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 12
                    ThemedCheckBox {
                        objectName: "financeCategoryRowCheck" + row.transactionId
                        checked: row.chosen
                        Accessible.name: "Select " + row.title
                        onClicked: { rows.setProperty(row.index, "chosen", checked); root.updateCount(); }
                    }
                    Label { text: row.rowDate; textFormat: Text.PlainText; color: Theme.textSecondary }
                    Rectangle { visible: row.currentColor.length > 0; width: 10; height: 10; radius: 5; color: visible ? row.currentColor : "transparent" }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        spacing: 0
                        Label { text: row.title; textFormat: Text.PlainText; color: Theme.textPrimary; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: row.account + " · " + row.currentCategory; textFormat: Text.PlainText; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                    Label { text: row.amount; textFormat: Text.PlainText; color: Theme.textPrimary }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            ThemedComboBox {
                id: category
                objectName: "financeBulkCategory"
                Layout.fillWidth: true
                model: root.categoryOptions
                textRole: "name"
                displayText: currentIndex < 0 ? "Choose a category" : currentText
                onCurrentIndexChanged: root.chooseCategory()
            }
            Field { id: nameInput; objectName: "financeBulkCategoryName"; visible: root.creating; Layout.fillWidth: true; maximumLength: 100; placeholderText: "New category name" }
        }
        RowLayout {
            Layout.fillWidth: true
            Field {
                id: colorInput
                objectName: "financeCategoryColor"
                Layout.fillWidth: true
                maximumLength: 7
                placeholderText: "#RRGGBB"
                validator: RegularExpressionValidator { regularExpression: /#[0-9a-fA-F]{6}/ }
            }
            Rectangle { width: 28; height: 28; radius: 14; color: colorInput.acceptableInput ? colorInput.text : "transparent"; border.color: Theme.border }
            Action { objectName: "financeChooseCategoryColor"; text: "Choose color"; onClicked: picker.open() }
            Action { objectName: "financeSaveCategory"; text: root.creating ? "Create category" : "Save color"; enabled: category.currentIndex >= 0; onClicked: root.saveCategory() }
        }
        Label { text: "Save the category or color before assigning it. Color changes apply to all transactions in that category."; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall; wrapMode: Text.Wrap; Layout.fillWidth: true }
        Label { id: error; objectName: "financeCategoryError"; visible: text.length > 0; color: Theme.danger; wrapMode: Text.Wrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Action { objectName: "financeCancelCategory"; text: "Cancel"; onClicked: root.close() }
            PrimaryButton { objectName: "financeApplyCategory"; text: "Assign category"; enabled: root.selectedCount > 0 && category.currentIndex >= 0 && !root.creating; onClicked: root.assign() }
        }
    }
}
