import QtQuick
import "GuideCatalog.js" as Guides

Button {
    id: helpButton
    property string topicId: "start"
    objectName: "guideButton-" + topicId
    label: "Cách dùng"
    quiet: true
    Accessible.name: "Hướng dẫn " + Guides.find(topicId).title
    onClicked: GuideCenter.show(topicId, helpButton)
}
