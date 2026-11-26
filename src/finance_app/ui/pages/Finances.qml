pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import "../components"
import "../components/finances"
import "../components/plaid"
import "../themes"

Item {
    id: root
    objectName: "financesPage"
    required property QtObject financeViewModel
    property QtObject plaidViewModel
    property date selectedDate: new Date()
    property string viewMode: "Month"
    property string importMessage: ""
    property string todayKey: Qt.formatDate(new Date(), "yyyy-MM-dd")
    readonly property string selectedKey: Qt.formatDate(selectedDate, "yyyy-MM-dd")
    readonly property var summary: {
        if (!financeViewModel) return null;
        const accounts = financeViewModel.accounts;
        const transactions = financeViewModel.transactions;
        const today = root.todayKey;
        return financeViewModel.summaryFor(viewMode, selectedKey);
    }
    readonly property var subscriptions: financeViewModel
        ? financeViewModel.transactions.filter(item => item.recurrence !== "none") : []

    function nextDateCheckInterval() {
        const now = new Date();
        const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
        return Math.max(100, Math.min(60000, tomorrow.getTime() - now.getTime() + 50));
    }

    Timer {
        id: dateCheck
        interval: root.nextDateCheckInterval()
        repeat: true
        running: true
        onTriggered: {
            root.todayKey = Qt.formatDate(new Date(), "yyyy-MM-dd");
            dateCheck.interval = root.nextDateCheckInterval();
        }
    }

    function navigate(amount) {
        const day = selectedDate;
        if (viewMode === "Day") {
            selectedDate = new Date(day.getFullYear(), day.getMonth(), day.getDate() + amount, 12);
        } else {
            const months = viewMode === "Month" ? amount : amount * 12;
            const first = new Date(day.getFullYear(), day.getMonth() + months, 1, 12);
            const last = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
            selectedDate = new Date(first.getFullYear(), first.getMonth(), Math.min(day.getDate(), last), 12);
        }
    }

    component Action: Button {
        id: button
        implicitHeight: 38
        leftPadding: 14
        rightPadding: 14
        opacity: enabled ? 1 : 0.45
        contentItem: Text { text: button.text; color: Theme.textPrimary; font.pixelSize: Theme.fontBody; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { radius: Theme.radiusSmall; color: button.checked || button.hovered ? Theme.surfaceHover : Theme.inputBackground; border.color: button.visualFocus || button.checked ? Theme.primary : Theme.border }
    }
    component Metric: Rectangle {
        required property string title
        required property string value
        required property color accent
        implicitHeight: 90
        color: Theme.surface
        radius: Theme.radiusLarge
        border.color: Theme.border
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 5
            Rectangle { width: 25; height: 3; radius: 2; color: parent.parent.accent }
            Label { text: parent.parent.value; color: Theme.textPrimary; font.pixelSize: 19; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
            Label { text: parent.parent.title; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall; Layout.fillWidth: true; elide: Text.ElideRight }
        }
    }
    component SectionTitle: Label {
        color: Theme.textPrimary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSubtitle
        font.bold: true
    }

    FinanceAccountDialog { id: accountDialog; financeViewModel: root.financeViewModel }
    FinanceTransactionDialog { id: transactionDialog; financeViewModel: root.financeViewModel }
    FinanceCategoryDialog {
        id: categoryDialog
        financeViewModel: root.financeViewModel
        onAssigned: count => root.importMessage = "Categorized " + count + (count === 1 ? " transaction." : " transactions.")
    }
    FinanceCsvImportDialog {
        id: csvDialog
        financeViewModel: root.financeViewModel
        onImported: count => root.importMessage = "Imported " + count + (count === 1 ? " transaction." : " transactions.")
    }
    PlaidImportDialog {
        id: plaidImport
        plaidViewModel: root.plaidViewModel
        financeViewModel: root.financeViewModel
        onImported: count => root.importMessage = "Imported " + count + (count === 1 ? " transaction." : " transactions.")
    }
    Dialog {
        id: confirmDeleteAll
        objectName: "financeConfirmDeleteAll"
        modal: true
        anchors.centerIn: parent
        width: Math.min(500, parent.width - 32)
        padding: 20
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.surface; radius: Theme.radiusLarge; border.color: Theme.border }
        onOpened: deleteAllError.text = ""
        contentItem: ColumnLayout {
            spacing: 12
            Label { text: "Delete all transactions?"; color: Theme.textPrimary; font.pixelSize: Theme.fontSubtitle; font.bold: true }
            Label {
                text: "Permanently delete all transactions across every account and date, including transfers and subscriptions. This cannot be undone."
                color: Theme.textPrimary
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            Label {
                text: "Accounts, opening balances, categories, and Plaid connections remain. Plaid import history is reset so transactions can be reviewed and imported again."
                color: Theme.textSecondary
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            Label { id: deleteAllError; objectName: "financeDeleteAllError"; visible: text.length > 0; color: Theme.danger; wrapMode: Text.Wrap; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Action { objectName: "financeCancelDeleteAll"; text: "Cancel"; onClicked: confirmDeleteAll.close() }
                Action {
                    objectName: "financeConfirmDeleteAllButton"
                    text: "Delete all"
                    onClicked: {
                        const message = root.financeViewModel.deleteAllTransactions();
                        if (message.length) deleteAllError.text = message;
                        else { root.importMessage = "All transactions deleted."; confirmDeleteAll.close(); }
                    }
                }
            }
        }
    }

    ScrollView {
        id: financeScroll
        objectName: "financeScroll"
        anchors.fill: parent
        anchors.margins: Theme.spacingPage
        clip: true
        rightPadding: pageScrollBar.implicitWidth + 8
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical: ScrollBar {
            id: pageScrollBar
            objectName: "financePageScrollBar"
            parent: financeScroll
            x: financeScroll.width - width
            y: 0
            height: financeScroll.height
        }
        ColumnLayout {
            width: financeScroll.availableWidth
            height: implicitHeight
            spacing: 16
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Label { text: "Finances"; color: Theme.textPrimary; font.family: Theme.fontFamily; font.pixelSize: Theme.fontTitle; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: "Manual accounts, transactions, and subscriptions."; color: Theme.textSecondary; font.pixelSize: Theme.fontBody; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                }
                Action { objectName: "financeNewAccount"; text: "+ Account"; enabled: root.financeViewModel !== null; onClicked: accountDialog.openNew(root.selectedKey) }
                Action { objectName: "financeImportCsv"; text: "Import CSV"; enabled: root.financeViewModel && root.financeViewModel.accounts.length > 0; onClicked: { root.importMessage = ""; csvDialog.openImport(); } }
                PrimaryButton {
                    objectName: "financeNewTransaction"
                    text: "+ Transaction"
                    enabled: root.financeViewModel && root.financeViewModel.accounts.length > 0
                    onClicked: transactionDialog.openNew(root.selectedKey)
                }
                Label { objectName: "financeImportMessage"; visible: root.importMessage.length > 0; text: root.importMessage; color: Theme.success; Layout.fillWidth: true }
            }
            Label {
                visible: !root.financeViewModel
                text: "Finances are unavailable."
                color: Theme.danger
            }
            RowLayout {
                Layout.fillWidth: true
                Action { text: "‹"; Accessible.name: "Previous"; onClicked: root.navigate(-1) }
                Action { text: "Today"; onClicked: root.selectedDate = new Date() }
                Action { text: "›"; Accessible.name: "Next"; onClicked: root.navigate(1) }
                Label {
                    objectName: "financePeriodHeading"
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    elide: Text.ElideRight
                    text: root.viewMode === "Year" ? Qt.formatDate(root.selectedDate, "yyyy")
                        : root.viewMode === "Month" ? Qt.formatDate(root.selectedDate, "MMMM yyyy")
                        : Qt.formatDate(root.selectedDate, "dddd, MMMM d, yyyy")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSubtitle
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }
                Repeater {
                    model: ["Day", "Month", "Year"]
                    delegate: Action {
                        required property string modelData
                        objectName: "finance" + modelData + "Button"
                        text: modelData
                        checkable: true
                        checked: root.viewMode === modelData
                        onClicked: root.viewMode = modelData
                    }
                }
            }
            Label {
                visible: root.summary && root.summary.error
                text: root.summary ? root.summary.error : ""
                color: Theme.danger
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Metric { objectName: "financeIncome"; Layout.fillWidth: true; Layout.minimumWidth: 0; title: "Income in period"; value: root.summary && !root.summary.error ? root.summary.income : "—"; accent: Theme.success }
                Metric { objectName: "financeExpenses"; Layout.fillWidth: true; Layout.minimumWidth: 0; title: root.summary && root.summary.futureEstimate ? "Recorded expenses in period" : "Expenses in period"; value: root.summary && !root.summary.error ? root.summary.expenses : "—"; accent: Theme.danger }
                Metric { objectName: "financeBalance"; Layout.fillWidth: true; Layout.minimumWidth: 0; title: "Net at period end"; value: root.summary && !root.summary.error ? root.summary.net : "—"; accent: Theme.primary }
                Metric { objectName: "financeCredit"; Layout.fillWidth: true; Layout.minimumWidth: 0; title: "Available credit"; value: root.summary && !root.summary.error ? root.summary.available : "—"; accent: Theme.warning }
            }
            Label {
                text: root.summary && !root.summary.error ? "Balances and available credit as of " + root.summary.end + ". Transfers are excluded from income and expenses." : ""
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSmall
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }
            SectionTitle { text: "Insights"; Layout.topMargin: 4 }
            RowLayout {
                Layout.fillWidth: true
                FinanceChart { Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 1; title: root.summary && root.summary.futureEstimate ? "Recorded + expected expenses by category" : "Expenses by category"; chartKind: "pie"; chartData: root.summary && !root.summary.error ? root.summary.pie : [] }
                FinanceChart { Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 1; title: root.summary && root.summary.futureEstimate ? "Recorded income vs. recorded + expected expenses" : "Income vs. expenses"; chartKind: "bar"; chartData: root.summary && !root.summary.error ? root.summary.bars : [] }
            }
            FinanceChart {
                Layout.fillWidth: true
                title: root.viewMode === "Day" ? "Last 7 days: cumulative flow and net balance" : "Period cumulative flow and net balance"
                chartKind: "line"
                expected: root.summary && !root.summary.error && root.summary.futureEstimate
                chartData: root.summary && !root.summary.error ? root.summary.lines : []
            }
            Label {
                visible: root.summary && !root.summary.error && root.summary.futureEstimate
                text: "Charts include recorded future expenses and subscription estimates; these may overlap. The balance line and account totals use recorded transactions only."
                color: Theme.textSecondary
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            SectionTitle { objectName: "financeAccountsHeading"; text: "Accounts"; Layout.topMargin: 4 }
            RowLayout {
                visible: root.plaidViewModel && root.plaidViewModel.connected
                Layout.fillWidth: true
                Label { text: "Linked Plaid accounts"; color: Theme.textPrimary; font.bold: true; Layout.fillWidth: true }
                Action { objectName: "financePlaidRefresh"; text: "Refresh"; enabled: root.plaidViewModel && !root.plaidViewModel.busy; onClicked: root.plaidViewModel.refresh() }
                Action { objectName: "financePlaidImport"; text: "Import transactions"; enabled: root.plaidViewModel && root.plaidViewModel.accounts.length > 0 && root.financeViewModel && !root.plaidViewModel.busy; onClicked: plaidImport.openImport() }
            }
            Label { visible: root.plaidViewModel && root.plaidViewModel.connected; text: root.plaidViewModel ? root.plaidViewModel.status : ""; textFormat: Text.PlainText; color: Theme.textSecondary; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Repeater {
                model: root.plaidViewModel ? root.plaidViewModel.accounts : []
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: 44
                    color: Theme.surface
                    radius: Theme.radiusSmall
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        Label { text: parent.parent.modelData.name + (parent.parent.modelData.mask ? " · " + parent.parent.modelData.mask : ""); textFormat: Text.PlainText; color: Theme.textPrimary; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: parent.parent.modelData.kind === "credit" ? "Credit" : "Bank"; color: Theme.textSecondary }
                        Label { text: parent.parent.modelData.balance + " " + parent.parent.modelData.currency; textFormat: Text.PlainText; color: Theme.textPrimary }
                    }
                }
            }
            Label { visible: root.plaidViewModel && root.plaidViewModel.accounts.length > 0; text: "Plaid balances may be cached and are separate from local account balances."; color: Theme.textSecondary; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Label { visible: root.financeViewModel && root.financeViewModel.accounts.length === 0; text: "Add an account to start recording transactions."; color: Theme.textSecondary; Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.Wrap }
            ListView {
                id: accountList
                objectName: "financeAccountList"
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(240, count * 50)
                clip: true
                spacing: 4
                model: root.summary && !root.summary.error ? root.summary.accounts : []
                ScrollBar.vertical: ScrollBar {}
                delegate: ItemDelegate {
                    id: accountRow
                    required property var modelData
                    objectName: "financeAccountRow"
                    width: ListView.view.width
                    height: 46
                    onClicked: accountDialog.openEdit(modelData)
                    background: Rectangle { radius: Theme.radiusSmall; color: accountRow.hovered ? Theme.surfaceHover : Theme.surface }
                    contentItem: RowLayout {
                        Label { text: accountRow.modelData.name; color: Theme.textPrimary; font.bold: true; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                        Label { text: accountRow.modelData.kind === "credit" ? "Credit card · owed" : "Bank / cash"; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall; Layout.maximumWidth: 140; elide: Text.ElideRight }
                        Label { text: accountRow.modelData.balanceDisplay; color: Theme.textPrimary; font.bold: true }
                        Label { visible: accountRow.modelData.kind === "credit" && accountRow.modelData.availableDisplay.length > 0; text: accountRow.modelData.availableDisplay + " available"; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                SectionTitle { text: "Transactions"; Layout.fillWidth: true }
                Action {
                    objectName: "financeAssignCategories"
                    text: "Assign categories"
                    enabled: root.financeViewModel !== null && root.summary && !root.summary.error
                    onClicked: categoryDialog.openFor(root.viewMode + " · " + root.summary.start + " – " + root.summary.end, root.summary.transactions)
                }
                Action {
                    objectName: "financeDeleteAll"
                    text: "Delete all transactions"
                    enabled: root.financeViewModel !== null
                    onClicked: confirmDeleteAll.open()
                }
            }
            Label { visible: transactionList.count === 0; text: "No recorded transactions in this period."; color: Theme.textSecondary; Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.Wrap }
            ListView {
                id: transactionList
                objectName: "financeTransactionList"
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(360, count * 50)
                clip: true
                spacing: 4
                model: root.summary && !root.summary.error ? root.summary.transactions : []
                ScrollBar.vertical: ScrollBar { objectName: "financeTransactionScrollBar" }
                delegate: ItemDelegate {
                    id: transactionRow
                    required property var modelData
                    objectName: "financeTransactionRow"
                    width: ListView.view.width
                    height: 46
                    onClicked: transactionDialog.openEdit(modelData)
                    background: Rectangle { radius: Theme.radiusSmall; color: transactionRow.hovered ? Theme.surfaceHover : Theme.surface }
                    contentItem: RowLayout {
                        spacing: 10
                        Label { text: transactionRow.modelData.date; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall }
                        Label { text: transactionRow.modelData.title; textFormat: Text.PlainText; color: Theme.textPrimary; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                        Rectangle { objectName: "financeTransactionCategoryColor" + transactionRow.modelData.id; visible: transactionRow.modelData.categoryColor.length > 0; width: 10; height: 10; radius: 5; color: visible ? transactionRow.modelData.categoryColor : "transparent" }
                        Label { objectName: "financeTransactionAccountLabel"; text: transactionRow.modelData.kind === "transfer" ? transactionRow.modelData.accountName + " → " + transactionRow.modelData.destinationName : transactionRow.modelData.accountName + " · " + transactionRow.modelData.category; textFormat: Text.PlainText; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall; Layout.maximumWidth: 200; elide: Text.ElideRight }
                        Label { text: (transactionRow.modelData.kind === "expense" ? "−" : transactionRow.modelData.kind === "income" ? "+" : "") + transactionRow.modelData.displayAmount; color: transactionRow.modelData.kind === "expense" ? Theme.danger : transactionRow.modelData.kind === "income" ? Theme.success : Theme.textPrimary; font.bold: true }
                    }
                }
            }
            SectionTitle { text: "Subscriptions" }
            Label {
                text: "Forecasts are estimates only; they do not create transactions or change totals."
                color: Theme.textSecondary
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }
            Label { visible: root.subscriptions.length === 0; text: "Mark an expense as monthly or yearly to track a subscription."; color: Theme.textSecondary; Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.Wrap }
            ListView {
                objectName: "financeSubscriptionList"
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(200, count * 44)
                clip: true
                spacing: 4
                model: root.subscriptions
                ScrollBar.vertical: ScrollBar {}
                delegate: ItemDelegate {
                    id: subscriptionRow
                    required property var modelData
                    objectName: "financeSubscriptionRow"
                    width: ListView.view.width
                    height: 40
                    onClicked: transactionDialog.openEdit(modelData)
                    background: Rectangle { radius: Theme.radiusSmall; color: subscriptionRow.hovered ? Theme.surfaceHover : Theme.surface }
                    contentItem: RowLayout {
                        Label { text: subscriptionRow.modelData.title; color: Theme.textPrimary; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                        Label { text: subscriptionRow.modelData.recurrence + (subscriptionRow.modelData.subscriptionActive ? " · active" : " · inactive"); color: Theme.textSecondary }
                        Label { text: "$" + subscriptionRow.modelData.amount; color: Theme.textPrimary }
                    }
                }
            }
            Label { text: "Estimated future charges in this period"; color: Theme.textPrimary; font.bold: true; Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.Wrap }
            Label { visible: forecastList.count === 0; text: "No estimated future charges in this period."; color: Theme.textSecondary; Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.Wrap }
            ListView {
                id: forecastList
                objectName: "financeForecastList"
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(200, count * 40)
                clip: true
                spacing: 4
                model: root.summary && !root.summary.error ? root.summary.forecasts : []
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    id: forecastRow
                    required property var modelData
                    width: ListView.view.width
                    height: 36
                    radius: Theme.radiusSmall
                    color: Theme.surface
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        Label { text: forecastRow.modelData.date; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall }
                        Label { text: forecastRow.modelData.title + " · " + forecastRow.modelData.accountName; color: Theme.textPrimary; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                        Label { text: forecastRow.modelData.amount; color: Theme.textPrimary }
                    }
                }
            }
        }
    }
}
