import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import "../themes"

Dialog {
    id: root
    objectName: "eventDialog"
    required property QtObject calendarViewModel
    property string editingId: ""
    property string editScope: "series"
    property string occurrenceDate: ""
    property bool hasExceptions: false
    property string originalStartDate: ""
    property string originalRepeat: "none"
    property string originalUntil: ""
    readonly property var eventCalendars: calendarViewModel.calendars.filter(calendar => calendar.id !== "tasks")
    signal deleted()

    modal: true
    anchors.centerIn: parent
    width: Math.min(500, parent.width - 32)
    padding: 24
    spacing: 16

    function openNew(day) {
        editingId = "";
        editScope = "series";
        occurrenceDate = "";
        hasExceptions = false;
        titleInput.text = "";
        startDate.text = day;
        endDate.text = day;
        startTime.text = "09:00";
        endTime.text = "10:00";
        allDay.checked = false;
        calendarInput.currentIndex = 0;
        repeatInput.currentIndex = 0;
        repeatUntil.text = "";
        error.text = "";
        open();
    }

    function openEdit(event, scope) {
        editingId = event.id;
        editScope = scope;
        occurrenceDate = event.occurrenceDate;
        hasExceptions = event.series.hasExceptions;
        originalStartDate = event.series.startDate;
        originalRepeat = event.series.recurrence;
        originalUntil = event.series.until;
        const source = scope === "series" ? event.series : event;
        titleInput.text = source.title;
        startDate.text = source.startDate;
        endDate.text = source.endDate;
        startTime.text = source.startTime;
        endTime.text = source.endTime;
        allDay.checked = source.allDay;
        calendarInput.currentIndex = eventCalendars.findIndex(calendar => calendar.id === source.calendarId);
        repeatInput.currentIndex = ["none", "daily", "weekly", "monthly", "yearly"].indexOf(event.series.recurrence);
        repeatUntil.text = event.series.until;
        error.text = "";
        open();
    }

    function save() {
        const recurrence = ["none", "daily", "weekly", "monthly", "yearly"][repeatInput.currentIndex];
        const until = repeatInput.currentIndex > 0 ? repeatUntil.text : "";
        if (editScope === "series" && hasExceptions
                && (startDate.text !== originalStartDate || recurrence !== originalRepeat || until !== originalUntil)) {
            confirmReset.open();
            return;
        }
        performSave(false);
    }

    function performSave(resetExceptions) {
        const message = calendarViewModel.saveEvent(editingId, titleInput.text, startDate.text,
            endDate.text, startTime.text, endTime.text, allDay.checked,
            calendarInput.currentIndex >= 0 ? eventCalendars[calendarInput.currentIndex].id : "",
            ["none", "daily", "weekly", "monthly", "yearly"][repeatInput.currentIndex],
            repeatInput.currentIndex > 0 ? repeatUntil.text : "", editScope, occurrenceDate, resetExceptions);
        if (message.length)
            error.text = message;
        else
            close();
    }

    onOpened: titleInput.forceActiveFocus()
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
        selectByMouse: true
        background: Rectangle {
            color: Theme.inputBackground
            radius: Theme.radiusSmall
            border.color: parent.activeFocus ? Theme.primary : Theme.border
        }
    }
    component Caption: Label {
        color: Theme.textPrimary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
        font.bold: true
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

    contentItem: ColumnLayout {
        spacing: 8
        Label {
            text: root.editingId ? "Edit event" : "New event"
            color: Theme.textPrimary
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSubtitle
            font.bold: true
            Layout.bottomMargin: 8
        }
        Caption { text: "Title" }
        Field {
            id: titleInput
            objectName: "eventTitle"
            Layout.fillWidth: true
            maximumLength: 500
            placeholderText: "Event title"
        }
        ThemedCheckBox {
            id: allDay
            objectName: "eventAllDay"
            text: "All day"
        }
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "Start date" }
                Field {
                    id: startDate
                    objectName: "eventStartDate"
                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "End date" }
                Field {
                    id: endDate
                    objectName: "eventEndDate"
                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }
            }
        }
        RowLayout {
            visible: !allDay.checked
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "Start time" }
                Field {
                    id: startTime
                    objectName: "eventStartTime"
                    Layout.fillWidth: true
                    placeholderText: "HH:MM"
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "End time" }
                Field {
                    id: endTime
                    objectName: "eventEndTime"
                    Layout.fillWidth: true
                    placeholderText: "HH:MM"
                }
            }
        }
        Caption { text: "Calendar"; Layout.topMargin: 4 }
        ThemedComboBox {
            id: calendarInput
            objectName: "eventCalendar"
            Layout.fillWidth: true
            model: root.eventCalendars
            textRole: "name"
        }
        RowLayout {
            Layout.fillWidth: true
            visible: root.editScope === "series"
            ColumnLayout {
                Layout.fillWidth: true
                Caption { text: "Repeat" }
                ThemedComboBox {
                    id: repeatInput
                    objectName: "eventRepeat"
                    Layout.fillWidth: true
                    model: ["Does not repeat", "Daily", "Weekly", "Monthly", "Yearly"]
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                visible: repeatInput.currentIndex > 0
                Caption { text: "Repeat until (optional)" }
                Field {
                    id: repeatUntil
                    objectName: "eventRepeatUntil"
                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }
            }
        }
        Label {
            id: error
            objectName: "eventError"
            Layout.fillWidth: true
            visible: text.length > 0
            text: ""
            color: Theme.danger
            wrapMode: Text.Wrap
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 8
            Action {
                objectName: "deleteEventButton"
                text: "Delete"
                visible: root.editingId.length > 0
                onClicked: confirmDelete.open()
            }
            Item { Layout.fillWidth: true }
            Action { text: "Cancel"; onClicked: root.close() }
            PrimaryButton {
                objectName: "saveEventButton"
                text: root.editingId ? "Save changes" : "Create event"
                onClicked: root.save()
            }
        }
    }

    Dialog {
        id: confirmReset
        objectName: "confirmResetOccurrences"
        title: "Remove individual occurrence changes?"
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: root.performSave(true)
    }

    Dialog {
        id: confirmDelete
        objectName: "confirmDeleteEvent"
        title: root.editScope === "occurrence" ? "Delete this occurrence?" : "Delete this event or series?"
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: {
            const message = root.calendarViewModel.deleteEvent(root.editingId, root.editScope, root.occurrenceDate);
            if (!message.length) {
                root.deleted();
                root.close();
            } else {
                error.text = message;
            }
        }
    }
}
