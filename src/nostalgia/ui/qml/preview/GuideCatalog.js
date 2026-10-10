.pragma library

// Nội dung tập trung để cập nhật hướng dẫn cùng lúc với từng luồng giao diện.
var topics = [
    {id: "start", title: "Tài khoản & bắt đầu", clip: "accounts",
     summary: "Google lưu hồ sơ launcher; tài khoản Minecraft dùng để vào game.",
     steps: ["Thêm tài khoản Minecraft: chọn Microsoft, Ely.by hoặc Ngoại tuyến.", "Với Microsoft/Google, hoàn tất đăng nhập trong trình duyệt rồi quay lại launcher. Ely.by dùng màn hình đăng nhập riêng.", "Chọn tài khoản Minecraft muốn chơi, sau đó tạo bản chơi hoặc cài modpack từ Thư viện.", "Bấm avatar ở góc dưới thanh bên để mở hồ sơ và đăng xuất Google."],
     tip: "Google không thay thế tài khoản Microsoft/Ely.by và không cấp quyền sở hữu Minecraft. Tài khoản ngoại tuyến có thể không vào được server yêu cầu xác thực."},
    {id: "create", title: "Tạo bản chơi", clip: "create",
     summary: "Chọn phiên bản và loader phù hợp trước khi tạo thế giới riêng.",
     steps: ["Mở Bản chơi → Tạo bản chơi.", "Tìm hoặc mở nhóm phiên bản Minecraft, rồi chọn bản phát hành cụ thể.", "Chọn Vanilla hoặc loader mà bộ mod yêu cầu; chọn phiên bản loader nếu có.", "Đặt tên, kiểm tra tóm tắt rồi bấm Tạo bản chơi. Bản chơi mới xuất hiện trong danh sách."],
     tip: "Forge, NeoForge, Fabric và Quilt không thay thế cho nhau. Với modpack có sẵn, nên cài từ Thư viện để lấy đúng phiên bản và loader của pack."},
    {id: "library", title: "Cài mod & modpack", clip: "library",
     summary: "Xem nội dung trước khi cài; chọn đúng bản chơi để tránh cài nhầm.",
     steps: ["Chọn loại nội dung: Modpack, Mod, Shader hoặc Gói tài nguyên.", "Từ Quản lý bản chơi → Nội dung đã cài → Thêm nội dung, thư viện lọc sẵn theo bản chơi đang mở.", "Tìm nội dung rồi bấm vào ô để xem thông tin và bản phát hành. Modpack ở thư viện chính tạo bản chơi riêng.", "Cài xong, quay lại quản lý để kiểm tra, bật/tắt hoặc gỡ nội dung. Thư viện mở từ quản lý giữ cố định bản chơi đích."],
     tip: "Shader cần nền tảng hỗ trợ shader phù hợp. Gói tài nguyên và shader đã tải vẫn cần được bật trong Minecraft. Chỉ cài nội dung từ nguồn bạn tin tưởng."},
    {id: "drop", title: "Kéo thả mod từ máy", clip: "drop",
     summary: "Thả file JAR vào bất kỳ trang hoặc popup nào rồi chọn bản chơi sẽ nhận mod.",
     steps: ["Kéo một hoặc nhiều file .jar từ trình quản lý file vào cửa sổ launcher.", "Ở popup Cài mod từ máy, chọn bản chơi muốn cài; chưa chọn thì chưa có file nào được chép.", "Mặc định bỏ qua file trùng tên. Chỉ bật Thay file trùng tên khi muốn cập nhật; bản cũ sẽ được giữ lại.", "Đóng game rồi bấm Cài vào bản chơi. Kiểm tra thông báo và mục Nội dung đã cài của bản chơi đó."],
     tip: "File gốc được giữ nguyên. Mods đang tắt vẫn giữ trạng thái tắt khi thay. Bạn cần đúng phiên bản/loader và nguồn tin tưởng; kéo thả không tự cài phụ thuộc hay loader cho Vanilla."},
    {id: "appearance", title: "Skin & cape", clip: "appearance",
     summary: "Thử skin, dáng tay và cape trên nhân vật 3D rồi mới lưu.",
     steps: ["Mở Tài khoản & skin, chọn tài khoản Minecraft sẽ nhận thay đổi.", "Thêm PNG hoặc bấm Xem trước trên một ô skin. Kéo nhân vật để xem các góc.", "Bật/tắt Classic/Slim để xem tay 4/3 px. Chuyển sang Cape để thử áo choàng đã sở hữu.", "Bấm Lưu thay đổi để áp dụng cho tài khoản đang chọn; Hủy thay đổi trở về diện mạo đã lưu."],
     tip: "Chọn skin không tự đổi skin trong game. Microsoft chỉ dùng cape đã sở hữu; Ely.by hiện xem cape đang mặc và thay cape tại ely.by."},
    {id: "friends", title: "Kết bạn & chat", clip: "friends",
     summary: "Đăng nhập Google để giữ bạn bè khi đổi máy.",
     steps: ["Mở Bạn bè và đăng nhập Google nếu chưa kết nối tài khoản launcher.", "Sao chép mã kết bạn của bạn, hoặc nhập mã của người muốn thêm.", "Chấp nhận yêu cầu kết bạn; chọn một người trong danh sách để chat.", "Bấm avatar để xem hồ sơ. Khi host đã mở phòng, gửi lời mời từ danh sách bạn bè."],
     tip: "Mã kết bạn là mã của tài khoản launcher. Đăng nhập Minecraft riêng vẫn cần thiết để khởi chạy game; trạng thái trực tuyến có thể cần ít giây để cập nhật."},
    {id: "host", title: "Mở phòng & chia sẻ", clip: "host",
     summary: "Chọn đúng bản chơi, nội dung chia sẻ và khởi chạy cùng một luồng.",
     steps: ["Đăng nhập Google và chọn tài khoản Minecraft; đóng game đang chạy trước khi host.", "Mở Bạn bè → Mở phòng, chọn bản chơi/modpack đã cài.", "Host có Plus trở lên có thể bật Đồng bộ modpack và chọn mods/pack muốn chia sẻ.", "Bấm Khởi chạy Minecraft. Vào thế giới và mở LAN trong Minecraft; khi phòng sẵn sàng, mời bạn ngay trong tab Chơi chung."],
     tip: "Bạn bè nhận lời mời không cần mua Plus để nhận pack từ host có quyền đồng bộ. Nếu bỏ mod bắt buộc, người nhận có thể không vào được phòng. Đừng chia sẻ nội dung bạn không có quyền phân phối."},
    {id: "invite", title: "Mời bạn vào world", clip: "host",
     summary: "Host mở LAN trước; bạn bè nhận lời mời ngay trong launcher.",
     steps: ["Host: mở Bạn bè → Mở phòng, chọn bản chơi rồi bấm Khởi chạy Minecraft.", "Trong Minecraft, tạo hoặc mở world → Esc → Open to LAN → Start LAN World. Để nguyên game đang chạy.", "Quay lại tab Chơi chung, chờ Phòng sẵn sàng và đồng bộ pack hoàn tất nếu có. Bấm Mời chơi bên cạnh người bạn trực tuyến.", "Người nhận: mở Bạn bè, bấm Vào phòng trên lời mời. Nếu có modpack, xem và đồng bộ nội dung trước khi chạy game.", "Người nhận: bấm Chép địa chỉ vào Minecraft, rồi vào Multiplayer → Direct Connection và dán địa chỉ. Bạn cũng có thể chọn thế giới LAN nếu thấy trong danh sách."],
     tip: "Hai người phải kết bạn và mở launcher, dùng Minecraft/mods tương thích. Lời mời có hiệu lực 5 phút. Host giữ world và launcher chạy; nhận pack từ host có Plus không yêu cầu người nhận mua Plus."},
    {id: "sync", title: "Nhận & cập nhật pack", clip: "sync",
     summary: "Kiểm tra nội dung host gửi và chọn những file sẽ cài trên máy bạn.",
     steps: ["Mở lời mời từ bạn bè để xem pack và nội dung host chia sẻ.", "Đọc cảnh báo; kiểm tra nguồn và bỏ chọn mods, texture pack hoặc shader không muốn nhận.", "Xác nhận đã hiểu rủi ro rồi đồng bộ. Lần đầu launcher tạo bản chơi riêng.", "Lần sau cùng pack được cập nhật vào bản chơi đã nhận. Kiểm tra nội dung mới trước khi áp dụng."],
     tip: "Mods và scripts có thể chạy mã trên máy bạn; chỉ nhận từ host tin tưởng. SHA-256 xác minh toàn vẹn, không chứng minh file an toàn. Pack mới của host không được coi là pack cũ để ghi đè."},
    {id: "server", title: "Tạo & quản lý server", clip: "server",
     summary: "Server chạy trên máy bạn; quyền Pro trở lên được kiểm tra tự động.",
     steps: ["Mở Bản chơi → Server, đăng nhập Google. Launcher tự kiểm tra quyền Pro, Max hoặc Ultimate.", "Bấm Tạo server, chọn nền tảng, phiên bản Minecraft và bản server.", "Mở Quản lý để chỉnh cấu hình, RAM và nội dung; lưu trước khi khởi chạy.", "Xem Console khi server chạy. Dừng & lưu thế giới trước khi chỉnh file hoặc xoá server."],
     tip: "Gói premium không kèm VPS. Bạn vẫn cần cấu hình kết nối mạng cho người khác vào server. Folia cần plugin hỗ trợ riêng; hybrid có thể cần kiểm tra tương thích bổ sung."},
    {id: "plugin", title: "Plugin & mod server", clip: "plugin",
     summary: "Nội dung server được lọc theo nền tảng và phiên bản đã chọn.",
     steps: ["Dừng server rồi mở Quản lý → Nội dung.", "Chọn Plugin hoặc Mod nếu nền tảng hỗ trợ. Danh sách khám phá được tải khi mở mục này.", "Tìm trên Modrinth hoặc Hangar, chọn dự án và bản phát hành tương thích trước khi cài.", "Kiểm tra phần Đã cài, rồi khởi chạy lại server và xem Console để xác nhận."],
     tip: "Vanilla không dùng plugin/mod. Mod chỉ dành cho client không nên cài vào server. Việc lọc phiên bản không đảm bảo mọi tổ hợp plugin, mod hoặc hybrid hoạt động cùng nhau."},
    {id: "backup", title: "Xuất modpack & dữ liệu", clip: "backup",
     summary: "Đóng gói MRPACK hoặc ZIP để chia sẻ và nhập lại trên máy khác.",
     steps: ["Dừng game, mở Bản chơi → Xuất modpack, hoặc Quản lý → Xuất & dữ liệu.", "Chọn bản chơi và định dạng MRPACK hoặc ZIP. Bật Đóng gói cả thế giới nếu muốn kèm saves.", "Bấm Xuất, chọn nơi lưu file. Để nhập lại, mở Nhập bản chơi và chọn file vừa xuất.", "Dữ liệu sao lưu/thùng rác trước đây nằm trong Khôi phục dữ liệu cũ; có thể khôi phục hoặc xóa hẳn từng bản chơi."],
     tip: "Xuất giữ bản chơi gốc và đúng Minecraft/loader. Xóa vĩnh viễn không qua thùng rác, không thể hoàn tác; thư mục game ngoài chỉ xóa khi bật Xóa cả thư mục game riêng và xác nhận đường dẫn."},
    {id: "import", title: "Nhập bản chơi", clip: "import",
     summary: "Đưa modpack hoặc bản chơi từ launcher khác vào Nostalgia.",
     steps: ["Mở Bản chơi → Nhập bản chơi.", "Ở File modpack, bấm Chọn file modpack và chọn .mrpack hoặc file .zip modpack được hỗ trợ.", "Hoặc chọn Launcher khác để quét các bản chơi trên máy, rồi bấm Nhập bản chơi.", "Chờ nhập xong và kiểm tra bản chơi mới trong danh sách trước khi mở game."],
     tip: "File ZIP bất kỳ không phải modpack hợp lệ. Chỉ nhập từ nguồn tin tưởng vì modpack có thể chứa mã thực thi. ZIP/MRPACK xuất từ Nostalgia có thể nhập ở đây."},
    {id: "repair", title: "Sửa lỗi từ log", clip: "repair",
     summary: "Chỉ tìm cách sửa khi log game có lỗi crash hoặc không tương thích rõ ràng.",
     steps: ["Chạy bản chơi gặp lỗi để có log, rồi dừng game.", "Mở quản lý bản chơi → Xuất & dữ liệu → Kiểm tra xung đột mod.", "Đọc lỗi và nguồn log. Với Plus, tìm bản phù hợp khi launcher xác định được yêu cầu phiên bản.", "Xem mod và bản thay thế, bấm Replace hoặc áp phương án; có bản trước sửa để Hoàn tác."],
     tip: "Không có lỗi được nhận diện trong log thì không tự đề xuất thay mod. Free xem lỗi; Plus sửa các trường hợp được hỗ trợ. Launcher không đảm bảo sửa được mọi nguyên nhân crash."},
    {id: "premium", title: "Mua & nâng cấp gói", clip: "premium",
     summary: "Premium gắn với Google; nút Đã chuyển khoản không tự cấp quyền.",
     steps: ["Đăng nhập Google, mở Premium và chọn gói phù hợp.", "Kiểm tra giá cuối cùng hoặc ưu đãi nâng cấp rồi tạo đơn.", "Chuyển đúng số tiền và nội dung riêng của đơn vào tài khoản hiện trên QR.", "Bấm Đã chuyển khoản để gửi yêu cầu kiểm tra. Chờ quản trị đối chiếu tiền vào và duyệt đơn."],
     tip: "Chỉ giao dịch thực nhận mới được duyệt. Plus 29.000đ/tháng; Pro 69.000đ/6 tháng; Max 109.000đ/năm; Ultimate 209.000đ/mua đứt. Ưu đãi nâng cấp lấy theo báo giá của đơn."},
    {id: "cosmetic", title: "Cosmetic & hồ sơ", clip: "cosmetic",
     summary: "Thử diện mạo trước, rồi sử dụng bộ đã mở khoá trên hồ sơ launcher.",
     steps: ["Mở Cosmetic trên thanh bên và đăng nhập Google.", "Chọn một bộ để xem avatar, khung và nền hồ sơ thay đổi trong bản xem thử.", "Với bộ đã mở khoá, bấm Sử dụng diện mạo để lưu.", "Bấm avatar của bạn ở thanh bên để mở và chỉnh hồ sơ."],
     tip: "Cosmetic hồ sơ launcher không phải skin/cape Minecraft và không tự hiện trong game. Các bộ chưa mở khoá vẫn có thể xem thử; quyền sử dụng được kiểm tra khi lưu."},
    {id: "settings", title: "Cài đặt giao diện", clip: "settings",
     summary: "Chỉnh cỡ chữ, chuyển động và nền cho phù hợp với máy bạn.",
     steps: ["Mở Cài đặt → Giao diện.", "Chọn tỉ lệ giao diện và ngôn ngữ dễ đọc.", "Bật Giảm chuyển động nếu muốn hạn chế animation và quán tính.", "Tắt nền trang trí hoặc âm thanh nếu muốn trải nghiệm nhẹ và yên tĩnh hơn."],
     tip: "Hướng dẫn vẫn đọc được khi giảm chuyển động: GIF dừng ở ảnh tĩnh. GIF được đóng gói trong launcher, không cần tải từ dịch vụ ngoài."},
    {id: "log", title: "Đọc nhật ký game", clip: "log",
     summary: "Xem lỗi thật từ game và sao chép log để gửi khi cần hỗ trợ.",
     steps: ["Khởi chạy bản chơi rồi mở Nhật ký để xem log game đang chạy.", "Chọn Tất cả, Cảnh báo+ hoặc Lỗi để lọc mức thông báo.", "Cuộn lên để đọc dòng cũ; launcher tạm ngừng bám dòng mới. Cuộn về cuối để tiếp tục theo dõi.", "Bấm Sao chép để lấy log. Khi game crash, dùng Sửa lỗi từ log trong quản lý bản chơi."],
     tip: "Một dòng WARN/ERROR không tự chứng minh mod bị lỗi. Đọc ngữ cảnh và thông báo crash; kiểm tra thông tin riêng tư trước khi chia sẻ log cho người khác."}
];

function find(topicId, translator) {
    var topic = topics.find(function(topic) { return topic.id === topicId; }) || topics[0];
    if (!translator) return topic;
    return {id: topic.id, clip: topic.clip, title: translator.phrase(topic.title),
            summary: translator.phrase(topic.summary), tip: translator.phrase(topic.tip),
            steps: topic.steps.map(function(step) { return translator.phrase(step); })};
}

function pageTopic(index) {
    return ["start", "create", "library", "appearance", "friends", "log", "settings", "cosmetic"][index] || "start";
}

function normalized(text) {
    return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").trim();
}

function matches(topic, query) {
    return normalized(topic.title + " " + topic.summary + " " + topic.steps.join(" ")).indexOf(normalized(query)) >= 0;
}
