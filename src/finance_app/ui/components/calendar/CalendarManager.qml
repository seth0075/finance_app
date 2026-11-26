import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs as QuickDialogs
import QtQuick.Layouts

import ".."
import "../../themes"

Dialog {
    id: root
    objectName: "calendarManager"
    required property QtObject calendarViewModel
    property string editingId: ""
    modal: true
    width: Math.min(480, parent.width - 32)
    padding: 24
    anchors.centerIn: parent

    function edit(calendar) {
        editingId = calendar.id;
        nameInput.text = calendar.name;
        colorInput.text = calendar.color;
        error.text = "";
    }

    function openNew() {
        editingId = "";
        nameInput.text = "";
        colorInput.text = "#7395F5";
        error.text = "";
    }

    onOpened: openNew()
    Overlay.modal: Rectangle { color: "#99000000" }
    background: Rectangle {
        color: Theme.surface
        radius: Theme.radiusLarge
        border.color: Theme.border
    }
    component Field: TextField {
        color: Theme.textPrimary
        placeholderTextColor: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBody
        leftPadding: 10
        rightPadding: 10
        implicitHeight: 40
        background: Rectangle {
            color: Theme.inputBackground
            radius: Theme.radiusSmall
            border.color: parent.activeFocus ? Theme.primary : Theme.border
        }
    }
    component Action: Button {
        id: button
        implicitHeight: 36
        leftPadding: 12
        rightPadding: 12
        contentItem: Text {
            text: button.text
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: button.hovered ? Theme.surfaceHover : Theme.inputBackground
            radius: Theme.radiusSmall
            border.color: button.visualFocus ? Theme.primary : Theme.border
        }
    }

    QuickDialogs.ColorDialog {
        id: picker
        objectName: "calendarColorPicker"
        title: "Choose calendar color"
        selectedColor: colorInput.acceptableInput ? colorInput.text : "#7395F5"
        onAccepted: {
            const red = Math.round(selectedColor.r * 255).toString(16).padStart(2, "0");
            const green = Math.round(selectedColor.g * 255).toString(16).padStart(2, "0");
            const blue = Math.round(selectedColor.b * 255).toString(16).padStart(2, "0");
            colorInput.text = ("#" + red + green + blue).toUpperCase();
        }
    }

    contentItem: ColumnLayout {
        spacing: 10
        Label {
            text: "Manage calendars"
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSubtitle
            font.bold: true
        }
        Label {
            text: "Use the circles to show or hide calendars. Select a local calendar to edit it; select it again to create a new one. Google calendars are read-only."
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSmall
            Layout.fillWidth: true
            wrapMode: Text.Wrap
        }
        ListView {
            objectName: "calendarList"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(150, contentHeight)
            clip: true
            spacing: 2
            model: root.calendarViewModel.calendars
            ScrollBar.vertical: ScrollBar {}
            delegate: ItemDelegate {
                id: row
                required property var modelData
                objectName: "calendarRow" + modelData.id
                width: ListView.view.width
                height: 48
                onClicked: {
                    if (modelData.readOnly)
                        return;
                    if (root.editingId === modelData.id)
                        root.openNew();
                    else
                        root.edit(modelData);
                }
                background: Rectangle {
                    radius: Theme.radiusSmall
                    color: root.editingId === row.modelData.id || (row.hovered && !row.modelData.readOnly) ? Theme.surfaceHover : Theme.inputBackground
                }
                contentItem: RowLayout {
                    spacing: 10
                    ThemedCheckBox {
                        objectName: "calendarVisibility" + row.modelData.id
                        checked: row.modelData.visible
                        Accessible.name: "Show " + row.modelData.name
                        onClicked: {
                            const message = root.calendarViewModel.setCalendarVisible(row.modelData.id, checked);
                            if (message.length) {
                                error.text = message;
                                checked = Qt.binding(function() { return row.modelData.visible; });
                            }
                        }
                    }
                    Rectangle { width: 12; height: 12; radius: 6; color: row.modelData.color }
                    Label { text: row.modelData.name; color: Theme.textPrimary; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: row.modelData.readOnly ? "Google · read-only" : row.modelData.id === "tasks" ? "Tasks" : ""; color: Theme.textSecondary }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: root.editingId ? "Edit calendar" : "New calendar"
                color: Theme.textPrimary
                font.bold: true
                Layout.fillWidth: true
            }
        }
        Field {
            id: nameInput
            objectName: "calendarName"
            Layout.fillWidth: true
            placeholderText: "Calendar name"
            maximumLength: 100
            enabled: root.editingId !== "tasks"
        }
        RowLayout {
            Layout.fillWidth: true
            Field {
                id: colorInput
                objectName: "calendarColor"
                Layout.fillWidth: true
                placeholderText: "#RRGGBB"
                maximumLength: 7
                validator: RegularExpressionValidator { regularExpression: /#[0-9a-fA-F]{6}/ }
            }
            Action {
                objectName: "chooseCalendarColor"
                text: "Choose color"
                onClicked: picker.open()
            }
            Rectangle {
                width: 28
                height: 28
                radius: 14
                color: colorInput.acceptableInput ? colorInput.text : "transparent"
                border.color: Theme.border
            }
        }
        Label {
            id: error
            objectName: "calendarError"
            Layout.fillWidth: true
            visible: text.length > 0
            color: Theme.danger
            wrapMode: Text.Wrap
        }
        RowLayout {
            Layout.fillWidth: true
            Action {
                objectName: "deleteCalendarButton"
                text: "Delete"
                visible: root.editingId.length > 0 && root.editingId !== "tasks"
                onClicked: confirmDelete.open()
            }
            Item { Layout.fillWidth: true }
            Action { text: "Close"; onClicked: root.close() }
            PrimaryButton {
                objectName: "saveCalendarButton"
                text: root.editingId ? "Save" : "Create"
                onClicked: {
                    const message = root.calendarViewModel.saveCalendar(root.editingId, nameInput.text, colorInput.text);
                    if (message.length)
                        error.text = message;
                    else
                        root.openNew();
                }
            }
        }
    }
    Dialog {
        id: confirmDelete
        objectName: "confirmDeleteCalendar"
        title: "Delete calendar and all its events?"
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: {
            const message = root.calendarViewModel.deleteCalendar(root.editingId);
            if (message.length)
                error.text = message;
            else
                root.openNew();
        }
    }
}
