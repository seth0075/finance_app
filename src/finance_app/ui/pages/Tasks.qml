pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import "../components"
import "../components/tasks"
import "../themes"

Item {
    id: root

    required property QtObject taskViewModel

    property string currentPeriod: "Today"
    property string currentFilter: "All"
    property var expandedTasks: ({})

    property string todayDate: root.taskViewModel.today()

    readonly property var allTasks: root.taskViewModel.tasks

    readonly property var periodTasks: {
        const today = root.todayDate;

        if (root.currentPeriod === "All")
            return root.allTasks;

        if (root.currentPeriod === "No date")
            return root.allTasks.filter(task => !task.dueDate);

        if (root.currentPeriod === "Overdue")
            return root.allTasks.filter(task => task.dueDate && task.dueDate < today && !task.completed);

        const range = root.taskViewModel.dateRange(root.currentPeriod);

        return root.allTasks.filter(task => task.dueDate && task.dueDate >= range.start && task.dueDate <= range.end);
    }

    readonly property int totalCount: root.periodTasks.length

    readonly property int completedCount: root.periodTasks.filter(task => task.completed).length

    readonly property int remainingCount: root.totalCount - root.completedCount

    readonly property real progress: root.totalCount > 0 ? root.completedCount / root.totalCount : 0

    readonly property var filteredTasks: {
        switch (root.currentFilter) {
        case "Active":
            return root.periodTasks.filter(task => !task.completed);
        case "Completed":
            return root.periodTasks.filter(task => task.completed);
        default:
            return root.periodTasks;
        }
    }

    Timer {
        interval: 60000
        running: true
        repeat: true

        onTriggered: {
            root.todayDate = root.taskViewModel.today();
        }
    }

    TaskDialog {
        id: taskDialog
        taskViewModel: root.taskViewModel
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingPage

        spacing: Theme.spacingLarge

        // Page header
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingMedium

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Label {
                    text: "Tasks"

                    color: Theme.textPrimary

                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontTitle
                    font.bold: true
                }

                Label {
                    text: "Stay organized and keep track of your progress."

                    Layout.fillWidth: true

                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontBody
                    wrapMode: Text.Wrap
                }
            }

            PrimaryButton {
                objectName: "newTaskButton"
                text: "+ New task"
                Layout.alignment: Qt.AlignVCenter

                onClicked: {
                    taskDialog.openNew(root.todayDate);
                }
            }
        }

        // Date Range Selector
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Repeater {
                model: ["Today", "Week", "Month", "Overdue", "No date", "All"]

                delegate: Button {
                    id: periodButton

                    required property string modelData

                    text: modelData

                    Layout.fillWidth: true
                    implicitHeight: 36

                    onClicked: {
                        root.currentPeriod = periodButton.modelData;
                    }

                    contentItem: Text {
                        text: periodButton.text

                        color: root.currentPeriod === periodButton.modelData ? Theme.textPrimary : Theme.textSecondary

                        font.pixelSize: Theme.fontBody

                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    background: Rectangle {
                        radius: Theme.radiusSmall

                        color: root.currentPeriod === periodButton.modelData ? Theme.surfaceHover : "transparent"

                        border.color: root.currentPeriod === periodButton.modelData ? Theme.primary : Theme.border
                    }
                }
            }
        }

        // Statistics cards
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingMedium

            StatCard {
                Layout.fillWidth: true
                Layout.minimumWidth: 0

                title: "Total tasks"
                value: String(root.totalCount)
                accentColor: Theme.primary
            }

            StatCard {
                Layout.fillWidth: true
                Layout.minimumWidth: 0

                title: "Remaining"
                value: String(root.remainingCount)
                accentColor: Theme.warning
            }

            StatCard {
                Layout.fillWidth: true
                Layout.minimumWidth: 0

                title: "Completed"
                value: String(root.completedCount)
                accentColor: Theme.success
            }
        }

        // Progress card
        Rectangle {
            Layout.fillWidth: true

            implicitHeight: progressContent.implicitHeight + 32

            color: Theme.surface
            radius: Theme.radiusLarge
            border.color: Theme.border

            ColumnLayout {
                id: progressContent

                anchors.fill: parent
                anchors.margins: 16

                spacing: 10

                RowLayout {
                    Layout.fillWidth: true

                    Label {
                        text: "Overall progress"

                        color: Theme.textPrimary
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Label {
                        text: Math.round(root.progress * 100) + "%"

                        color: Theme.success
                        font.pixelSize: Theme.fontBody
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 7

                    radius: 4
                    color: Theme.border

                    Rectangle {
                        height: parent.height
                        width: parent.width * root.progress

                        radius: 4
                        color: Theme.success

                        Behavior on width {
                            NumberAnimation {
                                duration: 250
                                easing.type: Easing.OutCubic
                            }
                        }
                    }
                }

                Label {
                    text: root.completedCount + " of " + root.totalCount + " tasks completed"

                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontSmall
                }
            }
        }

        // Main task list card
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 140

            color: Theme.surface
            radius: Theme.radiusLarge
            border.color: Theme.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16

                spacing: 12

                // Task list header and filters
                RowLayout {
                    Layout.fillWidth: true

                    Label {
                        text: "My tasks"

                        color: Theme.textPrimary

                        font.pixelSize: Theme.fontSubtitle
                        font.bold: true
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Rectangle {
                        implicitWidth: filterLayout.implicitWidth + 8
                        implicitHeight: 36

                        radius: Theme.radiusSmall
                        color: Theme.background

                        RowLayout {
                            id: filterLayout

                            anchors.centerIn: parent
                            spacing: 2

                            Repeater {
                                model: ["All", "Active", "Completed"]

                                delegate: Button {
                                    id: filterButton

                                    required property string modelData

                                    implicitWidth: 80
                                    implicitHeight: 28

                                    text: modelData

                                    checkable: true
                                    checked: root.currentFilter === modelData

                                    onClicked: {
                                        root.currentFilter = modelData;
                                    }

                                    contentItem: Text {
                                        text: filterButton.text

                                        color: filterButton.checked ? Theme.textPrimary : Theme.textSecondary

                                        font.pixelSize: Theme.fontSmall

                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }

                                    background: Rectangle {
                                        radius: Theme.radiusSmall

                                        color: filterButton.checked ? Theme.surfaceHover : "transparent"

                                        border.width: filterButton.activeFocus ? 1 : 0

                                        border.color: Theme.primary
                                    }
                                }
                            }
                        }
                    }
                }

                // Header divider
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1

                    color: Theme.border
                }

                // Task list
                ListView {
                    id: taskList

                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    clip: true
                    spacing: 4

                    model: root.filteredTasks

                    ScrollBar.vertical: ScrollBar {}

                    delegate: TaskRow {
                        id: taskDelegate

                        required property var modelData

                        width: ListView.view.width

                        taskId: modelData.id
                        title: modelData.title
                        completed: modelData.completed
                        priority: modelData.priority
                        subtasks: modelData.subtasks
                        expanded: root.expandedTasks[taskId] === true

                        onCompletionChanged: function (value) {
                            root.taskViewModel.setCompleted(taskDelegate.taskId, value);
                        }

                        onExpansionChanged: function (value) {
                            const expanded = Object.assign({}, root.expandedTasks);
                            if (value)
                                expanded[taskDelegate.taskId] = true;
                            else
                                delete expanded[taskDelegate.taskId];
                            root.expandedTasks = expanded;
                        }

                        onSubtaskAdded: function (title) {
                            root.taskViewModel.addSubtask(taskDelegate.taskId, title);
                        }

                        onSubtaskCompletionChanged: function (subtaskId, value) {
                            root.taskViewModel.setSubtaskCompleted(subtaskId, value);
                        }

                        onSubtaskDeleteRequested: function (subtaskId) {
                            root.taskViewModel.deleteSubtask(subtaskId);
                        }

                        onEditRequested: {
                            taskDialog.openEdit(taskDelegate.modelData);
                        }

                        onDeleteRequested: {
                            const expanded = Object.assign({}, root.expandedTasks);
                            delete expanded[taskDelegate.taskId];
                            root.expandedTasks = expanded;
                            root.taskViewModel.deleteTask(taskDelegate.taskId);
                        }
                    }

                    // Empty state
                    Column {
                        anchors.centerIn: parent

                        visible: taskList.count === 0
                        spacing: 8

                        Label {
                            anchors.horizontalCenter: parent.horizontalCenter

                            text: "No tasks to display"

                            color: Theme.textSecondary
                            font.pixelSize: 16
                            font.bold: true
                        }

                        Label {
                            anchors.horizontalCenter: parent.horizontalCenter

                            text: root.currentFilter === "All" ? "Add a task to get started." : "Try selecting a different filter."

                            color: Theme.textMuted
                            font.pixelSize: Theme.fontSmall
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1

                    color: Theme.border
                }

                Label {
                    text: "Showing " + taskList.count + " of " + root.totalCount + " tasks"

                    color: Theme.textMuted
                    font.pixelSize: Theme.fontSmall
                }
            }
        }
    }
}
