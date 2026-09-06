"""Nội dung cài thêm vào một bản chơi: mod, gói tài nguyên, shader.

Ba quy tắc, học từ chỗ hỏng của các launcher đi trước:

- **Một nguồn, một hình dạng.** Mọi thứ về `Project` / `ProjectVersion` ở `model.py`; UI không
  bao giờ nhìn thấy JSON của Modrinth.
- **Lọc theo bản chơi ngay ở lõi.** Mod chỉ được cài khi khớp cả `game_version` lẫn
  `loader_kind` của bản chơi — không có đường "cài rồi tính".
- **Theo dõi bằng file cạnh mod.** `.nostalgia-installed.json` trong chính thư mục `mods/`
  ghi mod nào đến từ dự án nào; nhờ vậy biết được có bản mới hay không mà không cần CSDL.
"""
