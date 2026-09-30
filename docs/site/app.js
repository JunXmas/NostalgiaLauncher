// Dò OS trình duyệt, chọn đúng asset trong GitHub Release mới nhất.
// Không framework, không build step. Nếu API GitHub rate-limit hoặc lỗi mạng, rơi về
// đường dẫn releases/latest để người dùng tự chọn.

const REPO = "JunXmas/NostalgiaLauncher";
const API_URL = `https://api.github.com/repos/${REPO}/releases/latest`;
const RELEASES_URL = `https://github.com/${REPO}/releases/latest`;

// Trả {os, arch} suy từ user agent. os: "windows" | "macos" | "linux" | null (không đoán được).
function detectPlatform() {
  const uaData = navigator.userAgentData;
  if (uaData && uaData.platform) {
    const p = uaData.platform.toLowerCase();
    if (p.includes("win")) return { os: "windows", arch: "x64" };
    if (p.includes("mac")) return { os: "macos", arch: detectMacArch() };
    if (p.includes("linux")) return { os: "linux", arch: "x64" };
  }
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("windows")) return { os: "windows", arch: "x64" };
  if (ua.includes("mac os") || ua.includes("macintosh")) return { os: "macos", arch: detectMacArch() };
  if (ua.includes("linux") || ua.includes("x11")) return { os: "linux", arch: "x64" };
  return { os: null, arch: null };
}

// UA thường không lộ arch macOS thật (Rosetta báo Intel). navigator.maxTouchPoints/UA
// không đủ tin cậy để phân biệt; mặc định arm64 (Apple Silicon là máy chủ đạo từ 2020).
function detectMacArch() {
  const ua = navigator.userAgent;
  if (/arm64|aarch64/i.test(ua)) return "arm64";
  return "arm64";
}

// Ưu tiên asset chính cho mỗi (os, arch); phần còn lại liệt kê dưới "khác".
function primaryAssetName(version, os, arch) {
  const v = version.replace(/^v/, "");
  if (os === "windows") return `nostalgia-${v}-windows-x64-setup.exe`;
  if (os === "macos") return `nostalgia-${v}-macos-${arch}.dmg`;
  if (os === "linux") return `nostalgia-${v}-linux-x64.AppImage`;
  return null;
}

function labelFor(name) {
  if (name.endsWith("-setup.exe")) return "Tải cho Windows (bộ cài)";
  if (name.endsWith(".dmg") && name.includes("arm64")) return "Tải cho macOS (Apple Silicon)";
  if (name.endsWith(".dmg") && name.includes("x64")) return "Tải cho macOS (Intel)";
  if (name.endsWith(".AppImage")) return "Tải cho Linux (AppImage)";
  return `Tải ${name}`;
}

function humanSize(bytes) {
  if (!bytes) return "";
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)} MB`;
}

function showFallback(statusText) {
  const status = document.getElementById("download-status");
  const primary = document.getElementById("primary-download");
  status.textContent = statusText;
  primary.hidden = false;
  primary.href = RELEASES_URL;
  document.getElementById("primary-label").textContent = "Xem mọi bản trên GitHub";
  document.getElementById("primary-meta").textContent = "";
}

function renderOtherFiles(assets, shownNames) {
  const rest = assets.filter((a) => !shownNames.includes(a.name) && a.name !== "SHA256SUMS");
  if (rest.length === 0) return;
  const list = document.getElementById("other-files-list");
  for (const a of rest) {
    const li = document.createElement("li");
    const a_ = document.createElement("a");
    a_.href = a.browser_download_url;
    a_.textContent = `${a.name} (${humanSize(a.size)})`;
    li.appendChild(a_);
    list.appendChild(li);
  }
  document.getElementById("other-files").hidden = false;
}

// Gắn nút phụ (Linux/macOS) trỏ đúng asset của hệ đó trong bản mới nhất — không trỏ
// chung vào trang Releases. Ẩn nút nếu bản phát hành không có asset cho hệ đó.
function wireSecondaryButton(id, assets, version, os, arch) {
  const el = document.getElementById(id);
  const wantedName = primaryAssetName(version, os, arch);
  const asset = assets.find((a) => a.name === wantedName);
  if (!asset) return null;
  el.href = asset.browser_download_url;
  el.hidden = false;
  return asset.name;
}

async function main() {
  const { os, arch } = detectPlatform();

  let release;
  try {
    const res = await fetch(API_URL, { headers: { Accept: "application/vnd.github+json" } });
    if (!res.ok) throw new Error(`GitHub API ${res.status}`);
    release = await res.json();
  } catch (err) {
    showFallback("Không dò được bản mới nhất tự động (API GitHub tạm không phản hồi).");
    return;
  }

  const assets = release.assets || [];
  if (!os || assets.length === 0) {
    showFallback("Không nhận diện được hệ điều hành — chọn file phù hợp bên dưới.");
    renderOtherFiles(assets, []);
    return;
  }

  const wantedName = primaryAssetName(release.tag_name, os, arch);
  const asset = assets.find((a) => a.name === wantedName);

  const status = document.getElementById("download-status");
  const primary = document.getElementById("primary-download");

  if (!asset) {
    showFallback(`Không thấy file cho hệ điều hành này trong bản ${release.tag_name}.`);
    renderOtherFiles(assets, []);
    return;
  }

  status.textContent = `Nostalgia Launcher ${release.tag_name}`;
  primary.hidden = false;
  primary.href = asset.browser_download_url;
  document.getElementById("primary-label").textContent = labelFor(asset.name);
  document.getElementById("primary-meta").textContent = humanSize(asset.size);

  const shownNames = [asset.name];
  if (os !== "linux") {
    const n = wireSecondaryButton("linux-download", assets, release.tag_name, "linux", "x64");
    if (n) shownNames.push(n);
  }
  if (os !== "macos") {
    const n = wireSecondaryButton("macos-download", assets, release.tag_name, "macos", "arm64");
    if (n) shownNames.push(n);
  }

  renderOtherFiles(assets, shownNames);
}

main();
