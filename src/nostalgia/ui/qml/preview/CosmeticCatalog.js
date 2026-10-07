.pragma library

// Keep the existing service IDs so saved profiles remain compatible.
var sets = [
    {key: "amethyst", name: "Amethyst", artwork: "amethyst", tint: "#b79bdc", description: "Sắc tím thạch anh"},
    {key: "emerald", name: "Grove", artwork: "grove", tint: "#80ad86", description: "Khoảng xanh yên bình"},
    {key: "amber", name: "Eclipse", artwork: "eclipse", tint: "#d8b972", description: "Ánh vàng giữa trời đêm"}
];

function find(key) {
    for (var i = 0; i < sets.length; ++i)
        if (sets[i].key === key) return sets[i];
    return null;
}

function name(key) {
    var set = find(key);
    return set ? set.name : "Nguyên bản";
}

function asset(key, kind) {
    var set = find(key);
    return set ? Qt.resolvedUrl("../assets/cosmetics/" + set.artwork + "-" + kind + ".png") : "";
}
