// Dò OS trình duyệt, chọn đúng asset trong GitHub Release mới nhất.
// Không framework, không build step. Nếu API GitHub rate-limit hoặc lỗi mạng, rơi về
// đường dẫn releases/latest để người dùng tự chọn.

// Gỡ ngay, trước mọi thứ khác: CSS dùng `.no-js` để bật sẵn nền thanh nav cho người không có
// JavaScript. Để sót class này thì nền hiện ngay từ đầu và mất hiệu ứng nav trong suốt trên hero.
document.documentElement.classList.remove("no-js");

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
  if (os !== "windows") {
    const n = wireSecondaryButton("windows-download", assets, release.tag_name, "windows", "x64");
    if (n) shownNames.push(n);
  }
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

/* ─────────────────────────── Chuyển động ───────────────────────────

   Ba hiệu ứng, viết tay bằng API sẵn có của trình duyệt. Trang mẫu (skewclient.store) làm
   cùng ba thứ này bằng Lenis + framer-motion + three.js, cộng lại hơn 600 KB JavaScript tải
   từ CDN — kho này không có một phụ thuộc runtime nào và trang web đi theo luật đó.

   Người bật "giảm chuyển động" trong hệ điều hành thì KHÔNG gắn gì cả: parallax với họ không
   phải trang trí mà là chóng mặt thật. CSS cũng có nhánh `prefers-reduced-motion` riêng, hai
   lớp này phải khớp nhau. */

const STILL = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// 1. Thanh điều hướng lấy nền sau khi rời khỏi hero.
const nav = document.getElementById("nav");
const heroBg = document.getElementById("heroBg");

// 2. Ảnh hero trôi chậm hơn trang (parallax).
//
// Đọc `scrollY` trong `rAF` chứ không ngay trong handler `scroll`: đọc trong handler thì mỗi
// sự kiện cuộn ép trình duyệt tính lại bố cục giữa chừng (layout thrashing) và trang giật ở
// đúng lúc đang cuộn. Cờ `ticking` gộp nhiều sự kiện vào một khung hình.
let ticking = false;

function onScroll() {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    const y = window.scrollY;
    nav.classList.toggle("is-stuck", y > 40);
    if (heroBg && !STILL) {
      // Hệ số 0.35 và chặn ở 1.2× chiều cao màn hình: quá ngưỡng đó ảnh đã khuất hẳn, tính
      // tiếp chỉ tốn công. Dấu dương vì ảnh đi CÙNG chiều cuộn nhưng chậm hơn — đi ngược
      // chiều thì nó chạy ra khỏi khung và lòi nền đen ở mép dưới.
      const limit = window.innerHeight * 1.2;
      heroBg.style.transform = `translate3d(0, ${Math.min(y, limit) * 0.35}px, 0)`;
    }
    ticking = false;
  });
}

window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

// 3. Hiện dần khi cuộn tới, lệch nhịp từng phần tử.
//
// Class `.reveal` GẮN BẰNG JS, không viết sẵn trong HTML: viết sẵn thì ai tắt JavaScript sẽ
// thấy trang trắng vĩnh viễn — mất nội dung chứ không phải mất hoạt ảnh.
if (!STILL && "IntersectionObserver" in window) {
  const watcher = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("is-in");
        // Bỏ theo dõi ngay: hiện rồi thì không ẩn lại khi cuộn ngược. Nội dung nhấp nháy mỗi
        // lần người dùng cuộn qua cuộn lại là thứ gây khó chịu nhanh nhất.
        watcher.unobserve(entry.target);
      }
    },
    // `-10%` dưới đáy: đợi phần tử vào hẳn trong khung rồi mới chạy, chứ không bật ngay lúc
    // mép trên vừa ló ra — bật sớm thì hoạt ảnh kết thúc trước khi người dùng nhìn tới.
    { threshold: 0.12, rootMargin: "0px 0px -10% 0px" },
  );

  for (const head of document.querySelectorAll(".section-head")) {
    head.classList.add("reveal");
    watcher.observe(head);
  }
  for (const group of document.querySelectorAll("[data-stagger]")) {
    [...group.children].forEach((child, index) => {
      child.classList.add("reveal");
      // Lệch nhịp đọc từ `--i` trong CSS. Chặn ở 6 để hàng cuối của lưới dài không phải chờ
      // nửa giây sau khi đã nằm sẵn trong khung nhìn.
      child.style.setProperty("--i", String(Math.min(index, 6)));
      watcher.observe(child);
    });
  }
}
