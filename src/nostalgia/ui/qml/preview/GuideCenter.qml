pragma Singleton
import QtQuick

QtObject {
    signal requested(string topicId, var opener)
    function show(topicId, opener) { requested(topicId, opener || null); }
}
