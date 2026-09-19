#!/usr/bin/env bash
# Chạy đúng những gì job `check` của .github/workflows/release.yml sẽ chạy — NHƯNG ở máy,
# TRƯỚC khi đẩy tag. Mọi lần release đỏ từ trước tới nay đều đỏ ở job này, và lúc đó tag
# đã nằm trên GitHub rồi, phải xoá tay rồi tag lại.
#
#   scripts/preflight-release.sh v1.0.14   # kiểm rồi in lệnh tag
#   scripts/preflight-release.sh v1.0.14 --tag   # kiểm xong tự tag + push nếu xanh
#
# Xanh hết mới được tag. Đỏ ở đâu thì dừng ngay ở đó.
set -euo pipefail
cd "$(dirname "$0")/.."

tag="${1:-}"
[[ -n $tag ]] || { echo "dùng: $0 vX.Y.Z [--tag]" >&2; exit 2; }

# Hậu tố kiểu `-hotfix` chính là thứ làm v1.0.10-hotfix đỏ: bước so tag với __version__
# trong workflow không bao giờ khớp được.
[[ $tag =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "✗ tag '$tag' sai dạng — phải đúng vX.Y.Z, không hậu tố" >&2; exit 1; }

step() { echo; echo "── $1"; }

step "tag khớp phiên bản trong mã"
expected="v$(uv run python -c 'import nostalgia; print(nostalgia.__version__)')"
[[ $tag == "$expected" ]] || {
  echo "✗ tag $tag khác $expected — sửa src/nostalgia/__init__.py và pyproject.toml trước" >&2
  exit 1; }
echo "✓ $tag"

step "tag chưa tồn tại"
git fetch --tags --quiet
git rev-parse -q --verify "refs/tags/$tag" >/dev/null && {
  echo "✗ tag $tag đã có — xoá trước, hoặc lên số mới" >&2; exit 1; }
echo "✓ chưa có"

step "ruff + mypy"
uv run ruff check .
uv run ruff format --check .
uv run mypy
echo "✓ sạch"

step "pytest (bỏ test cần mạng — giống workflow)"
uv run pytest -m "not network" -q
echo "✓ xanh"

step "ghi chú phát hành"
[[ -s docs/RELEASE_NOTES.md ]] || { echo "✗ docs/RELEASE_NOTES.md rỗng" >&2; exit 1; }
echo "✓ có nội dung ($(wc -l < docs/RELEASE_NOTES.md) dòng)"

echo
echo "════ tất cả xanh — $tag an toàn để đẩy ════"
if [[ ${2:-} == "--tag" ]]; then
  git tag -a "$tag" -m "Nostalgia Launcher $tag"
  git push origin "$tag"
  echo "đã đẩy $tag — theo dõi: gh run watch"
else
  echo "  git tag -a $tag -m 'Nostalgia Launcher $tag' && git push origin $tag"
fi
