pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import "../components"
import "../components/calendar"
import "../themes"

Item {
    id: root
    objectName: "calendarPage"
    required property QtObject taskViewModel
    required property QtObject calendarViewModel
    property QtObject googleViewModel
    property date selectedDate: new Date()
    property string viewMode: "Month"
    readonly property string selectedKey: dateKey(selectedDate)

    function dateKey(day) {
        return Qt.formatDate(day, "yyyy-MM-dd");
    }

    function dateOffset(day, amount) {
        return new Date(day.getFullYear(), day.getMonth(), day.getDate() + amount, 12);
    }

    function weekStart(day) {
        const first = Qt.locale().firstDayOfWeek % 7;
        return dateOffset(day, -((day.getDay() - first + 7) % 7));
    }

    function navigate(amount) {
        const day = selectedDate;
        if (viewMode === "Month") {
            const first = new Date(day.getFullYear(), day.getMonth() + amount, 1, 12);
            const last = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
            selectedDate = new Date(first.getFullYear(), first.getMonth(), Math.min(day.getDate(), last), 12);
        } else {
            selectedDate = dateOffset(day, amount * (viewMode === "Week" ? 7 : 1));
        }
    }

    function entriesFor(day) {
        const key = dateKey(day);
        const items = [];
        const calendars = calendarViewModel.calendars;
        const tasksCalendar = calendars.find(calendar => calendar.id === "tasks");
        const revision = calendarViewModel.events;
        for (const task of taskViewModel.tasks) {
            if (tasksCalendar.visible && task.dueDate === key)
                items.push({ kind: "task", title: task.title, color: tasksCalendar.color,
                    completed: task.completed, time: "Task" });
        }
        for (const event of calendarViewModel.occurrencesForDate(key)) {
            let label = "All day";
            if (!event.allDay)
                label = (event.startDate === key ? event.startTime : "00:00") + "–"
                    + (event.endDate === key ? event.endTime : "24:00");
            items.push({ kind: "event", title: event.title, color: event.color,
                time: label, event: event });
        }
        return items;
    }

    component NavButton: Button {
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
            radius: Theme.radiusSmall
            color: button.checked || button.hovered ? Theme.surfaceHover : Theme.inputBackground
            border.color: button.visualFocus || button.checked ? Theme.primary : Theme.border
        }
    }

    EventDialog {
        id: eventDialog
        calendarViewModel: root.calendarViewModel
    }

    CalendarManager {
        id: calendarManager
        calendarViewModel: root.calendarViewModel
    }

    Dialog {
        id: editChoice
        objectName: "recurrenceEditChoice"
        property var selectedEvent
        modal: true
        anchors.centerIn: parent
        padding: 20
        background: Rectangle { color: Theme.surface; radius: Theme.radiusLarge; border.color: Theme.border }
        contentItem: ColumnLayout {
            spacing: 12
            Label { text: "Edit recurring event"; color: Theme.textPrimary; font.bold: true; font.pixelSize: Theme.fontSubtitle }
            Label { text: "Choose which event to edit or delete."; color: Theme.textSecondary }
            RowLayout {
                NavButton {
                    objectName: "editOccurrenceButton"
                    text: "This occurrence"
                    onClicked: { editChoice.close(); eventDialog.openEdit(editChoice.selectedEvent, "occurrence"); }
                }
                NavButton {
                    objectName: "editSeriesButton"
                    text: "Entire series"
                    onClicked: { editChoice.close(); eventDialog.openEdit(editChoice.selectedEvent, "series"); }
                }
                NavButton { text: "Cancel"; onClicked: editChoice.close() }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingPage
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Label {
                    text: "Calendar"
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontTitle
                    font.bold: true
                }
                Label {
                    text: "Your tasks and events, all in one place."
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    color: Theme.textSecondary
                    font.pixelSize: Theme.fontBody
                }
            }
            NavButton {
                objectName: "manageCalendarsButton"
                text: "Calendars"
                onClicked: calendarManager.open()
            }
            PrimaryButton {
                objectName: "newEventButton"
                text: "+ New event"
                onClicked: eventDialog.openNew(root.selectedKey)
            }
        }

        Label {
            Layout.fillWidth: true
            visible: root.googleViewModel !== null && (root.googleViewModel.connected || root.googleViewModel.hasCache)
            text: root.googleViewModel ? "Google (read-only): " + root.googleViewModel.cacheCoverage : ""
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.Wrap
        }

        RowLayout {
            Layout.fillWidth: true
            NavButton { text: "‹"; Accessible.name: "Previous"; onClicked: root.navigate(-1) }
            NavButton { text: "Today"; onClicked: root.selectedDate = new Date() }
            NavButton { text: "›"; Accessible.name: "Next"; onClicked: root.navigate(1) }
            Label {
                objectName: "calendarHeading"
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                elide: Text.ElideRight
                text: root.viewMode === "Month" ? Qt.formatDate(root.selectedDate, "MMMM yyyy")
                    : root.viewMode === "Week" ? Qt.formatDate(root.weekStart(root.selectedDate), "MMM d")
                        + " – " + Qt.formatDate(root.dateOffset(root.weekStart(root.selectedDate), 6), "MMM d, yyyy")
                    : Qt.formatDate(root.selectedDate, "dddd, MMMM d, yyyy")
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSubtitle
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
            }
            Repeater {
                model: ["Day", "Week", "Month"]
                delegate: NavButton {
                    required property string modelData
                    objectName: "calendar" + modelData + "Button"
                    text: modelData
                    checkable: true
                    checked: root.viewMode === modelData
                    onClicked: root.viewMode = modelData
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.surface
            radius: Theme.radiusLarge
            border.color: Theme.border
            clip: true

            GridLayout {
                anchors.fill: parent
                anchors.margins: 16
                columns: root.viewMode === "Month" ? 2 : 1
                columnSpacing: 16
                rowSpacing: 8

                DayOfWeekRow {
                    visible: root.viewMode !== "Day"
                    Layout.row: 0
                    Layout.column: 0
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    locale: monthGrid.locale
                    delegate: Label {
                        required property string shortName
                        text: shortName
                        color: Theme.textSecondary
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                MonthGrid {
                    id: monthGrid
                    objectName: "monthGrid"
                    visible: root.viewMode === "Month"
                    Layout.row: 1
                    Layout.column: 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: parent.width * 0.57
                    month: root.selectedDate.getMonth()
                    year: root.selectedDate.getFullYear()
                    onClicked: function(day) { root.selectedDate = day; }

                    delegate: Rectangle {
                        id: dayCell
                        required property var model
                        readonly property var entries: root.entriesFor(model.date)
                        color: root.dateKey(model.date) === root.selectedKey ? Theme.surfaceHover : "transparent"
                        radius: Theme.radiusSmall
                        border.color: root.dateKey(model.date) === root.selectedKey ? Theme.primary : Theme.border
                        opacity: model.month === monthGrid.month ? 1 : 0.45
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 2
                            Label {
                                text: model.day
                                color: model.today ? Theme.primary : Theme.textPrimary
                                font.bold: model.today
                                font.pixelSize: Theme.fontSmall
                            }
                            Row {
                                spacing: 3
                                Repeater {
                                    model: Math.min(5, dayCell.entries.length)
                                    delegate: Rectangle {
                                        required property int index
                                        objectName: "calendarEntryDot"
                                        width: 6
                                        height: 6
                                        radius: 3
                                        color: index < dayCell.entries.length ? dayCell.entries[index].color : "transparent"
                                    }
                                }
                            }
                            Item { Layout.fillHeight: true }
                        }
                    }
                }

                RowLayout {
                    visible: root.viewMode === "Week"
                    Layout.row: 1
                    Layout.column: 0
                    Layout.fillWidth: true
                    spacing: 4
                    Repeater {
                        model: 7
                        delegate: ColumnLayout {
                            id: weekDay
                            required property int index
                            readonly property date day: root.dateOffset(root.weekStart(root.selectedDate), index)
                            readonly property var entries: root.entriesFor(day)
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: 1
                            Layout.alignment: Qt.AlignTop
                            spacing: 4
                            NavButton {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                checkable: true
                                checked: root.dateKey(weekDay.day) === root.selectedKey
                                text: Qt.formatDate(weekDay.day, "d")
                                Accessible.name: Qt.formatDate(weekDay.day, "dddd, MMMM d")
                                onClicked: root.selectedDate = weekDay.day
                            }
                            Repeater {
                                model: Math.min(3, weekDay.entries.length)
                                delegate: Label {
                                    required property int index
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    text: index < weekDay.entries.length ? weekDay.entries[index].title : ""
                                    color: index < weekDay.entries.length ? weekDay.entries[index].color : "transparent"
                                    font.pixelSize: Theme.fontSmall
                                    elide: Text.ElideRight
                                }
                            }
                            Label {
                                visible: weekDay.entries.length > 3
                                text: "+" + (weekDay.entries.length - 3) + " more"
                                color: Theme.textSecondary
                                font.pixelSize: Theme.fontSmall
                            }
                        }
                    }
                }

                Label {
                    objectName: "calendarSelectedDate"
                    Layout.row: root.viewMode === "Month" ? 0 : 2
                    Layout.column: root.viewMode === "Month" ? 1 : 0
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    elide: Text.ElideRight
                    text: Qt.formatDate(root.selectedDate, "dddd, MMMM d")
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    font.bold: true
                    Layout.topMargin: 4
                }

                ListView {
                    objectName: "calendarEntries"
                    Layout.row: root.viewMode === "Month" ? 1 : 3
                    Layout.column: root.viewMode === "Month" ? 1 : 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: root.viewMode === "Month" ? Math.min(360, parent.width * 0.43) : -1
                    Layout.maximumWidth: root.viewMode === "Month" ? 360 : Infinity
                    clip: true
                    spacing: 4
                    model: root.entriesFor(root.selectedDate)
                    ScrollBar.vertical: ScrollBar {}
                    delegate: ItemDelegate {
                        id: entry
                        objectName: "calendarEntry"
                        required property var modelData
                        width: ListView.view.width
                        height: 46
                        enabled: modelData.kind === "event" && !modelData.event.readOnly
                        onClicked: {
                            if (modelData.event.recurrence === "none")
                                eventDialog.openEdit(modelData.event, "series");
                            else {
                                editChoice.selectedEvent = modelData.event;
                                editChoice.open();
                            }
                        }
                        contentItem: RowLayout {
                            spacing: 10
                            Rectangle {
                                width: 4
                                Layout.fillHeight: true
                                radius: 2
                                color: entry.modelData.color
                            }
                            Label {
                                text: entry.modelData.time
                                color: Theme.textSecondary
                                font.pixelSize: Theme.fontSmall
                                Layout.preferredWidth: 90
                            }
                            Label {
                                text: entry.modelData.title
                                color: entry.modelData.completed ? Theme.textMuted : Theme.textPrimary
                                font.strikeout: entry.modelData.completed === true
                                font.pixelSize: Theme.fontBody
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Label {
                                text: entry.modelData.kind === "event" ? (entry.modelData.event.readOnly ? "Google · read-only" : "Edit") : "Task"
                                color: Theme.textSecondary
                                font.pixelSize: Theme.fontSmall
                            }
                        }
                        background: Rectangle {
                            radius: Theme.radiusSmall
                            color: entry.hovered && entry.enabled ? Theme.surfaceHover : Theme.inputBackground
                        }
                    }
                    Label {
                        anchors.centerIn: parent
                        visible: parent.count === 0
                        text: "No tasks or events for this day."
                        color: Theme.textMuted
                        font.pixelSize: Theme.fontBody
                    }
                }
            }
        }
    }
}
