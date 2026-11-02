import QtQuick

Canvas {
    id: root
    property string decor: "sprout"
    property string kind: "frame"
    property real radius: 18
    readonly property bool aurora: decor === "aurora-drift"
    onDecorChanged: requestPaint()
    onKindChanged: requestPaint()
    onRadiusChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onVisibleChanged: if (visible) requestPaint()
    onAvailableChanged: if (available) requestPaint()

    function rounded(context, w, h, r) {
        context.beginPath();
        context.moveTo(r, 0); context.lineTo(w - r, 0);
        context.quadraticCurveTo(w, 0, w, r); context.lineTo(w, h - r);
        context.quadraticCurveTo(w, h, w - r, h); context.lineTo(r, h);
        context.quadraticCurveTo(0, h, 0, h - r); context.lineTo(0, r);
        context.quadraticCurveTo(0, 0, r, 0); context.closePath();
    }

    onPaint: {
        if (!visible || !available) return;
        var context = getContext("2d");
        context.clearRect(0, 0, width, height);
        context.save();
        if (kind === "frame") {
            var size = Math.min(width, height);
            context.translate(width / 2, height / 2);
            var gradient = context.createLinearGradient(-size / 2, -size / 2, size / 2, size / 2);
            gradient.addColorStop(0, aurora ? "#94f3ed" : "#c4e8b4");
            gradient.addColorStop(0.5, aurora ? "#9d8cf1" : "#568c6a");
            gradient.addColorStop(1, aurora ? "#e9b8f1" : "#b6dca2");
            context.strokeStyle = gradient;
            context.lineWidth = Math.max(2, size * 0.034);
            context.beginPath(); context.arc(0, 0, size * 0.39, 0, 2 * Math.PI); context.stroke();
            context.strokeStyle = aurora ? "#659dc9" : "#385f4b";
            context.lineWidth = Math.max(1, size * 0.012);
            context.beginPath(); context.arc(0, 0, size * 0.43, -0.7, 3.8); context.stroke();
            for (var i = 0; i < 3; ++i) {
                var x = -size * 0.26 + i * size * 0.075;
                var y = size * 0.30 + i * size * 0.025;
                context.fillStyle = aurora ? "#c6baff" : "#a5d28e";
                context.beginPath(); context.moveTo(x, y);
                context.bezierCurveTo(x - size * 0.09, y - size * 0.01, x - size * 0.08, y - size * 0.11, x + size * 0.015, y - size * 0.06);
                context.bezierCurveTo(x + size * 0.08, y - size * 0.02, x + size * 0.06, y + size * 0.03, x, y);
                context.fill();
            }
        } else {
            rounded(context, width, height, Math.min(radius, width / 2, height / 2));
            context.clip();
            var background = context.createLinearGradient(0, height, width, 0);
            background.addColorStop(0, aurora ? "#182a3c" : "#1b302b");
            background.addColorStop(0.5, aurora ? "#464774" : "#486b52");
            background.addColorStop(1, aurora ? "#624169" : "#99b383");
            context.fillStyle = background; context.fillRect(0, 0, width, height);
            for (var ribbon = 0; ribbon < 6; ++ribbon) {
                context.strokeStyle = aurora ? "#447bcfc7" : "#337fa06a";
                context.lineWidth = Math.max(2, height * 0.11);
                context.beginPath();
                context.moveTo(-width * 0.1, height * (0.35 + ribbon * 0.12));
                context.bezierCurveTo(width * 0.3, -height * 0.5, width * 0.65, height * 1.3, width * 1.15, height * (0.1 + ribbon * 0.1));
                context.stroke();
            }
            if (aurora) {
                context.fillStyle = "#bde5e8";
                for (var star = 0; star < 18; ++star) {
                    var sx = width * ((star * 37 % 97) / 100);
                    var sy = height * ((star * 19 % 83) / 100);
                    context.beginPath(); context.arc(sx, sy, star % 4 === 0 ? 1.5 : 0.7, 0, 2 * Math.PI); context.fill();
                }
            }
        }
        context.restore();
    }
}
