// Dò OS trình duyệt, chọn đúng asset trong GitHub Release mới nhất.
// Không framework, không build step. Nếu API GitHub rate-limit hoặc lỗi mạng, rơi về
// đường dẫn releases/latest để người dùng tự chọn.

// Gỡ ngay, trước mọi thứ khác: CSS dùng `.no-js` để bật sẵn nền thanh nav cho người không có
// JavaScript. Để sót class này thì nền hiện ngay từ đầu và mất hiệu ứng nav trong suốt trên hero.
document.documentElement.classList.remove("no-js");

const REPO = "JunXmas/NostalgiaLauncher";
// `/releases` chứ không `/releases/latest`: cùng MỘT request vừa ra bản mới nhất vừa ra lượt
// tải của mọi bản. API ẩn danh chỉ cho 60 lượt/giờ/IP — thêm một request nữa chỉ để đếm là
// tự rút ngắn ngưỡng đó xuống một nửa cho mọi người dùng chung IP (ký túc xá, quán net, NAT
// nhà mạng), và khi cháy ngưỡng thì thứ hỏng là NÚT TẢI chứ không phải con số trang trí.
// 100 là trần của API. Kho có 18 bản; vượt 100 thì con số đếm thiếu phần đuôi — chấp nhận,
// vì phân trang đổi lấy một request nữa mỗi lượt vào trang, mà phần đuôi là các bản cũ nhất.
const PAGE_SIZE = 100;
const API_URL = `https://api.github.com/repos/${REPO}/releases?per_page=${PAGE_SIZE}`;
const RELEASES_URL = `https://github.com/${REPO}/releases/latest`;

// Lượt tải đã có trước khi kho được dựng lại dưới PolyForm Strict (2026-10-05). GitHub đặt
// `download_count` về 0 cho mọi asset vừa tải lên, nên lượt tải KHÔNG chuyển kho được — API
// của kho mới chỉ trả về lượt tải phát sinh sau khi chuyển. Không cộng mốc này thì con số
// trên trang tụt từ 758 xuống còn vài lượt ngay sau khi chuyển, đọc ra như chưa ai từng tải.
// Đếm từ `/releases` của kho cũ (19 bản, đã bỏ `SHA256SUMS`) đúng trước lúc chuyển. Kho cũ
// nay đã lưu trữ riêng và không còn công khai, nên con số này không đối chiếu lại được từ
// bên ngoài — sửa nó thì phải có số liệu thật trong tay, đừng ước lượng.
const DOWNLOADS_BEFORE_RELICENSE = 758;

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

// Cộng lượt tải mọi bản, trên nền mốc trước lúc đổi giấy phép. Bỏ `SHA256SUMS`: nó là file
// băm để đối chiếu, một người tải launcher rồi tải thêm nó sẽ bị đếm thành hai lượt — con số
// phồng lên mà không ai kiểm lại được.
function countDownloads(releases) {
  let total = DOWNLOADS_BEFORE_RELICENSE;
  for (const release of releases) {
    for (const asset of release.assets || []) {
      if (asset.name !== "SHA256SUMS") total += asset.download_count || 0;
    }
  }
  return total;
}

