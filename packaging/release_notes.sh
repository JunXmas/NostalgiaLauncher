#!/usr/bin/env bash
# Trích phần changelog của một phiên bản để làm mô tả (devlog) cho GitHub Release,
# rồi thêm ghi chú cài đặt/cảnh báo chưa ký số.
#
#   bash packaging/release_notes.sh <version> [outfile]
#   ví dụ: bash packaging/release_notes.sh 0.2.7 release_notes.md
set -euo pipefail

VERSION="${1:?cần truyền version, ví dụ 0.2.7}"
OUT="${2:-release_notes.md}"
CHANGELOG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/CHANGELOG.md"

# Lấy các dòng dưới "## <version>" cho tới heading "## " kế tiếp.
ver_re="${VERSION//./\\.}"
section="$(awk -v re="^## +${ver_re}([ ]|\$)" '
    $0 ~ re {grab=1; next}
    grab && /^## / {grab=0}
    grab {print}
' "$CHANGELOG")"

{
    if [ -n "$section" ]; then
        printf '## What'\''s new in %s\n%s\n' "$VERSION" "$section"
    else
        printf 'Release %s.\n' "$VERSION"
    fi
    cat <<'NOTE'

---

Installers are not code-signed, so the first launch shows an OS warning — this is normal:

- **Windows** — SmartScreen says "Windows protected your PC": *More info → Run anyway*.
- **macOS** — right-click the app → *Open* → *Open* (or System Settings → Privacy & Security → *Open Anyway*).
- **Linux** — install the package: `sudo apt install ./NostalgiaLauncher-*-amd64.deb`
NOTE
} > "$OUT"

echo "wrote $OUT for $VERSION"
