import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import "../themes"

Dialog {
    id: root

    required property QtObject taskViewModel

    property string editingId: ""

    modal: true
    width: Math.min(480, parent.width - 32)
    padding: 24
    spacing: 20

    anchors.centerIn: parent

    signal saved

    component FormLabel: Label {
        color: Theme.textPrimary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
        font.bold: true
    }

    component FormField: TextField {
        color: Theme.textPrimary
        placeholderTextColor: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBody
        leftPadding: 12
        rightPadding: 12
        implicitHeight: 40
        selectByMouse: true

        background: Rectangle {
            radius: Theme.radiusSmall
            color: Theme.inputBackground
            border.color: parent.activeFocus ? Theme.primary : Theme.border
        }
    }

    component SecondaryButton: Button {
        id: button

        implicitHeight: 40
        leftPadding: 14
        rightPadding: 14
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBody

        contentItem: Text {
            text: button.text
            font: button.font
            color: Theme.textPrimary
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            radius: Theme.radiusSmall
            color: button.down || button.hovered ? Theme.surfaceHover : Theme.inputBackground
            border.color: button.visualFocus ? Theme.primary : Theme.border
        }
    }

    function openNew(defaultDate) {
        root.editingId = "";
        titleInput.text = "";
        descriptionInput.text = "";
        dateInput.text = defaultDate;
        priorityInput.currentIndex = 1;
        errorLabel.text = "";

        root.open();
    }

    function openEdit(task) {
        root.editingId = task.id;
        titleInput.text = task.title;
        descriptionInput.text = task.description;
        dateInput.text = task.dueDate;
        priorityInput.currentIndex = task.priority - 1;
        errorLabel.text = "";

        root.open();
    }

    function saveTask() {
        let success;

        if (root.editingId) {
            success = root.taskViewModel.updateTask(root.editingId, titleInput.text, descriptionInput.text, dateInput.text.trim(), priorityInput.currentIndex + 1);
        } else {
            success = root.taskViewModel.addTask(titleInput.text, descriptionInput.text, dateInput.text.trim(), priorityInput.currentIndex + 1);
        }

        if (success) {
            root.saved();
            root.close();
        } else {
            errorLabel.text = "Enter a valid title and date.";
        }
    }

    onOpened: titleInput.forceActiveFocus()

    Overlay.modal: Rectangle {
        color: "#99000000"
    }

    background: Rectangle {
        color: Theme.surface
        radius: Theme.radiusLarge
        border.color: Theme.border
    }

    header: Item {
        implicitHeight: dialogHeading.implicitHeight + 24

        ColumnLayout {
            id: dialogHeading
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            anchors.topMargin: 24
            spacing: 6

            Label {
                text: root.editingId ? "Edit task" : "New task"
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSubtitle
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                text: root.editingId ? "Update the details of your task." : "Add a task and keep your plans on track."
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                wrapMode: Text.Wrap
            }
        }
    }

    contentItem: ColumnLayout {
        spacing: 8

        FormLabel {
            text: "Task title"
        }

        FormField {
            id: titleInput
            objectName: "taskTitleInput"

            Layout.fillWidth: true
            maximumLength: 500
            placeholderText: "What needs to be done?"
        }

        FormLabel {
            text: "Description"
            Layout.topMargin: 8
        }

        TextArea {
            id: descriptionInput

            Layout.fillWidth: true
            Layout.preferredHeight: 76

            placeholderText: "Optional details"
            placeholderTextColor: Theme.textMuted
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            padding: 12
            wrapMode: Text.Wrap
            selectByMouse: true

            background: Rectangle {
                radius: Theme.radiusSmall
                color: Theme.inputBackground
                border.color: descriptionInput.activeFocus ? Theme.primary : Theme.border
            }
        }

        FormLabel {
            text: "Due date"
            Layout.topMargin: 8
        }

        RowLayout {
            Layout.fillWidth: true

            FormField {
                id: dateInput

                Layout.fillWidth: true
                placeholderText: "YYYY-MM-DD"
            }

            SecondaryButton {
                text: "Today"

                onClicked: {
                    dateInput.text = root.taskViewModel.today();
                }
            }

            SecondaryButton {
                text: "Clear"
                onClicked: dateInput.clear()
            }
        }

        FormLabel {
            text: "Priority"
            Layout.topMargin: 8
        }

        ThemedComboBox {
            id: priorityInput
            objectName: "taskPriorityInput"

            Layout.fillWidth: true

            model: ["Low", "Medium", "High"]
            currentIndex: 1
        }

        Label {
            id: errorLabel

            Layout.fillWidth: true

            color: Theme.danger
            visible: text.length > 0
            wrapMode: Text.Wrap
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 12

            Item {
                Layout.fillWidth: true
            }

            SecondaryButton {
                text: "Cancel"
                onClicked: root.close()
            }

            PrimaryButton {
                objectName: "saveTaskButton"
                text: root.editingId ? "Save changes" : "Create task"

                enabled: titleInput.text.trim().length > 0

                onClicked: root.saveTask()
            }
        }
    }
}
