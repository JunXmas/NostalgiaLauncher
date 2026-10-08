# Key art trong cửa sổ tạo bản chơi

- Dùng lại ảnh Mojang trong `qml/assets/keyart`; không tạo ảnh thay thế. Ảnh đổi theo
  dòng của phiên bản đang chọn, giữ tỷ lệ 2,56:1 và không cắt thêm nội dung.
- Hai khu vực ở cửa sổ rộng: key art/bản phát hành bên trái; nền tảng, loader, tên và
  thiết lập nâng cao bên phải. Ở cửa sổ hẹp, các khu vực xếp dọc; ảnh và selector có
  thể nằm cạnh nhau để tiết kiệm chiều cao.
- Chân cửa sổ cố định có phiên bản đang chọn, Huỷ và Tạo bản chơi. Form giữ cuộn
  quán tính và selector tìm kiếm có chiều cao giới hạn; không bung thành danh sách
  ảnh/phiên bản dài như trước.
- Chưa chọn phiên bản có nhãn xem trước; ảnh của bản cũ hoặc dòng chưa có artwork
  dùng key art Java Edition hiện có. Không thay đổi lựa chọn hoặc đường cài game.
- Ảnh tải bất đồng bộ, dùng cache, giải mã tối đa 1024 px và bỏ nguồn khi popup ẩn.
  Chuyển ảnh có fade hữu hạn, tôn trọng giảm chuyển động.

Kiểm tra liên quan: 12 bài offscreen và 20 bài Qt/OpenGL thực tế đạt, gồm tạo đúng
bản chơi, dropdown, cuộn ngược, resize và các popup. Mypy/Ruff/format đạt và diff
không lỗi khoảng trắng. Capture thêm kiểm tra tỷ lệ ảnh, đổi dòng 1.21/1.20/26,
fallback cho bản cũ/dòng chưa có ảnh, nguồn được bỏ khi đóng và footer trong viewport.

6 ảnh Qt/OpenGL để riêng trong `/workspace/artifacts/nostalgia-keyart-creator`, có
1440×900 và 1024×600 với chữ 150%. Metadata phiên bản/loader dùng fixture để review
bố cục; nhật ký QML khi chụp rỗng. Không build bộ cài hoặc tạo release/draft mới.
