import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import "../themes"

Rectangle {
    id: root

    required property string taskId
    required property string title
    required property bool completed
    required property int priority
    required property var subtasks
    property bool expanded: false

    readonly property int completedSubtasks: subtasks.filter(subtask => subtask.completed).length
    readonly property color priorityColor: priority === 3 ? Theme.danger : priority === 2 ? Theme.warning : Theme.textSecondary
    readonly property string priorityLabel: priority === 3 ? "High" : priority === 2 ? "Medium" : "Low"

    signal completionChanged(bool value)
    signal deleteRequested
    signal editRequested
    signal expansionChanged(bool value)
    signal subtaskAdded(string title)
    signal subtaskCompletionChanged(string subtaskId, bool value)
    signal subtaskDeleteRequested(string subtaskId)

    implicitHeight: content.implicitHeight + 16
    radius: Theme.radiusSmall
    color: hoverHandler.hovered || expanded ? Theme.surfaceHover : "transparent"

    Behavior on color {
        ColorAnimation { duration: 120 }
    }

    HoverHandler { id: hoverHandler }

    component TaskCheckBox: ThemedCheckBox {
        id: checkBox
        property string taskTitle

        Accessible.name: (checked ? "Mark incomplete: " : "Mark complete: ") + taskTitle
    }

    component RowButton: Button {
        id: button

        implicitHeight: 32
        leftPadding: 8
        rightPadding: 8
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall

        contentItem: Text {
            text: button.text
            color: button.hovered ? Theme.textPrimary : Theme.textSecondary
            font: button.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            radius: Theme.radiusSmall
            color: button.hovered ? Theme.background : "transparent"
            border.width: button.visualFocus ? 1 : 0
            border.color: Theme.primary
        }
    }

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 8
        spacing: 4

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TaskCheckBox {
                objectName: "taskCompletion"
                taskTitle: root.title
                checked: root.completed
                onToggled: root.completionChanged(checked)
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 3

                Label {
                    Layout.fillWidth: true
                    text: root.title
                    color: root.completed ? Theme.textMuted : Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    font.strikeout: root.completed
                    wrapMode: Text.Wrap
                }

                RowLayout {
                    spacing: 8
                    Label {
                        objectName: "taskPriorityLabel"
                        text: root.priorityLabel + " priority"
                        color: root.priorityColor
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                    }

                    Label {
                        visible: root.subtasks.length > 0
                        text: root.completedSubtasks + "/" + root.subtasks.length + " subtasks"
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                    }
                }
            }

            RowButton {
                objectName: "toggleSubtasksButton"
                text: root.expanded ? "Hide subtasks" : "Subtasks"
                Accessible.name: (root.expanded ? "Hide subtasks for " : "Show subtasks for ") + root.title
                onClicked: root.expansionChanged(!root.expanded)
            }

            RowButton {
                objectName: "editTaskButton"
                text: "Edit"
                onClicked: root.editRequested()
            }

            RowButton {
                text: "×"
                font.pixelSize: 22
                Accessible.name: "Delete task: " + root.title
                ToolTip.visible: hovered
                ToolTip.text: "Delete task"
                ToolTip.delay: 500
                onClicked: root.deleteRequested()
            }
        }

        ColumnLayout {
            visible: root.expanded
            Layout.fillWidth: true
            Layout.leftMargin: 44
            Layout.rightMargin: 8
            spacing: 4

            Repeater {
                model: root.subtasks

                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 8

                    TaskCheckBox {
                        objectName: "subtaskCompletion"
                        taskTitle: modelData.title
                        checked: modelData.completed
                        onToggled: root.subtaskCompletionChanged(modelData.id, checked)
                    }

                    Label {
                        Layout.fillWidth: true
                        text: modelData.title
                        color: modelData.completed ? Theme.textMuted : Theme.textPrimary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        font.strikeout: modelData.completed
                        wrapMode: Text.Wrap
                    }

                    RowButton {
                        objectName: "deleteSubtaskButton"
                        text: "×"
                        font.pixelSize: 20
                        Accessible.name: "Delete subtask: " + modelData.title
                        onClicked: root.subtaskDeleteRequested(modelData.id)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                TextField {
                    id: subtaskInput
                    objectName: "subtaskInput"
                    Layout.fillWidth: true
                    placeholderText: "Add a subtask"
                    placeholderTextColor: Theme.textMuted
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    maximumLength: 500
                    implicitHeight: 36
                    leftPadding: 10
                    rightPadding: 10
                    selectByMouse: true
                    Accessible.name: "New subtask for " + root.title

                    function submit() {
                        const title = text.trim();
                        if (title.length === 0)
                            return;
                        clear();
                        root.subtaskAdded(title);
                    }

                    onAccepted: submit()
                    background: Rectangle {
                        radius: Theme.radiusSmall
                        color: Theme.inputBackground
                        border.color: subtaskInput.activeFocus ? Theme.primary : Theme.border
                    }
                }

                RowButton {
                    objectName: "addSubtaskButton"
                    text: "Add"
                    enabled: subtaskInput.text.trim().length > 0
                    opacity: enabled ? 1 : 0.45
                    onClicked: subtaskInput.submit()
                }
            }
        }
    }
}
