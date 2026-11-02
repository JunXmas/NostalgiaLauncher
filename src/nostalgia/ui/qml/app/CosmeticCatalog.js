.pragma library

// Danh mục do bridge đọc từ JSON; JS chỉ phân giải dữ liệu đã kiểm tra.
function find(key, sets) {
    for (var i = 0; i < sets.length; ++i)
        if (sets[i].key === key && sets[i].state !== "disabled") return sets[i];
    return null;
}

function available(sets) {
    return sets.filter(function(set) { return set.state === "active"; });
}

function name(key, sets) {
    var set = find(key, sets);
    return set ? set.name : "Nguyên bản";
}

function asset(key, kind, sets) {
    var set = find(key, sets);
    return set && (kind === "frame" || kind === "banner") ? Qt.resolvedUrl("../assets/cosmetics/" + set.artwork + "-" + kind + ".png") : "";
}
