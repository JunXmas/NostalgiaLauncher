pragma Singleton
import QtQuick

// Local catalogs only; bindings re-evaluate when the dictionary changes.
QtObject {
    id: root

    readonly property string currentLanguage: _lang
    readonly property string localeName: _lang === "en" ? "en_US" : "vi_VN"
    property string _lang: "vi"
    property var _dict: ({})
    property var _patterns: []
    property var _cache: ({})

    signal languageChanged()

    function text(key) {
        return _dict[key] !== undefined ? _dict[key] : key;
    }

    function phrase(source) {
        if (source === undefined || source === null) return "";
        return _dict["p:" + source] !== undefined ? _dict["p:" + source] : source;
    }
    function message(source, depth) {
        // Only known launcher messages are translated. Unknown service/game text stays intact.
        var dictionary = _dict;
        if (!source) return "";
        source = String(source);
        if (dictionary["p:" + source] !== undefined) return dictionary["p:" + source];
        if (_cache[source] !== undefined) return _cache[source];
        for (var i = 0; i < _patterns.length; ++i) {
            var pattern = _patterns[i];
            var match = pattern.regex.exec(source);
            if (!match) continue;
            var translated = pattern.target.replace(/\{(\d+)\}/g, function(token, position) {
                var value = match[pattern.positions.indexOf(position) + 1];
                return pattern.nested && (depth || 0) < 3 ? message(value, (depth || 0) + 1) : value;
            });
            if (Object.keys(_cache).length >= 256)
                Object.keys(_cache).forEach(function(key) { delete _cache[key]; });
            _cache[source] = translated;
            return translated;
        }
        return source;
    }
    function format(source, values) {
        return phrase(source).replace(/%([1-9]\d*)/g, function(token, position) {
            return values[Number(position) - 1] !== undefined ? values[Number(position) - 1] : token;
        });
    }
    function plural(source, count) {
        return count === 1 && _dict["s:" + source] !== undefined ? _dict["s:" + source] : phrase(source);
    }
    function _compile(dictionary) {
        var patterns = [];
        Object.keys(dictionary).forEach(function(key) {
            if (key.indexOf("m:") !== 0) return;
            var source = key.slice(2), positions = [];
            var escaped = source.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            escaped = escaped.replace(/\\\{(\d+)\\\}/g, function(token, position) {
                positions.push(position); return "([\\s\\S]*?)";
            });
            patterns.push({regex: new RegExp("^" + escaped + "$"), positions: positions,
                           nested: source.indexOf("lỗi không lường trước:") === 0 || source.indexOf("Unexpected error:") === 0,
                           target: dictionary[key], weight: source.replace(/\{\d+\}/g, "").length});
        });
        return patterns.sort(function(a, b) { return b.weight - a.weight; });
    }
    function setLanguage(lang) {
        lang = lang === "en" ? "en" : "vi";
        if (lang === _lang) return;
        _lang = lang;
        _load(lang);
    }

    function _load(lang) {
        var xhr = new XMLHttpRequest();
        var url = Qt.resolvedUrl("i18n/" + lang + ".json");
        xhr.open("GET", url, false);  // Bundled file; never a network request.
        xhr.send();
        if (xhr.status === 200 || xhr.status === 0) {
            try {
                _dict = JSON.parse(xhr.responseText);
            } catch (e) {
                console.warn("TranslationProvider: parse error for", lang, e);
                _dict = {};
            }
        } else {
            console.warn("TranslationProvider: failed to load", url, xhr.status);
            _dict = {};
        }
        _patterns = _compile(_dict);
        _cache = ({});
        languageChanged();
    }

    Component.onCompleted: _load(_lang)
}
