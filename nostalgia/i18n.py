"""Đa ngôn ngữ đơn giản: tr(<chuỗi tiếng Anh>) trả bản dịch theo ngôn ngữ đang chọn.

Khoá dịch chính là chuỗi tiếng Anh, nên chuỗi nào CHƯA có bản dịch sẽ tự rơi về
tiếng Anh — dịch dần cũng không vỡ giao diện.
"""

from __future__ import annotations

# (mã, tên hiển thị) — hiện trong Settings.
LANGUAGES = [
    ("en", "English"), ("vi", "Tiếng Việt"), ("es", "Español"),
    ("fr", "Français"), ("de", "Deutsch"), ("pt", "Português"),
    ("ru", "Русский"), ("zh", "中文"), ("ja", "日本語"), ("ko", "한국어"),
]

# Bộ chuỗi UI chính. en là khoá; mỗi ngôn ngữ khác dịch những gì có, thiếu -> en.
_T = {
    "vi": {
        "Home": "Trang chủ", "Instances": "Trò chơi", "Games": "Trò chơi",
        "Mods": "Mods",
        "Resource Packs": "Gói giao diện", "Shaders": "Shader",
        "Servers": "Máy chủ", "Skin": "Skin", "Settings": "Cài đặt",
        # Tooltip helper cho nav (giải thích bằng lời thường).
        "Your dashboard — jump straight back into a game.":
            "Bảng điều khiển — vào lại game nhanh.",
        "Your separate Minecraft setups. Each has its own version, mods and worlds.":
            "Các bản Minecraft riêng của bạn. Mỗi bản có phiên bản, mod và thế giới riêng.",
        "Your games. Open one to play it or add mods, resource packs and shaders.":
            "Các game của bạn. Mở một game để chơi hoặc thêm mod, gói giao diện, shader.",
        "Add-ons that change or add features to the game.":
            "Tiện ích thêm/đổi tính năng cho game.",
        "Texture & sound packs that change how the game looks and sounds.":
            "Gói đổi hình ảnh & âm thanh của game.",
        "Fancy lighting and visual effects for a better-looking game.":
            "Ánh sáng và hiệu ứng đẹp hơn cho game.",
        "Change how your character looks in the game.":
            "Đổi ngoại hình nhân vật trong game.",
        "Memory, folders, language and updates.":
            "Bộ nhớ, thư mục, ngôn ngữ và cập nhật.",
        "Open our community Discord in your browser.":
            "Mở Discord cộng đồng trên trình duyệt.",
        # Subheading / helper trên các trang + tooltip nút.
        "Each is a separate copy of the game — its own version, mods and worlds.":
            "Mỗi bản là một bản game riêng — phiên bản, mod và thế giới riêng.",
        "No games yet. Click NEW GAME to set one up — just a name and a version.":
            "Chưa có game nào. Bấm NEW GAME để tạo — chỉ cần tên và phiên bản.",
        "Set up a fresh copy of the game (pick a name and version).":
            "Tạo một bản game mới (đặt tên và chọn phiên bản).",
        "Install a ready-made bundle of mods someone already put together.":
            "Cài một gói mod dựng sẵn của người khác.",
        "Packs that change how the game looks and sounds.":
            "Gói đổi hình ảnh và âm thanh của game.",
        "Choose which game to install this into.":
            "Chọn game để cài vào.",
        # Onboarding lần đầu.
        "Welcome to Nostalgia Launcher": "Chào mừng đến Nostalgia Launcher",
        "SET UP MY FIRST GAME": "TẠO GAME ĐẦU TIÊN",
        "BROWSE READY-MADE PACKS": "XEM CÁC GÓI DỰNG SẴN",
        "SKIP FOR NOW": "ĐỂ SAU",
        ("Let’s get your first game running. One click sets up a ready-to-play "
         "copy of Minecraft with the Aero glass look — no setup, no jargon.\n\n"
         "After that, three easy moves make it yours:  play once  ·  add a skin  ·  add a mod."):
            ("Cùng chạy game đầu tiên nào. Một cú bấm là có ngay một bản Minecraft "
             "chơi được với giao diện kính Aero — không cài đặt, không thuật ngữ.\n\n"
             "Sau đó, ba bước là thành của bạn:  chơi thử  ·  đổi skin  ·  thêm mod."),
        # Empty state + tooltip.
        "Nothing here yet — open the Browse tab to add some from Modrinth.":
            "Chưa có gì ở đây — mở tab Browse để thêm từ Modrinth.",
        "Show add-ons for this mod system. Match it to your game (Fabric is the most common).":
            "Hiện tiện ích theo hệ mod này. Chọn khớp với game của bạn (Fabric phổ biến nhất).",
        "How much memory the game may use. More helps big modpacks; too much can slow your PC.":
            "Bộ nhớ game được dùng. Nhiều giúp modpack lớn; quá nhiều có thể làm máy chậm.",
        "Advanced: where games and downloads are stored. Most people never change this.":
            "Nâng cao: nơi lưu game và bản tải. Hầu như không cần đổi.",
        "Advanced: leave empty and the launcher picks the right Java for you.":
            "Nâng cao: để trống, launcher tự chọn Java đúng cho bạn.",
        "No game yet": "Chưa có game",
        "No game yet — click NEW GAME to make one.":
            "Chưa có game — bấm NEW GAME để tạo.",
        "Show snapshots": "Hiện bản snapshot",
        "Close launcher when the game starts": "Đóng launcher khi game khởi động",
        "Check for updates on startup": "Kiểm tra cập nhật khi mở",
        "Dark menu background (night panorama)": "Nền menu tối (panorama ban đêm)",
        "Menu background: off = daytime panorama, on = nighttime.":
            "Nền menu: tắt = panorama ban ngày, bật = ban đêm.",
        "Menu: Day": "Menu: Ngày", "Menu: Night": "Menu: Đêm",
        "Switch the in-game menu background between day and night.":
            "Đổi nền menu trong game giữa ngày và đêm.",
        "Setting near all your RAM can freeze the system.":
            "Đặt gần hết RAM có thể làm treo máy.",
        "Settings most people never need to touch.":
            "Những cài đặt hầu như không ai cần đụng tới.",
        "Welcome back!": "Chào mừng trở lại!",
        "What will we build today?": "Hôm nay ta xây gì nào?",
        "My Instances": "Trò chơi của tôi", "New Instance": "Trò chơi mới",
        "My Games": "Trò chơi của tôi", "New Game": "Trò chơi mới",
        "PLAY": "CHƠI", "NEW INSTANCE": "TRÒ CHƠI MỚI", "NEW GAME": "TRÒ CHƠI MỚI",
        "Manage Account": "Quản lý tài khoản", "YOUR ACCOUNT": "TÀI KHOẢN",
        "Connected": "Đã kết nối", "Offline": "Ngoại tuyến", "NEWS": "TIN TỨC",
        "CONTINUE PLAYING": "CHƠI TIẾP", "World": "Thế giới", "Server": "Máy chủ",
        "No worlds or servers yet — play a bit and they'll show up here.":
            "Chưa có thế giới hay máy chủ nào — chơi một chút là nó hiện ở đây.",
        "Loading…": "Đang tải…",
        "just now": "vừa xong", "{n}m ago": "{n} phút trước",
        "{n}h ago": "{n} giờ trước", "{n}d ago": "{n} ngày trước",
        "{n}mo ago": "{n} tháng trước",
        "Join server?": "Vào máy chủ?", "Open world?": "Mở thế giới?",
        "Launch “{inst}” and connect to {name}?":
            "Chạy “{inst}” và kết nối tới {name}?",
        "Launch “{inst}” and load the world “{name}”?":
            "Chạy “{inst}” và mở thế giới “{name}”?",
        "That instance no longer exists.": "Instance này không còn nữa.",
        "Language": "Ngôn ngữ", "Game folder": "Thư mục game",
        "Java path": "Đường dẫn Java", "Everything is up to date!": "Mọi thứ đã mới nhất!",
    },
    "es": {
        "Home": "Inicio", "Instances": "Instancias", "Resource Packs": "Paquetes de recursos",
        "Shaders": "Shaders", "Servers": "Servidores", "Skin": "Skin", "Settings": "Ajustes",
        "Welcome back!": "¡Bienvenido de nuevo!", "What will we build today?": "¿Qué construiremos hoy?",
        "My Instances": "Mis instancias", "New Instance": "Nueva instancia", "PLAY": "JUGAR",
        "NEW INSTANCE": "NUEVA INSTANCIA", "Manage Account": "Gestionar cuenta",
        "YOUR ACCOUNT": "TU CUENTA", "Connected": "Conectado", "Offline": "Sin conexión",
        "NEWS": "NOTICIAS", "Language": "Idioma", "Game folder": "Carpeta del juego",
        "Java path": "Ruta de Java",
    },
    "fr": {
        "Home": "Accueil", "Instances": "Instances", "Resource Packs": "Packs de ressources",
        "Shaders": "Shaders", "Servers": "Serveurs", "Skin": "Skin", "Settings": "Paramètres",
        "Welcome back!": "Bon retour !", "What will we build today?": "Que construisons-nous aujourd'hui ?",
        "My Instances": "Mes instances", "New Instance": "Nouvelle instance", "PLAY": "JOUER",
        "NEW INSTANCE": "NOUVELLE INSTANCE", "Manage Account": "Gérer le compte",
        "YOUR ACCOUNT": "VOTRE COMPTE", "Connected": "Connecté", "Offline": "Hors ligne",
        "NEWS": "ACTUALITÉS", "Language": "Langue", "Game folder": "Dossier du jeu",
        "Java path": "Chemin Java",
    },
    "de": {
        "Home": "Startseite", "Instances": "Instanzen", "Resource Packs": "Ressourcenpakete",
        "Shaders": "Shader", "Servers": "Server", "Skin": "Skin", "Settings": "Einstellungen",
        "Welcome back!": "Willkommen zurück!", "What will we build today?": "Was bauen wir heute?",
        "My Instances": "Meine Instanzen", "New Instance": "Neue Instanz", "PLAY": "SPIELEN",
        "NEW INSTANCE": "NEUE INSTANZ", "Manage Account": "Konto verwalten",
        "YOUR ACCOUNT": "DEIN KONTO", "Connected": "Verbunden", "Offline": "Offline",
        "NEWS": "NEUES", "Language": "Sprache", "Game folder": "Spielordner",
        "Java path": "Java-Pfad",
    },
    "pt": {
        "Home": "Início", "Instances": "Instâncias", "Resource Packs": "Pacotes de recursos",
        "Shaders": "Shaders", "Servers": "Servidores", "Skin": "Skin", "Settings": "Configurações",
        "Welcome back!": "Bem-vindo de volta!", "What will we build today?": "O que vamos construir hoje?",
        "My Instances": "Minhas instâncias", "New Instance": "Nova instância", "PLAY": "JOGAR",
        "NEW INSTANCE": "NOVA INSTÂNCIA", "Manage Account": "Gerenciar conta",
        "YOUR ACCOUNT": "SUA CONTA", "Connected": "Conectado", "Offline": "Offline",
        "NEWS": "NOTÍCIAS", "Language": "Idioma", "Game folder": "Pasta do jogo",
        "Java path": "Caminho do Java",
    },
    "ru": {
        "Home": "Главная", "Instances": "Сборки", "Mods": "Моды",
        "Resource Packs": "Ресурспаки", "Shaders": "Шейдеры", "Servers": "Серверы",
        "Skin": "Скин", "Settings": "Настройки", "Welcome back!": "С возвращением!",
        "What will we build today?": "Что построим сегодня?", "My Instances": "Мои сборки",
        "New Instance": "Новая сборка", "PLAY": "ИГРАТЬ", "NEW INSTANCE": "НОВАЯ СБОРКА",
        "Manage Account": "Управление аккаунтом", "YOUR ACCOUNT": "ВАШ АККАУНТ",
        "Connected": "Подключено", "Offline": "Оффлайн", "NEWS": "НОВОСТИ",
        "Language": "Язык", "Game folder": "Папка игры", "Java path": "Путь к Java",
    },
    "zh": {
        "Home": "主页", "Instances": "实例", "Mods": "模组", "Resource Packs": "资源包",
        "Shaders": "光影", "Servers": "服务器", "Skin": "皮肤", "Settings": "设置",
        "Welcome back!": "欢迎回来！", "What will we build today?": "今天要建造什么？",
        "My Instances": "我的实例", "New Instance": "新建实例", "PLAY": "开始游戏",
        "NEW INSTANCE": "新建实例", "Manage Account": "管理账户", "YOUR ACCOUNT": "你的账户",
        "Connected": "已连接", "Offline": "离线", "NEWS": "新闻", "Language": "语言",
        "Game folder": "游戏文件夹", "Java path": "Java 路径",
    },
    "ja": {
        "Home": "ホーム", "Instances": "インスタンス", "Mods": "Mod",
        "Resource Packs": "リソースパック", "Shaders": "シェーダー", "Servers": "サーバー",
        "Skin": "スキン", "Settings": "設定", "Welcome back!": "おかえりなさい！",
        "What will we build today?": "今日は何を作る？", "My Instances": "マイインスタンス",
        "New Instance": "新規インスタンス", "PLAY": "プレイ", "NEW INSTANCE": "新規インスタンス",
        "Manage Account": "アカウント管理", "YOUR ACCOUNT": "アカウント", "Connected": "接続済み",
        "Offline": "オフライン", "NEWS": "ニュース", "Language": "言語",
        "Game folder": "ゲームフォルダー", "Java path": "Java のパス",
    },
    "ko": {
        "Home": "홈", "Instances": "인스턴스", "Mods": "모드", "Resource Packs": "리소스 팩",
        "Shaders": "셰이더", "Servers": "서버", "Skin": "스킨", "Settings": "설정",
        "Welcome back!": "다시 오신 걸 환영해요!", "What will we build today?": "오늘은 무엇을 만들까요?",
        "My Instances": "내 인스턴스", "New Instance": "새 인스턴스", "PLAY": "플레이",
        "NEW INSTANCE": "새 인스턴스", "Manage Account": "계정 관리", "YOUR ACCOUNT": "내 계정",
        "Connected": "연결됨", "Offline": "오프라인", "NEWS": "뉴스", "Language": "언어",
        "Game folder": "게임 폴더", "Java path": "Java 경로",
    },
}

_current = "en"


def set_language(code: str) -> None:
    global _current
    _current = code if code in dict(LANGUAGES) else "en"


def language() -> str:
    return _current


def language_name(code: str) -> str:
    return dict(LANGUAGES).get(code, code)


def tr(s: str) -> str:
    return _T.get(_current, {}).get(s, s)
