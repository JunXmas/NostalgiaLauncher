import QtQuick
import QtQuick.Controls as Controls
import "../" as Legacy
Item {
    id: root; objectName: "marketplacePage"
    property var details: marketBridge.details
    property int tab: 0
    property var selected: ({})
    property bool walletRequested: false
    property bool usePoints: false
    function ownedCount(product) { var items=product.product_kind==="bundle" ? product.members : [product];var total=0;for(var i=0;i<items.length;i++)for(var j=0;j<details.owned.length;j++)if(items[i].product_id===details.owned[j].product_id)total++;return total; }
    function previewHashes(product) { return product.product_kind==="bundle" ? product.members.map(function(item){return item.asset_hash;}).join(",") : (product.asset_hash||""); }
    property string previewAccountId: bridge.activeAccountId
    readonly property var previewAccount: {
        var accounts=accountBridge.accounts;
        for(var i=0;i<accounts.length;i++)if(accounts[i].accountId===previewAccountId)return accounts[i];
        return accounts.length ? accounts[0] : ({});
    }
    signal navigate(int index)
    function wallet() { if (!walletRequested && details.enabled && socialBridge.signedIn && !marketBridge.busy) { walletRequested=true; marketBridge.refreshWallet(); } }
    Component.onCompleted: marketBridge.refresh()
    Connections { target: marketBridge; function onBusyChanged() { if(!marketBridge.busy)Qt.callLater(root.wallet); } }
    Connections { target: socialBridge; function onSessionChanged() { root.walletRequested=false;root.usePoints=false; } function onChanged() { root.wallet(); } }
    Connections { target: marketBridge; function onChanged() {
        if(!root.selected.product_id && root.details.products.length)root.selected=root.details.products[0];
        if(root.details.quote.quote_id)checkout.open();else checkout.close();
    } }
    InertialScroll { anchors.fill: parent; contentHeight: body.implicitHeight+24
        Column { id: body; width: parent.width-10; spacing: 20
            Flow { width: parent.width; spacing: 16
                Column { width: Math.max(230,parent.width-240); spacing: 7
                    PaymentText { text: "Marketplace"; font.family: GlassTheme.displayFont; font.pixelSize: GlassTheme.fontPage; font.weight: Font.DemiBold }
                    PaymentText { width: parent.width; text: Legacy.Tr.phrase("Mặc thử trên nhân vật của bạn. Chọn diện mạo theo cách riêng."); color: GlassTheme.muted; wrapMode: Text.WordWrap }
                }
                Button { objectName: "marketBalance"; label: (socialBridge.signedIn ? root.details.balance : "—")+" coin"; quiet: true; onClicked: { root.tab=1;marketBridge.refreshOrders(); } }
                Button { label: Legacy.Tr.phrase("Làm mới"); quiet: true; clickable: !marketBridge.busy; onClicked: { root.walletRequested=false;marketBridge.refresh(); } }
            }
            MotionTabs { width: parent.width; labels: [Legacy.Tr.phrase("Cửa hàng"),Legacy.Tr.phrase("Nạp coin"),Legacy.Tr.phrase("Tủ đồ")]; currentIndex: root.tab; namePrefix: "marketTab-"; onSelected: function(index) { root.tab=index;if(index===1)marketBridge.refreshOrders();else if(index===2)marketBridge.refreshWallet(); } }
            Glass { padding: 0; visible: !root.details.enabled; width: parent.width; height: unavailable.implicitHeight+32
                PaymentText { id: unavailable; x: 16; y: 16; width: parent.width-32; text: Legacy.Tr.phrase("Marketplace chưa mở bán. Chơi game và các tính năng hiện tại vẫn hoạt động bình thường."); wrapMode: Text.WordWrap; color: GlassTheme.muted }
            }
            ServiceAccountCard { width: parent.width; visible: !socialBridge.signedIn }
            PaymentText { width: parent.width; visible: !!root.details.note; text: Legacy.Tr.message(root.details.note); wrapMode: Text.WordWrap; color: GlassTheme.accent }
            Item { width: parent.width; visible: root.tab===0; height: root.tab===0 ? Math.max(store.implicitHeight,preview.implicitHeight)+(width<850 ? store.implicitHeight+20 : 0) : 0
                MarketStore { id: store; width: parent.width<850 ? parent.width : parent.width*0.50; products: root.details.products; selectedId: root.selected.product_id || ""; onChosen: function(product) { root.selected=product; } }
                Column { id: preview; x: parent.width<850 ? 0 : parent.width*0.54; y: parent.width<850 ? store.implicitHeight+20 : 0; width: parent.width<850 ? parent.width : parent.width*0.46; spacing: 12
                    Flow { width: parent.width; spacing: 6
                        Repeater { model: accountBridge.accounts; delegate: Button { required property var modelData; label: modelData.playerName; quiet: true; selected: root.previewAccount.accountId===modelData.accountId; onClicked: root.previewAccountId=modelData.accountId } }
                    }
                    MarketFigure { width: parent.width; height: 340*GlassTheme.scale; skinSource: root.previewAccount.skinFile || ""; slim: root.previewAccount.slim || false; digest: root.previewHashes(root.selected) }
                    PaymentText { width: parent.width; text: root.selected.product_id ? (Legacy.Tr.currentLanguage==="vi" ? root.selected.name_vi : root.selected.name_en) : Legacy.Tr.phrase("Nhân vật của bạn"); font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
                    PaymentText { width: parent.width; text: root.selected.product_id ? (Legacy.Tr.currentLanguage==="vi" ? root.selected.description_vi : root.selected.description_en) : ""; wrapMode: Text.WordWrap; color: GlassTheme.muted }
                    PaymentText { width: parent.width; text: Legacy.Tr.phrase("Hiển thị cho người dùng Nos Client tương thích trong phòng chơi do Nos host. Chưa hỗ trợ vanilla, Horizon hoặc server offline tùy ý."); wrapMode: Text.WordWrap; color: GlassTheme.muted; font.pixelSize: GlassTheme.fontCaption }
                    PaymentText { width: parent.width; visible: root.selected.product_kind==="bundle"; text: Legacy.Tr.phrase("Bộ gồm")+": "+(root.selected.members||[]).map(function(item){return Legacy.Tr.currentLanguage==="vi"?item.name_vi:item.name_en;}).join(", ")+"\n"+Legacy.Tr.phrase("Đã sở hữu")+": "+root.ownedCount(root.selected)+" / "+(root.selected.members||[]).length; wrapMode: Text.WordWrap; color: GlassTheme.muted }
                    Controls.CheckBox { objectName: "marketUsePoints"; visible: !!root.details.rewards.member && root.details.rewards.balance>0; text: Legacy.Tr.phrase("Dùng điểm thưởng để giảm một phần giá"); checked: root.usePoints; enabled: !marketBridge.busy; onToggled: root.usePoints=checked; palette.windowText: GlassTheme.text; font.family: GlassTheme.font; font.pixelSize: GlassTheme.fontControl }
                    Button { objectName: "marketBuy"; label: root.selected.product_id && root.ownedCount(root.selected)===(root.selected.product_kind==="bundle" ? root.selected.members.length : 1) ? Legacy.Tr.phrase("Đã sở hữu") : Legacy.Tr.phrase("Xem giá và mua"); primary: true; clickable: root.details.enabled && socialBridge.signedIn && !!root.selected.product_id && root.ownedCount(root.selected)<(root.selected.product_kind==="bundle"?root.selected.members.length:1) && !marketBridge.busy; onClicked: marketBridge.quote(root.selected.product_id,root.usePoints) }
                    PaymentText { width: parent.width; visible: !!marketPreviews.note; text: Legacy.Tr.message(marketPreviews.note); wrapMode: Text.WordWrap; color: GlassTheme.muted }
                }
            }
            MarketRewards { visible: root.tab===1; width: parent.width; rewards: root.details.rewards; marketEnabled: root.details.enabled }
            MarketWallet { visible: root.tab===1; width: parent.width; details: root.details }
            Column { visible: root.tab===2; width: parent.width; spacing: 14
                PaymentText { text: Legacy.Tr.phrase("Tủ đồ"); font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
                PaymentText { visible: !root.details.owned.length; width: parent.width; text: Legacy.Tr.phrase("Chưa có cosmetic trong game. Bạn có thể mặc thử tại Cửa hàng."); color: GlassTheme.muted; wrapMode: Text.WordWrap }
                Repeater { model: root.details.owned; delegate: Glass { padding: 0; required property var modelData; width: body.width; height: 88
                    PaymentText { x: 16; anchors.verticalCenter: parent.verticalCenter; width: parent.width-180; text: Legacy.Tr.currentLanguage==="vi" ? modelData.name_vi : modelData.name_en; elide: Text.ElideRight }
                    Button { anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; label: modelData.equipped_slot ? Legacy.Tr.phrase("Bỏ trang bị") : Legacy.Tr.phrase("Trang bị"); clickable: !marketBridge.busy; onClicked: marketBridge.equip(modelData.equipped_slot ? "" : modelData.instance_id,modelData.slot) }
                } }
                Button { label: Legacy.Tr.phrase("Trang trí hồ sơ"); quiet: true; onClicked: root.navigate(7) }
            }
        }
    }
    Controls.Popup { id: checkout; objectName: "marketCheckout"; parent: Controls.Overlay.overlay; width: Math.min(430,parent.width-40); x: (parent.width-width)/2; y: (parent.height-height)/2; padding: 24; modal: true; focus: true; closePolicy: marketBridge.busy ? Controls.Popup.NoAutoClose : Controls.Popup.CloseOnEscape
        onClosed: marketBridge.cancelQuote()
        background: PopupGlass {}
        contentItem: Column { spacing: 16
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Xác nhận mua cosmetic"); wrapMode: Text.WordWrap; font.pixelSize: GlassTheme.fontSection }
            PaymentText { width: parent.width; text: Legacy.Tr.phrase("Giá phần chưa sở hữu")+": "+(root.details.quote.base_price || 0)+" coin\n"+Legacy.Tr.phrase("Điểm thưởng sử dụng")+": "+(root.details.quote.reward_points || 0)+"\n"+Legacy.Tr.phrase("Coin thanh toán")+": "+(root.details.quote.price || 0)+" coin\n"+Legacy.Tr.phrase("Số dư sau mua")+": "+(root.details.balance-(root.details.quote.price || 0))+" coin"; wrapMode: Text.WordWrap }
            PaymentText { width: parent.width; visible: !!root.details.note; text: Legacy.Tr.message(root.details.note); wrapMode: Text.WordWrap; color: GlassTheme.muted }
            Flow { width: parent.width; spacing: 10
                Button { label: Legacy.Tr.phrase("Hủy"); clickable: !marketBridge.busy; onClicked: checkout.close() }
                Button { objectName: "marketConfirmBuy"; label: Legacy.Tr.phrase("Xác nhận mua"); primary: true; clickable: !marketBridge.busy && root.details.balance >= (root.details.quote.price || 0); onClicked: marketBridge.buy() }
            }
        }
    }
}
