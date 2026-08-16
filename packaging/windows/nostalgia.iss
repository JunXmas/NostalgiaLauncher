; Kịch bản Inno Setup cho Nostalgia Launcher.
;
; Biên dịch (sau khi PyInstaller đã chạy xong):
;   iscc packaging\windows\nostalgia.iss
;
; Kết quả: dist\installer\NostalgiaLauncher-<phiên bản>-Setup.exe

#define AppName "Nostalgia Launcher"
#define AppVersion "0.4.0"
#define AppPublisher "Nostalgia Launcher"
#define AppURL "https://github.com/jun/nostalgia-launcher"
#define AppExeName "Nostalgia Launcher.exe"

[Setup]
AppId={{8E2C1A94-6F3D-4B7A-9C15-2D8E4F1B6A73}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\..\dist\installer
OutputBaseFilename=NostalgiaLauncher-{#AppVersion}-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

; Cài cho một người dùng nên không cần quyền quản trị, và đó là chủ ý: bản cài
; chưa mua chứng thư ký số, mà hộp thoại UAC hiện lên với dòng "Unknown
; publisher" là lúc phần lớn người ta bấm huỷ. Ai muốn cài cho cả máy vẫn chọn
; được — dòng dưới cho phép đổi ngay trong lúc cài.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Qt 6 không còn bản 32-bit, nên chặn thẳng máy x86 thay vì để nó cài xong rồi
; mới lỗi lúc chạy.
;
; Tên "x64compatible" chỉ có từ Inno Setup 6.3 trở đi. Bản cũ hơn báo lỗi ngay
; lúc biên dịch; gặp vậy thì đổi cả hai dòng dưới thành "x64" là chạy được.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; PyInstaller xuất ra một thư mục; chép trọn cả cây, kể cả thư mục con.
Source: "..\..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Bỏ 'skipifsilent' để bản cài im lặng (auto-update) tự mở lại app sau khi cài.
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall

[UninstallDelete]
; Chỉ dọn thứ do chính bản cài sinh ra. Tài khoản đã đăng nhập, cấu hình và toàn
; bộ thư mục game nằm trong %APPDATA% và phải được giữ nguyên: gỡ cài đặt để cài
; lại bản mới là chuyện thường, xoá mất bản đồ và thế giới của người chơi thì
; không sửa lại được.
Type: filesandordirs; Name: "{app}\_internal"
