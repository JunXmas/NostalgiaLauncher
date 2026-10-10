.pragma library

function normalize(text) {
    return String(text || "").toLowerCase().normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").trim();
}

function filter(friends, query) {
    var needle = normalize(query);
    return needle ? friends.filter(function(friend) {
        return normalize(friend.name).indexOf(needle) >= 0;
    }) : friends;
}
