import QtQuick
import "../" as Legacy
Column {
    id: root
    property var details: ({})
    width: parent.width; spacing: 16
    PaymentText { text: Legacy.Tr.phrase("Nạp coin"); font.pixelSize: GlassTheme.fontSection; font.weight: Font.DemiBold }
    PaymentText { width: parent.width; text: Legacy.Tr.phrase("Chọn gói để tạo đơn VietQR. Coin chỉ được cộng sau khi tiền thật đã được đối soát."); color: GlassTheme.muted; wrapMode: Text.WordWrap }
    Flow { width: parent.width; spacing: 12
        Repeater { model: root.details.coinOffers || []
            delegate: Button { required property var modelData; objectName: "coinOffer-"+modelData.offer_id; label: modelData.coins+" coin · "+Number(modelData.amount).toLocaleString(Qt.locale(Legacy.Tr.localeName),"f",0)+" VND"; clickable: socialBridge.signedIn && !marketBridge.busy && root.details.enabled; onClicked: marketBridge.topup(modelData.offer_id) }
        }
    }
    Button { label: Legacy.Tr.phrase("Làm mới đơn và số dư"); clickable: socialBridge.signedIn && !marketBridge.busy; onClicked: marketBridge.refreshOrders() }
    Repeater { model: root.details.orders || []
        delegate: Glass { padding: 0;
            required property var modelData
            width: root.width; height: orderColumn.implicitHeight+32
            Column { id: orderColumn; x: 16; y: 16; width: parent.width-32; spacing: 10
                PaymentText { width: parent.width; text: modelData.coins+" coin · "+modelData.amount+" VND · "+Legacy.Tr.phrase(modelData.status); font.weight: Font.DemiBold }
                PaymentText { width: parent.width; text: "Vietcombank · "+modelData.bank_account+"\n"+modelData.bank_holder+"\n"+Legacy.Tr.phrase("Nội dung chuyển khoản")+": "+modelData.memo; wrapMode: Text.WordWrap }
                Image { visible: !!modelData.qr_image; source: modelData.qr_image || ""; width: 220; height: 220; fillMode: Image.PreserveAspectFit; smooth: false; Accessible.name: Legacy.Tr.phrase("Mã QR chuyển khoản") }
                Button { label: Legacy.Tr.phrase("Tôi đã chuyển khoản"); visible: modelData.status === "pending"; clickable: !marketBridge.busy; onClicked: marketBridge.submitTopup(modelData.order_id) }
                PaymentText { width: parent.width; visible: modelData.status === "submitted"; text: Legacy.Tr.phrase("Đang chờ đối soát. Chưa cộng coin."); color: GlassTheme.muted }
            }
        }
    }
}
