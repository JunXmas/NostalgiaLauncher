pragma Singleton
import QtQuick

/* Nhà cung cấp bản dịch: đọc từ điển JSON, cho phép chuyển ngôn ngữ tức thì mà không cần
   restart. Các file QML dùng `Tr.text("key")` thay cho chuỗi cứng. */
QtObject {
    id: root

    readonly property string currentLanguage: _lang
    property string _lang: "vi"
    property var _dict: ({})

    signal languageChanged()

    function text(key) {
        return _dict[key] !== undefined ? _dict[key] : key;
    }

    function setLanguage(lang) {
        if (lang === _lang) return;
        _lang = lang;
        _load(lang);
    }

    function _load(lang) {
        var xhr = new XMLHttpRequest();
        var url = Qt.resolvedUrl("i18n/" + lang + ".json");
        xhr.open("GET", url, false);  // đồng bộ: file nội bộ, <1 KB
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
        languageChanged();
    }

    Component.onCompleted: _load(_lang)
}
