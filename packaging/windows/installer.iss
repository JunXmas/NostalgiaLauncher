; Inno Setup: bộ cài Windows x64 từ thư mục PyInstaller dist\nostalgia-ui.
;   set NOSTALGIA_VERSION=1.0.0 && iscc packaging\windows\installer.iss
; Cài vào thư mục của người dùng (không cần quyền admin) để bộ tự cập nhật tráo được thư mục.
#define MyAppVersion GetEnv("NOSTALGIA_VERSION")

[Setup]
AppId={{7E1C4C2A-5B7F-4E0B-9A7B-3C4E6D2F1A90}
AppName=Nostalgia Launcher
AppVersion={#MyAppVersion}
AppPublisher=JunXmas
AppPublisherURL=https://github.com/JunXmas/NostalgiaLauncher
AppSupportURL=https://github.com/JunXmas/NostalgiaLauncher/issues
DefaultDirName={autopf}\Nostalgia Launcher
DefaultGroupName=Nostalgia Launcher
DisableProgramGroupPage=yes
OutputDir=..\..\out
OutputBaseFilename=nostalgia-{#MyAppVersion}-windows-x64-setup
SetupIconFile=..\icons\nostalgia.ico
UninstallDisplayIcon={app}\nostalgia-ui.exe
LicenseFile=..\..\LICENSE
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Tạo lối tắt trên màn hình"; GroupDescription: "Lối tắt:"

[Files]
Source: "..\..\dist\nostalgia-ui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; WorkingDir: {%TEMP} — KHÔNG để mặc định. Thiếu chỉ thị này thì Windows lấy thư mục chứa
; .exe làm thư mục làm việc, tức chính {app}. Windows giữ handle chặn DELETE trên thư mục
; làm việc của mọi tiến trình đang sống, và đổi tên một thư mục cần quyền DELETE — nên script
; tự cập nhật không dời được {app} và launcher tắt rồi không mở lại (bug 1.1.x). Bộ cập nhật
; đã tự chống ba lớp, dòng này bịt nguyên nhân ở gốc: launcher không bao giờ chạy với thư mục
; làm việc trỏ vào thư mục cài nữa. Launcher không đọc/ghi gì theo đường tương đối nên đổi
; thư mục làm việc không ảnh hưởng chức năng nào.
Name: "{group}\Nostalgia Launcher"; Filename: "{app}\nostalgia-ui.exe"; WorkingDir: "{%TEMP}"
Name: "{autodesktop}\Nostalgia Launcher"; Filename: "{app}\nostalgia-ui.exe"; WorkingDir: "{%TEMP}"; Tasks: desktopicon

[Run]
Filename: "{app}\nostalgia-ui.exe"; Description: "Mở Nostalgia Launcher"; Flags: nowait postinstall skipifsilent
