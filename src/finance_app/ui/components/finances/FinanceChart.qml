import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

import "../../themes"

Rectangle {
    id: root
    objectName: "financeChartPanel" + chartKind
    required property string title
    required property string chartKind
    property var chartData: []
    property bool expected: false
    color: Theme.surface
    radius: Theme.radiusLarge
    border.color: Theme.border
    implicitHeight: 290
    onChartDataChanged: canvas.requestPaint()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8
        Label { text: root.title; color: Theme.textPrimary; font.pixelSize: Theme.fontBody; font.bold: true; Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.Wrap }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Canvas {
                id: canvas
                objectName: "financeChart" + root.chartKind
                Accessible.name: root.title
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 120
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx = getContext("2d");
                    ctx.reset();
                    const rows = root.chartData || [];
                    const w = width, h = height;
                    ctx.font = "10px sans-serif";
                    ctx.fillStyle = "#949BA8";
                    if (!rows.length) {
                        ctx.fillText("No data for this period", 10, h / 2);
                        return;
                    }
                    if (root.chartKind === "pie") {
                        let total = 0;
                        for (const row of rows) total += row.value;
                        if (!total) return;
                        let angle = -Math.PI / 2;
                        const radius = Math.max(0, Math.min(w, h) / 2 - 8);
                        for (const row of rows) {
                            const end = angle + row.value / total * Math.PI * 2;
                            ctx.beginPath();
                            ctx.moveTo(w / 2, h / 2);
                            ctx.arc(w / 2, h / 2, radius, angle, end);
                            ctx.closePath();
                            ctx.fillStyle = row.color;
                            ctx.fill();
                            angle = end;
                        }
                        return;
                    }
                    const left = 60, right = Math.max(left + 1, w - 6), top = 14, bottom = Math.max(top + 1, h - 26);
                    let low = 0, high = 0;
                    for (const row of rows) {
                        high = Math.max(high, row.income, row.expense);
                        if (root.chartKind === "line") {
                            high = Math.max(high, row.balance);
                            low = Math.min(low, row.balance);
                        }
                    }
                    if (high === low) high = low + 100;
                    function y(value) { return bottom - (value - low) / (high - low) * (bottom - top); }
                    function money(value) {
                        const amount = Math.abs(value / 100);
                        return (value < 0 ? "-$" : "$") + (amount >= 1000 ? (amount / 1000).toFixed(1) + "k" : amount.toFixed(0));
                    }
                    ctx.strokeStyle = "#303540";
                    ctx.fillStyle = "#949BA8";
                    for (let i = 0; i <= 2; i++) {
                        const value = low + (high - low) * i / 2;
                        const position = y(value);
                        ctx.beginPath(); ctx.moveTo(left, position); ctx.lineTo(right, position); ctx.stroke();
                        ctx.fillText(money(value), 2, position + 3);
                    }
                    const step = (right - left) / rows.length;
                    if (root.chartKind === "bar") {
                        const barWidth = Math.max(1, Math.min(12, step * 0.34));
                        for (let i = 0; i < rows.length; i++) {
                            const x = left + (i + 0.5) * step;
                            ctx.fillStyle = "#62C6A0";
                            ctx.fillRect(x - barWidth, y(rows[i].income), barWidth, bottom - y(rows[i].income));
                            ctx.fillStyle = "#F07878";
                            ctx.fillRect(x, y(rows[i].expense), barWidth, bottom - y(rows[i].expense));
                        }
                    } else {
                        for (const series of [{key: "income", color: "#62C6A0"}, {key: "expense", color: "#F07878"}, {key: "balance", color: "#7395F5"}]) {
                            ctx.beginPath();
                            ctx.strokeStyle = series.color;
                            ctx.lineWidth = 2;
                            for (let i = 0; i < rows.length; i++) {
                                const x = left + (i + 0.5) * step;
                                if (i === 0) ctx.moveTo(x, y(rows[i][series.key]));
                                else ctx.lineTo(x, y(rows[i][series.key]));
                            }
                            ctx.stroke();
                        }
                    }
                    ctx.fillStyle = "#949BA8";
                    const interval = Math.max(1, Math.ceil(rows.length / 6));
                    for (let i = 0; i < rows.length; i += interval)
                        ctx.fillText(rows[i].label, left + i * step, h - 5);
                }
            }
            ListView {
                visible: root.chartKind === "pie"
                Layout.preferredWidth: 140
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: root.chartKind === "pie" ? root.chartData : []
                ScrollBar.vertical: ScrollBar {}
                delegate: Item {
                    id: legendItem
                    required property var modelData
                    width: ListView.view.width
                    height: 20
                    RowLayout {
                        anchors.fill: parent
                        spacing: 5
                        Rectangle { width: 8; height: 8; radius: 4; color: legendItem.modelData.color }
                        Label { text: legendItem.modelData.name + " " + legendItem.modelData.amount; textFormat: Text.PlainText; color: Theme.textSecondary; font.pixelSize: Theme.fontSmall; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                    }
                }
            }
        }
        Label {
            visible: root.chartKind !== "pie"
            text: root.chartKind === "bar" ? "Income (green)   Expenses (red)"
                : root.expected ? "Recorded income (green)   Recorded + expected expenses (red)   Recorded net balance (blue)"
                : "Cumulative income (green)   Expenses (red)   Net balance (blue)"
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
