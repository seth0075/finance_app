pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs as QuickDialogs
import QtQuick.Layouts

import ".."
import "../../themes"

Dialog {
    id: root
    objectName: "financeCsvDialog"
    required property QtObject financeViewModel
    property url fileUrl: ""
    property var headers: []
    property bool reviewing: false
    property int selectedCount: 0
    property int validCount: 0
    property string errorText: ""
    signal imported(int count)
    readonly property var columnOptions: ["Choose column"].concat(headers)
    modal: true
    anchors.centerIn: parent
    width: Math.min(800, parent.width - 32)
    height: Math.min(700, parent.height - 32)
    padding: 20
    Overlay.modal: Rectangle { color: "#99000000" }
    background: Rectangle { color: Theme.surface; radius: Theme.radiusLarge; border.color: Theme.border }

    component Caption: Label { color: Theme.textPrimary; font.pixelSize: Theme.fontSmall; font.bold: true }
    component Field: TextField {
        implicitHeight: 40
        leftPadding: 10
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
        contentItem: Text { text: button.text; color: Theme.textPrimary; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { color: button.hovered ? Theme.surfaceHover : Theme.inputBackground; radius: Theme.radiusSmall; border.color: button.visualFocus ? Theme.primary : Theme.border }
    }

    ListModel { id: previewModel }
    QuickDialogs.FileDialog {
        id: picker
        title: "Choose a CSV file"
        nameFilters: ["CSV files (*.csv)", "All files (*)"]
        onAccepted: root.loadFile(selectedFile)
    }

    function openImport() {
        fileUrl = "";
        headers = [];
        reviewing = false;
        selectedCount = 0;
        validCount = 0;
        errorText = "";
        fileInfo.text = "No file loaded";
        previewModel.clear();
        delimiter.currentIndex = 0;
        account.currentIndex = -1;
        open();
    }
    function loadFile(url) {
        fileUrl = url;
        headers = [];
        previewModel.clear();
        reviewing = false;
        errorText = "";
        fileInfo.text = "No file loaded";
        const result = financeViewModel.loadCsv(url, ["comma", "semicolon", "tab"][delimiter.currentIndex]);
        if (result.error) {
            errorText = result.error;
            return;
        }
        headers = result.headers;
        const s = result.suggestions;
        dateColumn.currentIndex = s.date + 1;
        descriptionColumn.currentIndex = s.description + 1;
        amountColumn.currentIndex = s.amount + 1;
        typeColumn.currentIndex = s.type + 1;
        categoryColumn.currentIndex = s.category + 1;
        debitColumn.currentIndex = s.debitAmount + 1;
        creditColumn.currentIndex = s.creditAmount + 1;
        dateFormat.currentIndex = ["iso", "us4", "us2", "eu4"].indexOf(s.dateFormat);
        direction.currentIndex = ["signed", "reverse", "type", "columns"].indexOf(s.direction);
        debitText.text = "Debit";
        creditText.text = "Credit";
        fileInfo.text = result.rowCount + " rows loaded";
    }
    function preview() {
        const accounts = financeViewModel.accounts;
        const result = financeViewModel.previewCsv({
            accountId: account.currentIndex >= 0 ? accounts[account.currentIndex].id : "",
            date: dateColumn.currentIndex - 1, description: descriptionColumn.currentIndex - 1,
            amount: amountColumn.currentIndex - 1, type: typeColumn.currentIndex - 1,
            debitAmount: debitColumn.currentIndex - 1, creditAmount: creditColumn.currentIndex - 1,
            category: categoryColumn.currentIndex - 1,
            dateFormat: ["iso", "us4", "us2", "eu4"][dateFormat.currentIndex],
            direction: ["signed", "reverse", "type", "columns"][direction.currentIndex],
            debitText: debitText.text, creditText: creditText.text
        });
        errorText = result.error;
        if (result.error) return;
        previewModel.clear();
        validCount = 0;
        for (const row of result.rows) {
            previewModel.append({ line: row.line, rowDate: row.date, title: row.title,
                amount: row.amount, kind: row.kind, category: row.category,
                valid: row.valid, chosen: row.selected, status: row.status });
            if (row.valid) validCount++;
        }
        updateCount();
        reviewing = true;
    }
    function updateCount() {
        let count = 0;
        for (let i = 0; i < previewModel.count; i++) {
            if (previewModel.get(i).chosen) count++;
        }
        selectedCount = count;
    }
    function save() {
        const selected = [];
        for (let i = 0; i < previewModel.count; i++) {
            if (previewModel.get(i).chosen) selected.push(i);
        }
        const result = financeViewModel.importCsv(selected);
        errorText = result.error;
        if (!result.error) {
            imported(result.imported);
            close();
        }
    }
    function toggleAll() {
        const choose = selectedCount < validCount;
        for (let i = 0; i < previewModel.count; i++) {
            if (previewModel.get(i).valid) previewModel.setProperty(i, "chosen", choose);
        }
        updateCount();
    }

    contentItem: ColumnLayout {
        spacing: 10
        Label { text: root.reviewing ? "Review CSV transactions" : "Import transactions"; color: Theme.textPrimary; font.pixelSize: Theme.fontSubtitle; font.bold: true }
        Label {
            Layout.fillWidth: true
            text: root.reviewing
                ? "Import into " + account.currentText + ". Possible duplicates are initially unchecked; Select all valid includes them. Invalid rows cannot be selected."
                : "Choose a local CSV and map its columns. Opening balances and dates are not changed; balance and account-number columns are not imported. Transfers are not inferred."
            textFormat: Text.PlainText
            color: Theme.textSecondary
            wrapMode: Text.Wrap
        }
        ScrollView {
            id: mappingScroll
            visible: !root.reviewing
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                width: mappingScroll.availableWidth
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Action { objectName: "financeCsvChoose"; text: "Choose CSV"; onClicked: picker.open() }
                    Label { id: fileInfo; objectName: "financeCsvFileInfo"; text: root.headers.length ? "" : "No file loaded"; color: Theme.textSecondary; Layout.fillWidth: true; elide: Text.ElideRight }
                    ColumnLayout {
                        Caption { text: "Delimiter" }
                        ThemedComboBox { id: delimiter; objectName: "financeCsvDelimiter"; model: ["Comma", "Semicolon", "Tab"]; onActivated: { if (root.fileUrl.toString().length) root.loadFile(root.fileUrl); } }
                    }
                }
                Caption { text: "Import into account" }
                ThemedComboBox { id: account; objectName: "financeCsvAccount"; Layout.fillWidth: true; model: root.financeViewModel ? root.financeViewModel.accounts : []; textRole: "name"; displayText: currentIndex < 0 ? "Choose an account" : currentText }
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Date column" } ThemedComboBox { id: dateColumn; objectName: "financeCsvDate"; Layout.fillWidth: true; model: root.columnOptions } }
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Description column" } ThemedComboBox { id: descriptionColumn; objectName: "financeCsvDescription"; Layout.fillWidth: true; model: root.columnOptions } }
                }
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Date format" } ThemedComboBox { id: dateFormat; objectName: "financeCsvDateFormat"; Layout.fillWidth: true; model: ["YYYY-MM-DD", "MM/DD/YYYY", "MM/DD/YY", "DD/MM/YYYY"] } }
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Direction" } ThemedComboBox { id: direction; objectName: "financeCsvDirection"; Layout.fillWidth: true; model: ["+ income / − expense", "+ expense / − income", "Type column", "Separate debit / credit columns"] } }
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: direction.currentIndex !== 3
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Amount column" } ThemedComboBox { id: amountColumn; objectName: "financeCsvAmount"; Layout.fillWidth: true; model: root.columnOptions } }
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: direction.currentIndex === 3
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Debit amount column" } ThemedComboBox { id: debitColumn; objectName: "financeCsvDebitColumn"; Layout.fillWidth: true; model: root.columnOptions } }
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Credit amount column" } ThemedComboBox { id: creditColumn; objectName: "financeCsvCreditColumn"; Layout.fillWidth: true; model: root.columnOptions } }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Caption { text: "Category column (optional)" }
                    ThemedComboBox { id: categoryColumn; objectName: "financeCsvCategory"; Layout.fillWidth: true; model: root.columnOptions }
                }
                RowLayout {
                    visible: direction.currentIndex === 2
                    Layout.fillWidth: true
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Type column" } ThemedComboBox { id: typeColumn; objectName: "financeCsvType"; Layout.fillWidth: true; model: root.columnOptions } }
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Expense value" } Field { id: debitText; objectName: "financeCsvDebitText"; Layout.fillWidth: true; text: "Debit" } }
                    ColumnLayout { Layout.fillWidth: true; Caption { text: "Income value" } Field { id: creditText; objectName: "financeCsvCreditText"; Layout.fillWidth: true; text: "Credit" } }
                }
                Label {
                    visible: direction.currentIndex === 2 || direction.currentIndex === 3
                    text: "Amount signs are ignored; the type or debit/credit column determines direction."
                    color: Theme.textSecondary
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
                Item { Layout.fillHeight: true }
            }
        }
        ListView {
            id: rowList
            objectName: "financeCsvRows"
            visible: root.reviewing
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: previewModel
            clip: true
            spacing: 4
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                id: row
                required property int index
                required property int line
                required property string rowDate
                required property string title
                required property string amount
                required property string kind
                required property string category
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
                        objectName: "financeCsvRowCheck"
                        checked: row.chosen
                        enabled: row.valid
                        onClicked: { previewModel.setProperty(row.index, "chosen", checked); root.updateCount(); }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "#" + row.line; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall }
                            Label { text: row.rowDate; textFormat: Text.PlainText; color: Theme.textSecondary }
                            Label { text: row.title; textFormat: Text.PlainText; color: Theme.textPrimary; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                            Label { text: row.kind; textFormat: Text.PlainText; color: Theme.textSecondary }
                            Label { text: row.amount; textFormat: Text.PlainText; color: Theme.textPrimary }
                        }
                        Label { visible: row.status.length > 0; text: row.status; textFormat: Text.PlainText; color: row.valid ? Theme.warning : Theme.danger; font.pixelSize: Theme.fontSmall; Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.Wrap }
                        Label { visible: row.category.length > 0; text: row.category; textFormat: Text.PlainText; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                }
            }
        }
        RowLayout {
            visible: root.reviewing
            Layout.fillWidth: true
            Label { objectName: "financeCsvSelection"; text: root.selectedCount + " of " + previewModel.count + " rows selected"; color: Theme.textSecondary; Layout.fillWidth: true }
            Action {
                objectName: "financeCsvSelectAll"
                text: root.selectedCount === root.validCount && root.validCount > 0 ? "Clear selection" : "Select all valid"
                enabled: root.validCount > 0
                onClicked: root.toggleAll()
            }
        }
        Label { visible: root.errorText.length > 0; objectName: "financeCsvError"; text: root.errorText; textFormat: Text.PlainText; color: Theme.danger; wrapMode: Text.Wrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Action { visible: root.reviewing; text: "Back"; onClicked: { root.reviewing = false; root.errorText = ""; } }
            Action { text: "Cancel"; onClicked: root.close() }
            PrimaryButton { objectName: "financeCsvPreview"; visible: !root.reviewing; text: "Preview"; onClicked: root.preview() }
            PrimaryButton { objectName: "financeCsvImport"; visible: root.reviewing; enabled: root.selectedCount > 0; text: "Import selected"; onClicked: root.save() }
        }
    }
}
