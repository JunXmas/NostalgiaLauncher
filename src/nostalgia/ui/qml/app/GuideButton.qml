import QtQuick
import "../" as Legacy
import "GuideCatalog.js" as Guides

Button {
    id: helpButton
    property string topicId: "start"
    objectName: "guideButton-" + topicId
    label: Legacy.Tr.phrase("Cách dùng")
    quiet: true
    Accessible.name: Legacy.Tr.phrase("Hướng dẫn ") + Guides.find(topicId, Legacy.Tr).title
    onClicked: GuideCenter.show(topicId, helpButton)
}
