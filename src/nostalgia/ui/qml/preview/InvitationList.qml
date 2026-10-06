import QtQuick

Column {
    id: root
    spacing: 12
    Repeater {
        model: socialBridge.invitations
        Glass {
            width: root.width
            implicitHeight: contents.implicitHeight + 32
            height: implicitHeight
            padding: 16
            Column {
                id: contents
                width: parent.width; spacing: 10
                Grid {
                    id: grid
                    width: parent.width
                    columns: width >= 620 * GlassTheme.scale ? 2 : 1
                    columnSpacing: 18; rowSpacing: 10
                    Column {
                        width: grid.columns === 2 ? grid.width - actions.width - 18 : grid.width
                        spacing: 8
                        PaymentText { width: parent.width; text: modelData.name + " mời bạn chơi"; font.weight: Font.DemiBold }
                        PaymentText { width: parent.width; text: modelData.world + " · Hiệu lực 5 phút"; color: GlassTheme.muted }
                    }
                    Flow {
                        id: actions
                        width: grid.columns === 2 ? 230 * GlassTheme.scale : grid.width
                        spacing: 10
                        Button { objectName: "acceptInvite-" + modelData.inviteId; label: "Vào phòng"; primary: true; clickable: !socialBridge.busy && !multiplayerBridge.active; onClicked: socialBridge.acceptInvite(modelData.inviteId) }
                        Button { label: "Từ chối"; quiet: true; clickable: !socialBridge.busy; onClicked: socialBridge.declineInvite(modelData.inviteId) }
                    }
                }
                PaymentText { visible: multiplayerBridge.active; width: parent.width; text: "Rời phòng hiện tại để nhận lời mời này."; color: GlassTheme.muted }
            }
        }
    }
}
