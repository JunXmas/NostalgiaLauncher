# Ký số (Authenticode) các file .exe của bản Windows.
#
# Kích hoạt khi có secret WINDOWS_CERT_PFX_BASE64 (+ WINDOWS_CERT_PASSWORD) —
# nội dung .pfx đã mã hoá base64. Không có chứng chỉ thì script tự bỏ qua, nên
# fork/PR không có secret vẫn build ra file cài (chưa ký) bình thường.
#
# Dùng:  pwsh packaging/windows/sign.ps1 -Paths "dist\...\App.exe","dist\installer\*.exe"
param(
    [Parameter(Mandatory = $true)][string[]]$Paths
)
$ErrorActionPreference = "Stop"

$b64 = $env:WINDOWS_CERT_PFX_BASE64
if ([string]::IsNullOrWhiteSpace($b64)) {
    Write-Host "Chưa cấu hình chứng chỉ (WINDOWS_CERT_PFX_BASE64) — bỏ qua bước ký."
    exit 0
}

# Giải mã .pfx ra file tạm.
$pfx = Join-Path $env:RUNNER_TEMP "codesign.pfx"
[IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($b64))

# Tìm signtool.exe trong Windows SDK (chọn bản mới nhất).
$signtool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" `
    -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
if (-not $signtool) {
    Remove-Item $pfx -ErrorAction SilentlyContinue
    throw "Không tìm thấy signtool.exe trong Windows SDK."
}

try {
    foreach ($pattern in $Paths) {
        foreach ($file in Get-ChildItem $pattern -ErrorAction Stop) {
            Write-Host "==> Ký $($file.FullName)"
            & $signtool.FullName sign `
                /f $pfx /p $env:WINDOWS_CERT_PASSWORD `
                /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
                $file.FullName
            if ($LASTEXITCODE -ne 0) { throw "signtool trả về $LASTEXITCODE cho $($file.FullName)" }
        }
    }
}
finally {
    Remove-Item $pfx -ErrorAction SilentlyContinue
}
