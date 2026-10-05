import QtQuick

/* Mã phòng 18 ký tự nhập qua ba ô × 6. Gõ đủ 6 tự nhảy ô sau; Backspace ở ô rỗng lùi về ô
   trước; dán cả chuỗi (có gạch, khoảng trắng, chữ thường) vào ô nào cũng tự chia. Mỗi ký tự
   hiện ra bằng một cú lật như xúc xắc thay vì hiện đùng một phát.
   `code` là 18 ký tự nối lại, `complete` khi đủ. Luật mã không đổi (docs/MULTIPLAYER_SECURITY.md). */
Row {
    id: root
    readonly property string code: boxes.map(function (box) { return box.text; }).join("")
    readonly property bool complete: code.length === 18
    readonly property int groupLength: 6
    readonly property var boxes: [firstBox, secondBox, thirdBox]
    signal submitted()

    spacing: 8

    function clear() {
        for (var i = 0; i < boxes.length; i++) boxes[i].text = "";
        firstBox.focusInput();
    }
    function setCode(text) { pour(0, normalise(text)); }
    function normalise(text) { return String(text).toUpperCase().replace(/[^A-Z0-9]/g, ""); }

    // Đổ `text` từ ô `start`, phần dư chảy sang các ô sau, rồi đưa con trỏ tới ô đầu tiên còn trống.
    function pour(start, text) {
        for (var i = start; i < boxes.length; i++) {
            boxes[i].text = text.slice(0, groupLength);
            text = text.slice(groupLength);
            if (text.length === 0) break;
        }
        var open = boxes.findIndex(function (box, j) { return j >= start && box.text.length < root.groupLength; });
        boxes[open >= 0 ? open : boxes.length - 1].focusInput();
    }

    // Gọi mỗi khi một ô đổi chữ: viết hoa, bỏ ký tự lạ, chia phần dư, nhảy ô khi đủ.
    property bool pouring: false
    function digest(position) {
        if (root.pouring) return;
        var box = boxes[position];
        var clean = normalise(box.text);
        root.pouring = true;
        if (clean !== box.text || clean.length > groupLength) {
            box.text = clean.slice(0, groupLength);
            if (clean.length > groupLength && position + 1 < boxes.length) pour(position + 1, clean.slice(groupLength));
        }
        root.pouring = false;
        if (box.text.length === groupLength && position + 1 < boxes.length && box.focused)
            boxes[position + 1].focusInput();
    }

    // Backspace ở ô rỗng: lùi về ô trước và xoá ký tự cuối của nó. TextInput nuốt Backspace
    // nên phải bắt ngay tại ô, không bắt được ở Row cha.
    function backspace(position, event) {
        if (event.key !== Qt.Key_Backspace || position === 0 || boxes[position].text.length > 0) return;
        var previous = boxes[position - 1];
        previous.text = previous.text.slice(0, -1);
        previous.focusInput();
        event.accepted = true;
    }

    RoomCodeBox { id: firstBox;  objectName: "roomCodeBox0"; position: 0 }
    RoomCodeBox { id: secondBox; objectName: "roomCodeBox1"; position: 1 }
    RoomCodeBox { id: thirdBox;  objectName: "roomCodeBox2"; position: 2 }
}
