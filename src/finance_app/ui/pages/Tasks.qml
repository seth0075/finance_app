pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property QtObject taskViewModel

    function submitTask() {
        if (taskInput.text.trim().length > 0) {
            taskViewModel.addTask(taskInput.text)
            taskInput.clear()
            taskInput.forceActiveFocus()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 20

        Label {
            text: "Tasks"
            color: "white"
            font.pixelSize: 32
            font.bold: true
        }

        Label {
            text: "Manage your daily to-do list."
            color: "#A0A0A0"
            font.pixelSize: 16
        }

        // New task input
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            TextField {
                id: taskInput

                Layout.fillWidth: true
                placeholderText: "Enter a new task..."
                maximumLength: 500

                onAccepted: root.submitTask()
            }

            Button {
                text: "Add Task"

                enabled: taskInput.text.trim().length > 0

                onClicked: root.submitTask()
            }
        }

        // Task list
        ListView {
            id: taskList

            Layout.fillWidth: true
            Layout.fillHeight: true

            clip: true
            spacing: 8

            model: root.taskViewModel.tasks

            ScrollBar.vertical: ScrollBar {}

            delegate: Rectangle {
                id: taskRow

                required property var modelData

                width: taskList.width
                height: Math.max(56, taskLabel.implicitHeight + 24)

                radius: 8
                color: "#20232A"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    CheckBox {
                        checked: taskRow.modelData.completed

                        onToggled: {
                            root.taskViewModel.setCompleted(
                                taskRow.modelData.id,
                                checked
                            )
                        }
                    }

                    Label {
                        id: taskLabel

                        Layout.fillWidth: true

                        text: taskRow.modelData.title

                        color: taskRow.modelData.completed
                            ? "#808080"
                            : "white"

                        font.pixelSize: 16

                        font.strikeout:
                            taskRow.modelData.completed

                        wrapMode: Text.Wrap
                    }

                    Button {
                        text: "Delete"

                        onClicked: {
                            root.taskViewModel.deleteTask(
                                taskRow.modelData.id
                            )
                        }
                    }
                }
            }

            Label {
                anchors.centerIn: parent

                visible: taskList.count === 0

                text: "No tasks yet. Add one above!"
                color: "#808080"
            }
        }

        Label {
            text: taskList.count + " total tasks"
            color: "#A0A0A0"
        }
    }
}