// Khoảng trắng hẹp không ngắt dòng (U+202F) làm dấu phân nhóm, đúng lối viết số tiếng Việt và
// không bị hiểu nhầm thành dấu thập phân như dấu chấm. `toLocaleString("vi-VN")` ra dấu chấm —
// "1.234" đọc ra một phẩy hai ba tư ở phần lớn phần còn lại của thế giới.
function groupDigits(number) {
  return String(number).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

// Con số này là thứ DUY NHẤT trên trang thay đổi sau mỗi lượt tải, nên nó cũng là thứ duy nhất
// có thể lặng lẽ sai mà không ai thấy. Nếu API không trả về được thì để nguyên con số tĩnh đã
// viết sẵn trong HTML — một con số cũ và đúng-tại-thời-điểm-ghi tốt hơn một ô trống, và tốt
// hơn hẳn số 0 (số 0 đọc ra "chưa ai tải", tức nói dối về chính thứ đang quảng cáo).
function renderDownloadTotal(releases) {
  const slot = document.getElementById("download-total");
  if (!slot) return;
  const total = countDownloads(releases);
  if (total <= 0) return;
  slot.textContent = groupDigits(total);
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

  let releases;
  try {
    const res = await fetch(API_URL, { headers: { Accept: "application/vnd.github+json" } });
    if (!res.ok) throw new Error(`GitHub API ${res.status}`);
    releases = await res.json();
    if (!Array.isArray(releases)) throw new Error("API không trả về danh sách");
  } catch (err) {
    showFallback("Không dò được bản mới nhất tự động (API GitHub tạm không phản hồi).");
    return;
  }

  // Đếm TRƯỚC khi lọc: một bản thử nghiệm vẫn là lượt tải thật của người thật.
  renderDownloadTotal(releases);

  // `/releases` trả về cả bản nháp và bản thử nghiệm, khác `/releases/latest` vốn tự bỏ hai
  // loại đó. Không lọc ở đây thì một bản nháp — thứ chỉ chủ kho nhìn thấy, và chỉ khi đã đăng
  // nhập — sẽ thành "bản mới nhất" của trang, với asset mà người lạ tải về 404.
  //
  // Sắp theo `published_at` chứ không tin thứ tự API trả về: `/releases` sắp theo `created_at`,
  // còn "bản mới nhất" theo định nghĩa của GitHub là theo `published_at`. Hai mốc đó lệch nhau
  // khi một bản được tạo nháp trước rồi publish sau — đúng quy trình phát hành của kho này
  // (`release.yml` dựng bản DRAFT, jun publish tay sau khi test).
  const published = releases
    .filter((r) => !r.draft && !r.prerelease)
    .sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at));
  const release = published[0];
  if (!release) {
    showFallback("Chưa có bản phát hành nào.");
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

/* 4. Cuộn quán tính.
 *
 *   Thứ làm trang mẫu "cảm giác khác" không phải hiệu ứng nào trong ba cái trên, mà là cuộn:
 *   con lăn ở đó không nhảy từng nấc mà đẩy trang trượt tới rồi hãm dần. Soi bundle của
 *   skewclient.store ra đúng thông số họ đặt cho Lenis:
 *
 *       options: { lerp: 0.1, duration: 1.5, smoothWheel: true }
 *
 *   `lerp: 0.1` nghĩa là mỗi khung hình đi 10% quãng đường còn lại — một bộ lọc thông thấp
 *   bậc nhất, không phải "animation có thời lượng". Dùng đúng 0.1, nhưng viết tay ~40 dòng
 *   thay vì kéo Lenis (20 KB nén) về: kho này không có một phụ thuộc runtime nào.
 *
 *   `scroll-behavior: smooth` của CSS KHÔNG thay được. Nó chỉ áp cho lệnh nhảy neo
 *   (`scrollTo`, bấm `#id`); con lăn vẫn giật từng nấc như cũ. Hai thứ khác nhau hẳn.
 *
 *   ĐÁNH ĐỔI, nói thẳng: đây là cướp con lăn khỏi trình duyệt. Người dùng chuột nấc cứng sẽ
 *   thấy trang trôi thêm một quãng sau khi ngón tay đã dừng. Đổi lại được cảm giác "nặng"
 *   mà jun chọn. Chỉ cướp ĐÚNG `wheel` — bàn phím (Space/PageDown/mũi tên), kéo thanh cuộn,
 *   và vuốt cảm ứng đều để nguyên cho hệ điều hành, vì ba thứ đó người dùng mong khớp 1:1
 *   với tay và làm mượt chúng là làm hỏng chúng. */

// `STILL` đã đọc ở trên. Người xin giảm chuyển động thì không gắn gì cả: quán tính là đúng
// loại chuyển động gây chóng mặt tiền đình, và họ đã nói rõ là không muốn.
//
// Cũng bỏ qua khi trình duyệt báo có màn hình cảm ứng chính (`pointer: coarse`): trên điện
// thoại, cuộn do hệ điều hành chạy ở luồng riêng (compositor) nên mượt sẵn và còn trả lại
// thanh địa chỉ đúng nhịp. Chen vào giữa thì mất cả hai.
const SMOOTH_WHEEL = !STILL && !window.matchMedia("(pointer: coarse)").matches;

if (SMOOTH_WHEEL) {
  const doc = document.documentElement;
  let target = window.scrollY;
  let current = target;
  let running = false;

  const maxScroll = () => doc.scrollHeight - window.innerHeight;

  // `lerp: 0.1` của Lenis là "mỗi khung hình đi 10% quãng còn lại" — và viết thẳng như vậy
  // thì tốc độ hãm BUỘC VÀO tần số quét màn hình: màn 120 Hz hãm xong trong nửa thời gian
  // của màn 60 Hz, cùng một trang mà hai máy cho hai cảm giác khác hẳn. Quy về thời gian
  // thật: sau `dt` mili giây, phần quãng CÒN LẠI là 0.9^(dt/16.67).
  const lerpOver = (dt) => 1 - Math.pow(0.9, dt / 16.667);

  let last = 0;

  function frame(now) {
    const dt = last ? Math.min(now - last, 50) : 16.667;
    last = now;
    const remaining = target - current;
    // Dưới 0.3px thì đặt thẳng vào đích và dừng vòng lặp. Không có ngưỡng này thì `lerp`
    // tiệm cận mãi mãi và `requestAnimationFrame` chạy suốt đời trang, ăn pin không vì gì.
    if (Math.abs(remaining) < 0.3) {
      current = target;
      running = false;
      last = 0;
    } else {
      current += remaining * lerpOver(dt);
      requestAnimationFrame(frame);
    }
    window.scrollTo(0, current);
    // Trả `scroll-behavior` lại cho CSS NGAY khi hãm xong, không tắt vĩnh viễn: nó vẫn là
    // thứ làm mượt các neo `#download`, `#steps` và phím Home/End. Tắt trong lúc chạy là bắt
    // buộc — để nguyên thì mỗi lần ghi vị trí trình duyệt lại mở một hoạt ảnh riêng của nó,
    // hai vòng lặp đánh nhau và trang rung.
    if (!running) doc.style.scrollBehavior = "";
  }

  window.addEventListener(
    "wheel",
    (event) => {
      // Ctrl+lăn là phóng to của trình duyệt, không phải cuộn. Nuốt nó là chặn người dùng
      // phóng chữ lên — một đường vào trợ năng, không phải một cử chỉ trang trí.
      if (event.ctrlKey) return;
      // `deltaMode` 1 = lăn theo DÒNG (Firefox hay báo kiểu này), 2 = theo TRANG. Nhân
      // thẳng `deltaY` mà không quy đổi thì trên Firefox một nấc chỉ đi được 3 px.
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1;
      event.preventDefault();
      target = Math.max(0, Math.min(target + event.deltaY * unit, maxScroll()));
      if (!running) {
        running = true;
        doc.style.scrollBehavior = "auto";
        // Bắt nhịp từ vị trí THẬT: giữa chừng người dùng có thể đã kéo thanh cuộn hoặc bấm
        // một neo, và `current` cũ khi đó là một con số đã chết. Không đồng bộ ở đây thì
        // trang nhảy giật về chỗ cũ ngay nấc lăn đầu tiên sau đó.
        current = window.scrollY;
        requestAnimationFrame(frame);
      }
    },
    // `passive: false` bắt buộc — không có nó trình duyệt bỏ qua `preventDefault()` và cuộn
    // native vẫn chạy song song với vòng lặp này.
    { passive: false },
  );

  // Mọi đường cuộn KHÁC (bàn phím, thanh cuộn, neo `#id`, `Ctrl+F` nhảy tới kết quả) đều
  // không đi qua handler trên. Đồng bộ lại `target` để nấc lăn kế tiếp nối từ chỗ người dùng
  // đang đứng, chứ không kéo ngược về chỗ vòng lặp bỏ dở.
  window.addEventListener(
    "scroll",
    () => {
      if (!running) target = current = window.scrollY;
    },
    { passive: true },
  );
}
