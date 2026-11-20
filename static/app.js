const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
if (tg) {
  try {
    tg.ready();
    tg.expand();
  } catch {}
}

window.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && ["s", "p", "S", "P"].includes(e.key)) {
    e.preventDefault();
  }
});

function ensurePdfJs() {
  if (!window.pdfjsLib) {
    throw new Error("PDF viewer library is still loading or blocked by network.");
  }
  window.pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
  return window.pdfjsLib;
}

// ================= SVG ICON LIBRARY =================
const ICONS = {
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  quiz: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/></svg>',
  plan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
  saved: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>',
  invite: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>',
  admin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  starOutline: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
  starFilled: '<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.9"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
};

// ================= BILINGUAL STRINGS (ENGLISH / AMHARIC) =================
const I18N = {
  en: {
    who_title: "Who is registering?",
    who_sub: "Select your role so we can configure your dashboard and exam countdown.",
    role_student: "Student",
    role_student_sub: "Study library, timed bubble-sheet quizzes, study plans, and grade countdown",
    role_parent: "Parent or Guardian",
    role_parent_sub: "Child activity charts, progress reports, sibling discounts, and full library",
    prefer_call: "Prefer to register by phone? Call us directly:",
    back: "Back",
    lbl_student_name: "Student Full Name",
    lbl_parent_name: "Parent / Guardian Full Name",
    lbl_phone: "Active Phone Number",
    lbl_grade: "Grade Level (National exam grades marked)",
    lbl_stream: "Academic Stream (Grades 11–12)",
    stream_nat: "Natural Science",
    stream_soc: "Social Science",
    lbl_children: "Children",
    add_child: "+ Add Child",
    sibling_msg: "Sibling tuition discount applied for registering 2 or more children.",
    lbl_format: "Preferred Program",
    fmt_weekend: "Weekend Exam Cohort (Bishoftu Hub)",
    fmt_home: "1-on-1 Home Mentorship",
    fmt_digital: "Digital Study Library Only",
    lbl_ref: "Referral Code (Optional)",
    terms_agree: "By submitting, you agree to our",
    terms_link: "Program Terms & Privacy",
    btn_submit_reg: "Submit Registration",
    invite_short: "Invite",
    child_activity_title: "Child Study Activity",
    progress_reports: "Bi-Weekly Coordinator Reports",
    quiz_cta_title: "Quiz Me — Bubble Sheet",
    quiz_cta_go: "Start",
    search_ph: "Search exam, textbook, year (e.g. 2017 bio)...",
    show_all: "Show All Grades",
    quiz_hub_title: "Mock Exams & Bubble Sheets",
    plan_title: "Study Plans & Syllabi",
    plan_sub: "Follow a structured schedule or add your own daily tasks.",
    tile_ref: "Study Squad Referral",
    tile_ref_sub: "Share your code and track verified friends",
    tile_req: "Request Missing Material",
    tile_req_sub: "Ask for a specific past paper or textbook",
    ref_modal_title: "Study Squad Referral",
    your_ref_code: "Your Personal Referral Code",
    ref_verified_lbl: "Verified Friends Joined:",
    btn_share_tg: "Share on Telegram",
    btn_copy_code: "Copy Code",
    ref_how_title: "How Study Squad Perks Work",
    ref_how_body: "Share your code with classmates in Bishoftu. Once two friends register and complete enrollment, you qualify for same-table Study Squad seating, a bound formula folder, and tuition savings.",
    req_modal_title: "Request a Material",
    req_desc: "Looking for a specific past paper, textbook, or answer key? Send a note to the academic team.",
    btn_send_req: "Send Request",
    btn_offline_tg: "Save Offline in Telegram (Protected View)",
    cd_matric_12: "until Grade 12 ESSLCE (Matric)",
    cd_ministry_8: "until Grade 8 Ministry Exam",
    cd_ministry_6: "until Grade 6 Ministry Exam",
    cd_semester: "until Semester Final Exams",
    days_left: "days",
    launch_banner: "Launch Period Active: Full access to all study resources and quizzes is open.",
    trial_banner: "Preview Mode: 3 grade-matched books and 10-question quizzes are open. Full access activates after approval.",
  },
  am: {
    who_title: "ማን ነው የሚመዘገበው?",
    who_sub: "ዳሽቦርዱን እና የፈተና ቀን ቆጠራውን ለማስተካከል ሁኔታዎን ይምረጡ።",
    role_student: "ተማሪ",
    role_student_sub: "መጽሐፍት፣ ፈጣን ኩዊዞች፣ የጥናት እቅዶች እና የክፍልዎ ፈተና ቆጠራ",
    role_parent: "ወላጅ / አሳዳጊ",
    role_parent_sub: "የልጆች የጥናት ግራፎች፣ ሪፖርቶች፣ የወንድማማች ቅናሽ እና ሙሉ መጽሐፍት",
    prefer_call: "በስልክ መመዝገብ ይመርጣሉ? ይደውሉ:",
    back: "ተመለስ",
    lbl_student_name: "የተማሪው ሙሉ ስም",
    lbl_parent_name: "የወላጅ / አሳዳጊ ሙሉ ስም",
    lbl_phone: "ንቁ የስልክ ቁጥር",
    lbl_grade: "ክፍል ይምረጡ",
    lbl_stream: "ዘርፍ ይምረጡ (11ኛ–12ኛ ክፍል)",
    stream_nat: "ተፈጥሮ ሳይንስ (Natural)",
    stream_soc: "ማህበራዊ ሳይንስ (Social)",
    lbl_children: "ልጆች",
    add_child: "+ ሌላ ልጅ ጨምር",
    sibling_msg: "2 እና ከዚያ በላይ ልጆችን ሲያስመዘግቡ የወንድማማች/እህትማማች ቅናሽ ያገኛሉ።",
    lbl_format: "የሚፈልጉት ፕሮግራም",
    fmt_weekend: "የሳምንት መጨረሻ ማዕከል (ቢሾፍቱ)",
    fmt_home: "1-ለ-1 የቤት ውስጥ አስጠኚ",
    fmt_digital: "ዲጂታል የጥናት መጽሐፍት ብቻ",
    lbl_ref: "የግብዣ ኮድ / Referral Code (አማራጭ)",
    terms_agree: "ሲመዘገቡ በእኛ",
    terms_link: "የአገልግሎት ደንብ እና ግላዊነት",
    btn_submit_reg: "ምዝገባውን ላክ",
    invite_short: "ጋብዝ",
    child_activity_title: "የልጅ የጥናት እንቅስቃሴ",
    progress_reports: "የሁለት ሳምንት የውጤት ሪፖርቶች",
    quiz_cta_title: "ፈተና ይለማመዱ — ባብል ሺት",
    quiz_cta_go: "ጀምር",
    search_ph: "መጽሐፍ፣ ፈተና ወይም ዓመት ይፈልጉ...",
    show_all: "ሁሉንም ክፍሎች አሳይ",
    quiz_hub_title: "የፈተና ልምምድ እና አውቶማቲክ እርማት",
    plan_title: "የጥናት እቅዶች",
    plan_sub: "የየቀኑን ምዕራፎች ይከታተሉ ወይም የራስዎን እቅድ ይፍጠሩ።",
    tile_ref: "የግብዣ ፕሮግራም",
    tile_ref_sub: "ኮድዎን ያጋሩ እና የተመዘገቡ ጓደኞችን ይከታተሉ",
    tile_req: "መጽሐፍ / ፈተና ይጠይቁ",
    tile_req_sub: "የሚፈልጉትን ፈተና ወይም መጽሐፍ ይጠይቁ",
    ref_modal_title: "የግብዣ ፕሮግራም",
    your_ref_code: "የእርስዎ የግብዣ ኮድ",
    ref_verified_lbl: "በኮድዎ የገቡ ጓደኞች:",
    btn_share_tg: "በቴሌግራም አጋራ",
    btn_copy_code: "ኮዱን ቅዳ",
    ref_how_title: "የግብዣ ጥቅሞች",
    ref_how_body: "ኮድዎን በቢሾፍቱ ለሚገኙ ጓደኞችዎ ያጋሩ። 2 ጓደኞች በኮድዎ ሲመዘገቡና ሲጸድቁ የStudy Squad መቀመጫ፣ የፎርሙላ ደብተር እና የክፍያ ቅናሽ ያገኛሉ።",
    req_modal_title: "መጽሐፍ / ፈተና ይጠይቁ",
    req_desc: "የፈለጉትን ፈተና ወይም መጽሐፍ ካጡ ለአስተዳዳሪው በቀጥታ ይላኩ።",
    btn_send_req: "ጥያቄውን ላክ",
    btn_offline_tg: "ኦፍላይን ለማንበብ በቴሌግራም አስቀምጥ",
    cd_matric_12: "እስከ 12ኛ ክፍል ብሔራዊ ፈተና (ESSLCE)",
    cd_ministry_8: "እስከ 8ኛ ክፍል ሚኒስትሪ ፈተና",
    cd_ministry_6: "እስከ 6ኛ ክፍል ሚኒስትሪ ፈተና",
    cd_semester: "እስከ ሴሚስተር ማጠቃለያ ፈተና",
    days_left: "ቀናት",
    launch_banner: "የመክፈቻ ጊዜ: ሁሉም የተመዘገቡ ተማሪዎች ሙሉውን የጥናት ማዕከል በነጻ መጠቀም ይችላሉ።",
    trial_banner: "የሙከራ አገልግሎት: 3 መጽሐፍት እና 10 ጥያቄዎች ተከፍተዋል። ምዝገባዎ ሲጸድቅ ሁሉም ይከፈታል።",
  },
};

let currentLang = localStorage.getItem("qelal_lang") || "en";
function t(key) {
  return (I18N[currentLang] && I18N[currentLang][key]) || I18N.en[key] || key;
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (I18N[currentLang][key]) el.textContent = I18N[currentLang][key];
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (I18N[currentLang][key]) el.placeholder = I18N[currentLang][key];
  });
  const roleTag = document.getElementById("formRoleTag");
  if (roleTag) {
    roleTag.textContent = selectedRole === "parent"
      ? (currentLang === "am" ? "ወላጅ" : "Parent")
      : (currentLang === "am" ? "ተማሪ" : "Student");
  }
  const nameLbl = document.getElementById("lblFullName");
  if (nameLbl) {
    nameLbl.textContent = selectedRole === "parent" ? t("lbl_parent_name") : t("lbl_student_name");
  }
}

// ================= GLOBAL STATE =================
let sessionToken = "";
let userProfile = {};
let allItems = [];
let itemsById = {};
let filteredItems = [];
let visibleLimit = 30;
let cachedPlans = null;
let progress = { bookmarks: [], last_read: {}, plan_progress: {}, custom_plan: [] };

let parentAnalytics = null;
let selectedChildIdx = 0;
let adminOverview = null;

let selectedRole = "student";
let selectedStudentGrade = "Grade 12";
let selectedStudentStream = "Natural";
let parentChildren = [{ name: "", grade: "Grade 12", stream: "Natural", format: "Weekend Hub", child_contact: "" }];

let readerMainDoc = null, readerAnswerDoc = null, showingAnswer = false;
let currentPdfDoc = null, currentPage = 1, savedMainPage = 1, savedAnswerPage = 1, zoomMultiplier = 1.0, renderTask = null;
let activeQuizMeta = null, quizAnswers = {}, quizTimerInt = null, quizSeconds = 0;

function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 3400);
}
function closeModal(id) { document.getElementById(id).classList.add("hidden"); }
function openTermsModal() { document.getElementById("termsModal").classList.remove("hidden"); }
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function fetchJsonSafe(url, opts = {}, timeoutMs = 22000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...opts, signal: ctrl.signal });
    const raw = await res.text();
    let data = {};
    try { data = JSON.parse(raw); } catch { throw new Error(raw.slice(0, 120) || "Server error"); }
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data;
  } catch (err) {
    if (err.name === "AbortError") throw new Error("Server took too long to respond. Please tap retry.");
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

// ================= 1. BOOT & AUTH =================
async function initApp() {
  const urlParams = new URLSearchParams(window.location.search);
  const urlRef = urlParams.get("ref");
  if (urlRef) document.getElementById("regRefCode").value = urlRef.toUpperCase();

  try {
    const data = await fetchJsonSafe("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initData: tg ? (tg.initData || "") : "" }),
    }, 25000);

    document.getElementById("splashView").classList.add("hidden");

    if (!data.ok) {
      if (data.status === "OUTSIDE_TELEGRAM") {
        document.getElementById("outsideView").classList.remove("hidden");
        return;
      }
      setupOnboarding();
      document.getElementById("onboardingView").classList.remove("hidden");
      return;
    }

    userProfile = data;
    sessionToken = data.token;
    if (data.lang && !localStorage.getItem("qelal_lang")) {
      currentLang = data.lang;
    }

    applyTranslations();
    renderHeaderAndBanners();
    buildBottomNav();

    await Promise.all([loadLibrary(false), loadProgress()]);
    document.getElementById("appShell").classList.remove("hidden");

    if (userProfile.role === "parent") {
      switchTab("tabParentHome");
    } else {
      switchTab("tabLibrary");
    }
  } catch (err) {
    document.getElementById("splashView").classList.add("hidden");
    document.getElementById("outsideTitle").textContent = "Connection Error";
    document.getElementById("outsideMsg").textContent = err?.message || "Could not reach server. Please reopen the app.";
    document.getElementById("outsideView").classList.remove("hidden");
  }
}

// ================= 2. ONBOARDING WIZARD =================
function setupOnboarding() {
  applyTranslations();
  const grid = document.getElementById("studentGradeGrid");
  grid.innerHTML = "";
  for (let i = 1; i <= 12; i++) {
    const g = `Grade ${i}`;
    const isNat = [6, 8, 12].includes(i);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `grade-chip ${g === selectedStudentGrade ? "active" : ""}`;
    btn.textContent = isNat ? `${g} (Exam)` : g;
    btn.onclick = () => {
      selectedStudentGrade = g;
      grid.querySelectorAll(".grade-chip").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("studentStreamWrap").classList.toggle("hidden", !(i === 11 || i === 12));
    };
    grid.appendChild(btn);
  }
  document.getElementById("studentStreamWrap").classList.toggle(
    "hidden",
    !(selectedStudentGrade === "Grade 11" || selectedStudentGrade === "Grade 12")
  );
  renderParentChildrenForm();
}

function goStep(stepId) {
  ["stepLang", "stepRole", "stepForm"].forEach((id) => document.getElementById(id).classList.add("hidden"));
  document.getElementById(stepId).classList.remove("hidden");
  applyTranslations();
}

function pickLanguage(lang) {
  currentLang = lang;
  localStorage.setItem("qelal_lang", lang);
  applyTranslations();
  goStep("stepRole");
}

function pickRole(role) {
  selectedRole = role;
  document.getElementById("studentSingleFields").classList.toggle("hidden", role === "parent");
  document.getElementById("parentChildrenFields").classList.toggle("hidden", role !== "parent");
  applyTranslations();
  goStep("stepForm");
}

function setStudentStream(stream) {
  selectedStudentStream = stream;
  document.querySelectorAll(".stream-btn").forEach((b) => {
    b.classList.toggle("active", b.getAttribute("data-stream") === stream);
  });
}

function renderParentChildrenForm() {
  const list = document.getElementById("childrenList");
  list.innerHTML = "";
  document.getElementById("siblingBanner").classList.toggle("hidden", parentChildren.length < 2);

  parentChildren.forEach((ch, idx) => {
    const card = document.createElement("div");
    card.className = "child-card";

    let gradeOpts = "";
    for (let i = 1; i <= 12; i++) {
      const g = `Grade ${i}`;
      const label = [6, 8, 12].includes(i) ? `${g} (National Exam)` : g;
      gradeOpts += `<option value="${g}" ${ch.grade === g ? "selected" : ""}>${label}</option>`;
    }

    const showStream = ch.grade === "Grade 11" || ch.grade === "Grade 12";
    const childLbl = currentLang === "am" ? `ልጅ #${idx + 1}` : `Child #${idx + 1}`;
    const namePh = currentLang === "am" ? "የልጁ ሙሉ ስም" : "Child's Full Name";
    const tgPh = currentLang === "am" ? "የልጁ ቴሌግራም (@username ወይም ስልክ - አማራጭ)" : "Child's Telegram (@username or phone - optional)";

    card.innerHTML = `
      <div class="child-card-head">
        <span>${childLbl}</span>
        ${parentChildren.length > 1 ? `<button type="button" class="remove-child-btn">Remove</button>` : ""}
      </div>
      <input class="q-input ch-name" style="margin-bottom:7px;" type="text" placeholder="${namePh}" value="${escapeHtml(ch.name)}" />
      <select class="q-select ch-grade" style="margin-bottom:7px;">${gradeOpts}</select>
      <select class="q-select ch-stream ${showStream ? "" : "hidden"}" style="margin-bottom:7px;">
        <option value="Natural" ${ch.stream === "Natural" ? "selected" : ""}>Natural Science</option>
        <option value="Social" ${ch.stream === "Social" ? "selected" : ""}>Social Science</option>
      </select>
      <input class="q-input ch-tg" type="text" placeholder="${tgPh}" value="${escapeHtml(ch.child_contact)}" />
    `;

    card.querySelector(".ch-name").oninput = (e) => { ch.name = e.target.value; };
    card.querySelector(".ch-tg").oninput = (e) => { ch.child_contact = e.target.value; };
    card.querySelector(".ch-grade").onchange = (e) => {
      ch.grade = e.target.value;
      const needsStream = ch.grade === "Grade 11" || ch.grade === "Grade 12";
      card.querySelector(".ch-stream").classList.toggle("hidden", !needsStream);
    };
    card.querySelector(".ch-stream").onchange = (e) => { ch.stream = e.target.value; };
    const rmBtn = card.querySelector(".remove-child-btn");
    if (rmBtn) {
      rmBtn.onclick = () => {
        parentChildren.splice(idx, 1);
        renderParentChildrenForm();
      };
    }
    list.appendChild(card);
  });
}

document.getElementById("addChildBtn").onclick = () => {
  parentChildren.push({ name: "", grade: "Grade 8", stream: "Natural", format: "Weekend Hub", child_contact: "" });
  renderParentChildrenForm();
};

document.getElementById("submitRegBtn").onclick = async () => {
  const fullName = document.getElementById("regName").value.trim();
  const phone = document.getElementById("regPhone").value.trim();
  const format = document.getElementById("regFormat").value;
  const referralCode = document.getElementById("regRefCode").value.trim().toUpperCase();

  if (!fullName || !phone) {
    return showToast(currentLang === "am" ? "እባክዎ ስም እና ስልክ ቁጥር ያስገቡ።" : "Please enter full name and phone number.");
  }

  let payloadChildren = [];
  if (selectedRole === "student") {
    payloadChildren = [{
      name: fullName,
      grade: selectedStudentGrade,
      stream: (selectedStudentGrade === "Grade 11" || selectedStudentGrade === "Grade 12") ? selectedStudentStream : "General",
      format,
    }];
  } else {
    for (let i = 0; i < parentChildren.length; i++) {
      if (!parentChildren[i].name.trim()) {
        return showToast(currentLang === "am" ? `እባክዎ የልጅ #${i + 1} ስም ያስገቡ።` : `Please enter Child #${i + 1}'s name.`);
      }
    }
    payloadChildren = parentChildren.map((c) => ({ ...c, format }));
  }

  const btn = document.getElementById("submitRegBtn");
  btn.disabled = true;
  btn.textContent = currentLang === "am" ? "በመመዝገብ ላይ..." : "Saving registration...";

  try {
    const data = await fetchJsonSafe("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        initData: tg ? (tg.initData || "") : "",
        role: selectedRole,
        lang: currentLang,
        full_name: fullName,
        phone,
        format,
        referral_code: referralCode,
        children: payloadChildren,
      }),
    });
    if (!data.ok) throw new Error(data.detail || "Registration failed");

    document.getElementById("onboardingView").classList.add("hidden");
    document.getElementById("splashView").classList.remove("hidden");
    await initApp();
  } catch (err) {
    showToast(err.message);
    btn.disabled = false;
    applyTranslations();
  }
};

async function toggleLanguage() {
  currentLang = currentLang === "en" ? "am" : "en";
  localStorage.setItem("qelal_lang", currentLang);
  applyTranslations();
  if (sessionToken) {
    renderHeaderAndBanners();
    buildBottomNav();
    if (userProfile.role === "parent") renderParentDashboard();
    renderCards();
    fetch("/api/set-lang", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
      body: JSON.stringify({ lang: currentLang }),
    }).catch(() => {});
  }
}
document.getElementById("onboardLangBtn").onclick = toggleLanguage;
document.getElementById("appLangBtn").onclick = toggleLanguage;

// ================= 3. HEADER, COUNTDOWN & BOTTOM NAV =================
function renderHeaderAndBanners() {
  const firstName = (userProfile.name || "Member").split(" ")[0];
  document.getElementById("hdrGreeting").textContent = currentLang === "am" ? `ሰላም, ${firstName}` : firstName;
  document.getElementById("hdrMeta").textContent = userProfile.is_admin
    ? "Admin · Qelal Hub"
    : userProfile.role === "parent"
      ? (currentLang === "am" ? "የወላጅ ዳሽቦርድ" : "Parent Portal")
      : (userProfile.stream && userProfile.stream !== "General" ? `${userProfile.grade} · ${userProfile.stream}` : userProfile.grade);
  document.getElementById("hdrRefCount").textContent = userProfile.referral_count || 0;
  if (userProfile.is_admin) document.getElementById("refreshBtn").classList.remove("hidden");

  document.getElementById("quizCtaSub").textContent = userProfile.tier === "TRIAL"
    ? "First 10 questions open per exam"
    : "Timed past papers with automatic grading";

  const cd = userProfile.countdown;
  if (cd && cd.date) {
    const diff = Math.ceil((new Date(cd.date) - new Date()) / 86400000);
    if (diff > 0) {
      const label = t(`cd_${cd.type}`);
      const cb = document.getElementById("countdownBanner");
      cb.innerHTML = `<span><strong>${diff} ${t("days_left")}</strong> ${escapeHtml(label)}</span><span class="mono-num muted-p">${escapeHtml(cd.date)}</span>`;
      cb.classList.remove("hidden");
    }
  }

  const mb = document.getElementById("modeBanner");
  if (userProfile.launch_mode === "OPEN_LAUNCH") {
    mb.className = "mode-strip launch";
    mb.textContent = t("launch_banner");
    mb.classList.remove("hidden");
  } else if (userProfile.tier === "TRIAL") {
    mb.className = "mode-strip trial";
    mb.textContent = t("trial_banner");
    mb.classList.remove("hidden");
  } else if (userProfile.days_left !== null && userProfile.days_left <= 7) {
    mb.className = "mode-strip trial";
    mb.textContent = `${Math.max(0, userProfile.days_left)} day(s) remaining on your monthly pass.`;
    mb.classList.remove("hidden");
  } else {
    mb.classList.add("hidden");
  }
}

function buildBottomNav() {
  const nav = document.getElementById("bottomNav");
  const isParent = userProfile.role === "parent";
  const tabs = [];

  if (isParent) {
    tabs.push({ id: "tabParentHome", ico: ICONS.home, lbl: currentLang === "am" ? "ዋና" : "Home" });
  }
  tabs.push(
    { id: "tabLibrary", ico: ICONS.book, lbl: currentLang === "am" ? "መጽሐፍት" : "Library" },
    { id: "tabQuiz", ico: ICONS.quiz, lbl: currentLang === "am" ? "ፈተና" : "Quiz" },
    { id: "tabPlan", ico: ICONS.plan, lbl: currentLang === "am" ? "እቅድ" : "Plan" },
    { id: "tabMore", ico: ICONS.saved, lbl: currentLang === "am" ? "ተጨማሪ" : "Saved" },
  );
  if (userProfile.is_admin) {
    tabs.push({ id: "tabAdmin", ico: ICONS.admin, lbl: "Admin" });
  } else if (!isParent) {
    tabs.push({ id: "__ref", ico: ICONS.invite, lbl: currentLang === "am" ? "ጋብዝ" : "Invite" });
  }

  nav.innerHTML = "";
  tabs.forEach((tb) => {
    const btn = document.createElement("button");
    btn.className = "nav-btn";
    btn.dataset.tab = tb.id;
    btn.innerHTML = `<span class="nav-ico">${tb.ico}</span><span>${tb.lbl}</span>`;
    btn.onclick = () => (tb.id === "__ref" ? openReferralModal() : switchTab(tb.id));
    nav.appendChild(btn);
  });
}

function switchTab(tabId) {
  ["tabParentHome", "tabLibrary", "tabQuiz", "tabPlan", "tabMore", "tabAdmin"].forEach((id) => {
    document.getElementById(id).classList.toggle("hidden", id !== tabId);
  });
  document.querySelectorAll(".nav-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tabId);
  });
  if (tabId === "tabParentHome") renderParentDashboard();
  if (tabId === "tabQuiz") renderQuizHub();
  if (tabId === "tabPlan") loadAndRenderPlans();
  if (tabId === "tabMore") renderSavedTab();
  if (tabId === "tabAdmin") loadAdminOverview();
}

// ================= 4. VISUAL PARENT ACTIVITY DASHBOARD =================
async function renderParentDashboard() {
  const sc = document.getElementById("parentStatusCard");
  const isTrial = userProfile.tier === "TRIAL";
  sc.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
      <strong style="color:var(--navy);">${currentLang === "am" ? "የአባልነት ሁኔታ" : "Membership Status"}</strong>
      <span class="doc-tag ${isTrial ? "brass" : "teal"}">${userProfile.launch_mode === "OPEN_LAUNCH" ? "Launch Open" : userProfile.status}</span>
    </div>
    <p class="muted-p" style="margin-bottom:10px;">
      ${userProfile.sibling_discount ? "Sibling discount active (2+ children). " : ""}
      ${userProfile.days_left !== null ? `Valid for ${Math.max(0, userProfile.days_left)} more day(s).` : (isTrial ? t("trial_banner") : t("launch_banner"))}
    </p>
    <button class="btn btn-primary" style="width:100%;" onclick="switchTab('tabLibrary')">
      ${currentLang === "am" ? "መጽሐፍት እና ፈተናዎችን ክፈት" : "Open Library, Quizzes & Study Plans"}
    </button>
  `;

  if (!parentAnalytics) {
    document.getElementById("parentVisualDash").innerHTML = `<div class="surface-card"><p class="muted-p">Loading child activity...</p></div>`;
    try {
      const res = await fetchJsonSafe("/api/parent/analytics", {
        headers: { Authorization: `Bearer ${sessionToken}` },
      });
      parentAnalytics = res.children_analytics || [];
    } catch {
      parentAnalytics = [];
    }
  }

  renderParentVisualContent();
  renderParentReportsList();
}

function renderParentVisualContent() {
  const tabsEl = document.getElementById("parentChildTabs");
  const dashEl = document.getElementById("parentVisualDash");

  if (!parentAnalytics || !parentAnalytics.length) {
    tabsEl.classList.add("hidden");
    dashEl.innerHTML = `<div class="surface-card"><p class="muted-p">No linked children records found.</p></div>`;
    return;
  }

  if (parentAnalytics.length > 1) {
    tabsEl.classList.remove("hidden");
    tabsEl.innerHTML = "";
    parentAnalytics.forEach((ch, idx) => {
      const b = document.createElement("button");
      b.className = `seg-btn ${idx === selectedChildIdx ? "active" : ""}`;
      b.textContent = `${ch.student_name} (${ch.grade})`;
      b.onclick = () => { selectedChildIdx = idx; renderParentVisualContent(); };
      tabsEl.appendChild(b);
    });
  } else {
    tabsEl.classList.add("hidden");
  }

  const ch = parentAnalytics[selectedChildIdx] || parentAnalytics[0];
  const k = ch.kpis;
  const linkNote = ch.is_linked
    ? `<span class="doc-tag teal">Telegram Connected</span>`
    : (ch.is_shared_phone ? `<span class="doc-tag brass">Shared Device Tracking</span>` : `<span class="doc-tag">Not Linked</span>`);

  let htmlOut = `
    <div class="surface-card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;">
        <strong style="color:var(--navy);">${escapeHtml(ch.student_name)}</strong>
        ${linkNote}
      </div>
      <div class="meta-line" style="margin-bottom:${!ch.is_linked && ch.invite_url ? "10px" : "0"};">
        ${escapeHtml(ch.grade)}${ch.stream && ch.stream !== "General" ? ` · ${escapeHtml(ch.stream)}` : ""} · ${escapeHtml(ch.format)}
      </div>
      ${!ch.is_linked && ch.invite_url ? `
        <div class="actions">
          <button class="btn btn-primary" onclick="shareChildInvite(${selectedChildIdx})">Send Child Invite Link</button>
          <button class="btn btn-secondary" onclick="copyChildInvite(${selectedChildIdx})">Copy Link</button>
        </div>
      ` : ""}
    </div>

    <div class="kpi-grid">
      <div class="kpi-cell">
        <div class="kpi-val">${k.pdfs_opened}</div>
        <div class="kpi-lbl">${currentLang === "am" ? "የተከፈቱ መጽሐፍት" : "PDFs Opened"}</div>
        <div class="kpi-sub">${k.total_views} total opens</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">${k.quizzes_taken}</div>
        <div class="kpi-lbl">${currentLang === "am" ? "የተሰሩ ፈተናዎች" : "Quizzes Taken"}</div>
        <div class="kpi-sub">${k.avg_quiz_pct !== null ? `${k.avg_quiz_pct}% avg` : "No quizzes yet"}</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">${k.bookmarks_count}</div>
        <div class="kpi-lbl">${currentLang === "am" ? "ምልክት የተደረጉ" : "Bookmarks"}</div>
        <div class="kpi-sub">${k.offline_saved} saved offline</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">${k.plan_pct}%</div>
        <div class="kpi-lbl">${currentLang === "am" ? "የጥናት እቅድ" : "Study Plan"}</div>
        <div class="kpi-sub">${k.plan_done} / ${k.plan_total} tasks</div>
      </div>
    </div>
  `;

  htmlOut += buildQuizTrendSvgCard(ch.quiz_trend, k.quiz_delta_pct);

  if (ch.subject_stats && ch.subject_stats.length) {
    const maxAct = Math.max(...ch.subject_stats.map((s) => s.views + s.quizzes), 1);
    const rowsHtml = ch.subject_stats.map((s) => {
      const widthPct = Math.max(8, Math.round(((s.views + s.quizzes) / maxAct) * 100));
      const rightTxt = s.avg_pct !== null ? `${s.views} opens · Avg ${s.avg_pct}%` : `${s.views} opens`;
      return `
        <div class="subj-row">
          <div class="subj-top"><strong>${escapeHtml(s.subject)}</strong><span class="mono-num muted-p">${rightTxt}</span></div>
          <div class="bar-track"><div class="bar-fill ${s.avg_pct !== null ? "teal" : ""}" style="width:${widthPct}%;"></div></div>
        </div>
      `;
    }).join("");
    htmlOut += `
      <div class="chart-card">
        <div class="chart-head"><h4>${currentLang === "am" ? "የትምህርት ክፍፍል" : "Activity by Subject"}</h4></div>
        ${rowsHtml}
      </div>
    `;
  }

  const maxDay = Math.max(...ch.daily_7d.map((d) => d.count), 1);
  const weekCols = ch.daily_7d.map((d) => {
    const hPct = d.count > 0 ? Math.max(15, Math.round((d.count / maxDay) * 100)) : 5;
    return `
      <div class="week-col">
        <span class="week-cnt">${d.count || ""}</span>
        <div class="week-bar-wrap"><div class="week-bar" style="height:${hPct}%;opacity:${d.count > 0 ? 1 : 0.25};"></div></div>
        <span class="week-lbl">${d.day}</span>
      </div>
    `;
  }).join("");
  htmlOut += `
    <div class="chart-card">
      <div class="chart-head"><h4>${currentLang === "am" ? "የ7 ቀናት የጥናት እንቅስቃሴ" : "Last 7 Days Study Activity"}</h4></div>
      <div class="week-grid">${weekCols}</div>
    </div>
  `;

  if (ch.recent_reads.length || ch.bookmarked_docs.length) {
    const readRows = ch.recent_reads.map((r) => `
      <div class="ledger-item">
        <span>${escapeHtml(r.file_name)} <span class="muted-p">(${escapeHtml(r.subject)})</span></span>
        <span class="doc-tag brass mono-num">p.${r.page}</span>
      </div>
    `).join("");

    const bmRows = ch.bookmarked_docs.map((b) => `
      <div class="ledger-item">
        <span>${escapeHtml(b.file_name)}</span>
        <span class="doc-tag">${escapeHtml(b.subject)}</span>
      </div>
    `).join("");

    htmlOut += `
      <div class="chart-card">
        ${ch.recent_reads.length ? `<div class="chart-head"><h4>Currently Reading</h4></div><div class="ledger-list" style="margin-bottom:${ch.bookmarked_docs.length ? "12px" : "0"};">${readRows}</div>` : ""}
        ${ch.bookmarked_docs.length ? `<div class="chart-head"><h4>Bookmarked Materials</h4></div><div class="ledger-list">${bmRows}</div>` : ""}
      </div>
    `;
  }

  dashEl.innerHTML = htmlOut;
}

function buildQuizTrendSvgCard(trend, deltaPct) {
  const title = currentLang === "am" ? "የፈተና ውጤት መሻሻል" : "Quiz Score Trend";
  if (!trend || !trend.length) {
    return `
      <div class="chart-card">
        <div class="chart-head"><h4>${title}</h4></div>
        <p class="muted-p">No graded quizzes recorded yet. Once your child submits a Bubble-Sheet quiz, their score progress appears here.</p>
      </div>
    `;
  }

  if (trend.length === 1) {
    const q = trend[0];
    return `
      <div class="chart-card">
        <div class="chart-head"><h4>${title}</h4><span class="doc-tag mono-num">${q.pct}%</span></div>
        <p class="muted-p">First quiz completed: <strong>${escapeHtml(q.subject)}</strong> (${escapeHtml(q.score_text)}). Take one more quiz to plot improvement over time.</p>
      </div>
    `;
  }

  const W = 300, H = 98, padX = 18, padY = 14;
  const pts = trend.map((q, i) => {
    const x = padX + (i / (trend.length - 1)) * (W - padX * 2);
    const y = padY + ((100 - q.pct) / 100) * (H - padY * 2);
    return { x: x.toFixed(1), y: y.toFixed(1), pct: q.pct };
  });
  const polyPoints = pts.map((p) => `${p.x},${p.y}`).join(" ");
  const areaPoints = `${pts[0].x},${H - padY} ${polyPoints} ${pts[pts.length - 1].x},${H - padY}`;
  const deltaClass = deltaPct >= 0 ? "up" : "down";
  const deltaTxt = deltaPct >= 0 ? `+${deltaPct}%` : `${deltaPct}%`;

  const dots = pts.map((p) => `
    <circle cx="${p.x}" cy="${p.y}" r="4" fill="#2563eb" stroke="#ffffff" stroke-width="2" />
    <text x="${p.x}" y="${Number(p.y) - 8}" text-anchor="middle" fill="#0f2342" font-size="9" font-weight="700" font-family="JetBrains Mono">${Math.round(p.pct)}%</text>
  `).join("");

  return `
    <div class="chart-card">
      <div class="chart-head">
        <h4>${title} (${trend.length} quizzes)</h4>
        <span class="chart-delta ${deltaClass}">${deltaTxt}</span>
      </div>
      <svg class="svg-chart" viewBox="0 0 ${W} ${H}">
        <defs>
          <linearGradient id="qAreaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#2563eb" stop-opacity="0.22" />
            <stop offset="100%" stop-color="#2563eb" stop-opacity="0.0" />
          </linearGradient>
        </defs>
        <line x1="${padX}" y1="${padY}" x2="${W - padX}" y2="${padY}" stroke="#e2e8f0" stroke-dasharray="3 3" />
        <line x1="${padX}" y1="${H / 2}" x2="${W - padX}" y2="${H / 2}" stroke="#e2e8f0" stroke-dasharray="3 3" />
        <line x1="${padX}" y1="${H - padY}" x2="${W - padX}" y2="${H - padY}" stroke="#cbd5e1" />
        <polygon fill="url(#qAreaGrad)" points="${areaPoints}" />
        <polyline fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" points="${polyPoints}" />
        ${dots}
      </svg>
    </div>
  `;
}

function shareChildInvite(idx) {
  const ch = parentAnalytics[idx];
  if (!ch || !ch.invite_url) return;
  const txt = `Open your Qelal Learning Student Hub (${ch.grade}):`;
  const url = `https://t.me/share/url?url=${encodeURIComponent(ch.invite_url)}&text=${encodeURIComponent(txt)}`;
  if (tg && tg.openTelegramLink) tg.openTelegramLink(url);
  else window.open(url, "_blank");
}

async function copyChildInvite(idx) {
  const ch = parentAnalytics[idx];
  if (!ch || !ch.invite_url) return;
  try { await navigator.clipboard.writeText(ch.invite_url); showToast("Invite link copied."); } catch {}
}

function renderParentReportsList() {
  const rpList = document.getElementById("parentReportsList");
  rpList.innerHTML = "";
  const reports = userProfile.reports || [];
  if (!reports.length) {
    rpList.innerHTML = `
      <div class="surface-card">
        <p class="muted-p">${currentLang === "am"
          ? "የአስተባባሪ የሁለት ሳምንት ሪፖርቶች ሲለቀቁ እዚህ ይታያሉ።"
          : "Bi-weekly coordinator notes (attendance, class observations, and next focus) will appear here once published."}</p>
      </div>
    `;
    return;
  }
  reports.forEach((rp) => {
    const c = document.createElement("div");
    c.className = "report-card";
    c.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <strong style="color:var(--navy);">${escapeHtml(rp.student_name)} (${escapeHtml(rp.grade)})</strong>
        <span class="doc-tag teal">${escapeHtml(rp.period)}</span>
      </div>
      <div class="meta-line">Tutor: ${escapeHtml(rp.tutor_name || "Qelal Coordinator")}</div>
      <p style="font-size:13px;margin-bottom:4px;"><strong>Attendance:</strong> ${escapeHtml(rp.attendance)}</p>
      <p style="font-size:13px;margin-bottom:4px;"><strong>Scores:</strong> ${escapeHtml(rp.scores_text)}</p>
      <p style="font-size:13px;margin-bottom:4px;color:#15803d;"><strong>Improved:</strong> ${escapeHtml(rp.improved_note)}</p>
      <p style="font-size:13px;color:#b45309;"><strong>Next Focus:</strong> ${escapeHtml(rp.focus_note)}</p>
    `;
    rpList.appendChild(c);
  });
}

// ================= 5. ADMIN CONSOLE =================
async function loadAdminOverview() {
  try {
    adminOverview = await fetchJsonSafe("/api/admin/overview", {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    renderAdminSummary();
    renderAdminStudents();
    populateAdminReportSelect();
    populateAdminConfig();
    renderAdminTrialPicker();
  } catch (err) {
    showToast("Admin load error: " + err.message);
  }
}

function switchAdminSubTab(id, btnEl) {
  ["admStudents", "admReports", "admBroadcast", "admConfig"].forEach((s) => {
    document.getElementById(s).classList.toggle("hidden", s !== id);
  });
  document.querySelectorAll("#adminSubTabs .seg-btn").forEach((b) => b.classList.remove("active"));
  btnEl.classList.add("active");
}

function renderAdminSummary() {
  const s = adminOverview.summary;
  document.getElementById("adminSummaryGrid").innerHTML = `
    <div class="kpi-cell"><div class="kpi-val">${s.NEW || 0}</div><div class="kpi-lbl">Pending (NEW)</div><div class="kpi-sub">${s.EXPIRED || 0} in Grace</div></div>
    <div class="kpi-cell"><div class="kpi-val">${s.APPROVED || 0}</div><div class="kpi-lbl">Approved</div><div class="kpi-sub">${s.total_students} students</div></div>
    <div class="kpi-cell"><div class="kpi-val">${s.total_pdfs}</div><div class="kpi-lbl">Resources</div><div class="kpi-sub">${s.verified_links} verified pairs</div></div>
    <div class="kpi-cell"><div class="kpi-val">${s.quiz_keys}</div><div class="kpi-lbl">Quiz Keys</div><div class="kpi-sub">${s.total_referrals} referrals</div></div>
  `;
}

function renderAdminStudents() {
  if (!adminOverview) return;
  const stFilter = document.getElementById("admStatusFilter").value;
  const q = document.getElementById("admSearchInput").value.trim().toLowerCase();
  const list = document.getElementById("adminStudentList");
  list.innerHTML = "";

  const rows = adminOverview.registrations.filter((r) => {
    if (stFilter && r.status !== stFilter) return false;
    if (q && !`${r.name} ${r.phone} ${r.grade}`.toLowerCase().includes(q)) return false;
    return true;
  });

  rows.forEach((r) => {
    const tagClass = r.status === "APPROVED" ? "teal" : (r.status === "NEW" || r.status === "EXPIRED" ? "brass" : "danger");
    const daysTxt = r.days_left !== null ? (r.days_left >= 0 ? `${r.days_left}d left` : `${-r.days_left}d overdue`) : "";
    const kidsTxt = r.children.length
      ? `<div class="meta-line" style="margin-top:4px;">Children: ${r.children.map((c) => `${escapeHtml(c.name)} (${escapeHtml(c.grade)})${c.contact ? ` [${escapeHtml(c.contact)}]` : ""}`).join(", ")}</div>`
      : "";

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="card-top">
        <div class="card-title">${escapeHtml(r.name)} <span class="muted-p">(${escapeHtml(r.role)})</span></div>
        <span class="doc-tag ${tagClass}">${r.status}</span>
      </div>
      <div class="meta-line">
        ${escapeHtml(r.grade)}${r.stream !== "General" ? ` · ${escapeHtml(r.stream)}` : ""} · ${escapeHtml(r.phone)}
        ${daysTxt ? ` · <span class="mono-num">${daysTxt}</span>` : ""}
        ${r.sibling_discount ? " · Sibling Discount" : ""}
      </div>
      ${kidsTxt}
      <div class="actions"></div>
    `;

    const acts = card.querySelector(".actions");
    if (r.status === "NEW") {
      acts.appendChild(makeAdmBtn("Approve (30d)", "btn-primary", () => runAdminAction(r.tg_id, "approve")));
      acts.appendChild(makeAdmBtn("Reject", "btn-secondary", () => runAdminAction(r.tg_id, "reject")));
    } else {
      acts.appendChild(makeAdmBtn("Mark Paid (+30d)", "btn-teal", () => runAdminAction(r.tg_id, "mark_paid")));
      if (r.status !== "LEFT") {
        acts.appendChild(makeAdmBtn("Mark Left", "btn-secondary", () => runAdminAction(r.tg_id, "mark_left")));
      }
    }
    list.appendChild(card);
  });

  if (!rows.length) list.innerHTML = `<div class="surface-card"><p class="muted-p">No accounts match this filter.</p></div>`;
}

function makeAdmBtn(label, cls, onClick) {
  const b = document.createElement("button");
  b.className = `btn ${cls}`;
  b.textContent = label;
  b.onclick = onClick;
  return b;
}

async function runAdminAction(tgId, action) {
  showToast("Updating account...");
  try {
    await fetchJsonSafe("/api/admin/student-action", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
      body: JSON.stringify({ tg_id: tgId, action }),
    });
    showToast("Updated and pass delivered.");
    await loadAdminOverview();
  } catch (err) {
    showToast("Error: " + err.message);
  }
}

function populateAdminReportSelect() {
  const sel = document.getElementById("admRptStudent");
  sel.innerHTML = "";
  (adminOverview.students || []).forEach((s) => {
    const o = document.createElement("option");
    o.value = s.student_id;
    o.textContent = `${s.student_name} (${s.grade})`;
    sel.appendChild(o);
  });
}

async function adminPublishReport() {
  const payload = {
    student_id: document.getElementById("admRptStudent").value,
    period: document.getElementById("admRptPeriod").value.trim(),
    attendance: document.getElementById("admRptAttendance").value.trim(),
    scores_text: document.getElementById("admRptScores").value.trim(),
    improved_note: document.getElementById("admRptImproved").value.trim(),
    focus_note: document.getElementById("admRptFocus").value.trim(),
  };
  if (!payload.student_id || !payload.period || !payload.scores_text) {
    return showToast("Select student and enter period & scores.");
  }
  try {
    await fetchJsonSafe("/api/admin/publish-report", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
      body: JSON.stringify(payload),
    });
    ["admRptPeriod", "admRptAttendance", "admRptScores", "admRptImproved", "admRptFocus"].forEach((id) => {
      document.getElementById(id).value = "";
    });
    showToast("Report published and sent to parent.");
  } catch (err) {
    showToast("Error: " + err.message);
  }
}

async function adminSendBroadcast() {
  const target = document.getElementById("admBcTarget").value;
  const message = document.getElementById("admBcMessage").value.trim();
  if (!message) return showToast("Enter a message first.");
  if (!confirm(`Send this announcement to "${target}"?`)) return;

  try {
    const res = await fetchJsonSafe("/api/admin/broadcast", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
      body: JSON.stringify({ target, message }),
    });
    document.getElementById("admBcMessage").value = "";
    showToast(`Broadcast sent: ${res.sent} delivered (${res.failed} failed).`);
  } catch (err) {
    showToast("Error: " + err.message);
  }
}

function populateAdminConfig() {
  const c = adminOverview.config || {};
  document.getElementById("admLaunchMode").value = c.LAUNCH_MODE || "OPEN_LAUNCH";
  document.getElementById("admDateMatric").value = c.MATRIC_DATE || "";
  document.getElementById("admDateG8").value = c.GRADE8_MINISTRY_DATE || "";
  document.getElementById("admDateG6").value = c.GRADE6_MINISTRY_DATE || "";
  document.getElementById("admDateSem").value = c.SEMESTER_DATE || "";
}

async function adminSaveConfig() {
  const mode = document.getElementById("admLaunchMode").value;
  if (mode === "PAID_GATED" && adminOverview?.config?.LAUNCH_MODE === "OPEN_LAUNCH") {
    if (!confirm("End Launch Phase and restrict Pending/Left users to the 3-book Trial?")) return;
  }
  try {
    await fetchJsonSafe("/api/admin/config", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
      body: JSON.stringify({
        LAUNCH_MODE: mode,
        MATRIC_DATE: document.getElementById("admDateMatric").value,
        GRADE8_MINISTRY_DATE: document.getElementById("admDateG8").value,
        GRADE6_MINISTRY_DATE: document.getElementById("admDateG6").value,
        SEMESTER_DATE: document.getElementById("admDateSem").value,
      }),
    });
    userProfile.launch_mode = mode;
    renderHeaderAndBanners();
    showToast("Configuration updated.");
  } catch (err) {
    showToast("Error: " + err.message);
  }
}

function renderAdminTrialPicker() {
  const q = document.getElementById("admTrialSearch").value.trim().toLowerCase();
  const list = document.getElementById("admTrialList");
  list.innerHTML = "";
  const matches = allItems
    .filter((it) => !q || `${it.file_name} ${it.grade} ${it.subject}`.toLowerCase().includes(q))
    .sort((a, b) => Number(b.is_trial) - Number(a.is_trial))
    .slice(0, 20);

  matches.forEach((it) => {
    const row = document.createElement("div");
    row.className = "ledger-item";
    row.innerHTML = `
      <div style="flex:1;padding-right:8px;">
        <div style="font-weight:600;">${escapeHtml(it.file_name)}</div>
        <div class="muted-p">${escapeHtml(it.grade)} · ${escapeHtml(it.subject)}</div>
      </div>
      <button class="btn ${it.is_trial ? "btn-teal" : "btn-secondary"}" style="flex:0 0 auto;min-width:86px;padding:6px 10px;">
        ${it.is_trial ? "Trial ON" : "Set Trial"}
      </button>
    `;
    row.querySelector("button").onclick = async () => {
      try {
        await fetchJsonSafe("/api/admin/toggle-trial", {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
          body: JSON.stringify({ doc_id: it.doc_id, is_trial: !it.is_trial }),
        });
        it.is_trial = !it.is_trial;
        renderAdminTrialPicker();
      } catch (err) {
        showToast("Error: " + err.message);
      }
    };
    list.appendChild(row);
  });
}

// ================= 6. STUDENT LIBRARY, QUIZ, PLANS & SAVED =================
async function loadProgress() {
  try {
    const local = localStorage.getItem("qelal_prog");
    if (local) progress = { ...progress, ...JSON.parse(local) };
    const d = await fetchJsonSafe("/api/progress", { headers: { Authorization: `Bearer ${sessionToken}` } });
    if (d.ok) {
      progress = { bookmarks: d.bookmarks || [], last_read: d.last_read || {}, plan_progress: d.plan_progress || {}, custom_plan: d.custom_plan || [] };
      localStorage.setItem("qelal_prog", JSON.stringify(progress));
    }
  } catch {}
}

let saveProgTimer = null;
function saveProgressDebounced() {
  localStorage.setItem("qelal_prog", JSON.stringify(progress));
  clearTimeout(saveProgTimer);
  saveProgTimer = setTimeout(() => {
    fetch("/api/progress", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
      body: JSON.stringify(progress),
    }).catch(() => {});
  }, 900);
}

async function loadLibrary(forceRefresh) {
  const data = await fetchJsonSafe(forceRefresh ? "/api/library?refresh=true" : "/api/library", {
    headers: { Authorization: `Bearer ${sessionToken}` },
  });
  allItems = data.items || [];
  itemsById = {};
  allItems.forEach((it) => { itemsById[it.doc_id] = it; });

  populateSelect("gradeFilter", uniqueVals("grade"), "All Grades");
  populateSelect("streamFilter", uniqueVals("stream"), "All Streams");
  populateSelect("subjectFilter", uniqueVals("subject"), "All Subjects");
  populateSelect("categoryFilter", uniqueVals("category"), "All Categories");

  if (!forceRefresh) {
    if (userProfile.grade && uniqueVals("grade").includes(userProfile.grade)) {
      document.getElementById("gradeFilter").value = userProfile.grade;
    }
    if (userProfile.stream && userProfile.stream !== "General" && uniqueVals("stream").includes(userProfile.stream)) {
      document.getElementById("streamFilter").value = userProfile.stream;
    }
  }
  applyFilters();
}

function uniqueVals(field) { return [...new Set(allItems.map((i) => i[field]).filter(Boolean))].sort(); }
function populateSelect(id, values, label) {
  const sel = document.getElementById(id), prev = sel.value;
  sel.innerHTML = `<option value="">${label}</option>`;
  values.forEach((v) => { const o = document.createElement("option"); o.value = v; o.textContent = v; sel.appendChild(o); });
  if (values.includes(prev)) sel.value = prev;
}

function applyFilters() {
  const q = document.getElementById("searchInput").value.trim().toLowerCase();
  const g = document.getElementById("gradeFilter").value;
  const st = document.getElementById("streamFilter").value;
  const sub = document.getElementById("subjectFilter").value;
  const cat = document.getElementById("categoryFilter").value;

  filteredItems = allItems.filter((it) => {
    if (g) {
      if (g === "Grade 12" && !["Grade 12", "Grade 9-12", "Grade 11-12"].includes(it.grade)) return false;
      else if (g !== "Grade 12" && it.grade !== g) return false;
    }
    if (st && it.stream !== st && it.stream !== "General") return false;
    if (sub && it.subject !== sub) return false;
    if (cat && it.category !== cat) return false;
    if (q) {
      const hay = `${it.file_name} ${it.subject} ${it.category} ${it.year} ${it.grade} ${it.round_or_code}`.toLowerCase();
      if (!q.split(/\s+/).every((w) => hay.includes(w))) return false;
    }
    return true;
  });
  filteredItems.sort((a, b) => Number(a.locked) - Number(b.locked));
  visibleLimit = 30;
  renderCards();
}

function renderCards() {
  const list = document.getElementById("cardList");
  document.getElementById("resultCount").textContent = `${filteredItems.length} item${filteredItems.length === 1 ? "" : "s"}`;
  list.innerHTML = "";

  filteredItems.slice(0, visibleLimit).forEach((it) => {
    const card = document.createElement("div");
    card.className = `card ${it.locked ? "locked" : ""}`;
    const isStarred = progress.bookmarks.includes(it.doc_id);
    const lastPg = progress.last_read[it.doc_id]?.page;

    const metaParts = [it.grade, it.subject, it.category, it.year, it.round_or_code].filter(Boolean);
    const tags = [];
    if (it.locked) tags.push(`<span class="doc-tag danger">Member Access</span>`);
    else if (it.is_trial_pick && userProfile.tier === "TRIAL") tags.push(`<span class="doc-tag teal">Preview</span>`);
    if (it.linked_doc_id && it.category !== "Answer Sheet") tags.push(`<span class="doc-tag teal">Answer Key</span>`);
    if (it.has_quiz) tags.push(`<span class="doc-tag brass mono-num">Quiz · ${it.quiz_total_q} Qs</span>`);
    if (lastPg) tags.push(`<span class="doc-tag mono-num">Page ${lastPg}</span>`);

    card.innerHTML = `
      <div class="card-top">
        <div class="card-title">${escapeHtml(it.file_name)}</div>
        <button class="star-btn ${isStarred ? "starred" : ""}" aria-label="Bookmark">
          ${isStarred ? ICONS.starFilled : ICONS.starOutline}
        </button>
      </div>
      <div class="meta-line">${escapeHtml(metaParts.join(" · "))}</div>
      ${tags.length ? `<div class="tag-row">${tags.join("")}</div>` : ""}
      <div class="actions"></div>
    `;

    card.querySelector(".star-btn").onclick = () => {
      if (progress.bookmarks.includes(it.doc_id)) progress.bookmarks = progress.bookmarks.filter((x) => x !== it.doc_id);
      else progress.bookmarks.push(it.doc_id);
      saveProgressDebounced();
      renderCards();
    };

    const actions = card.querySelector(".actions");
    if (it.locked) {
      const unlockBtn = document.createElement("button");
      unlockBtn.className = "btn btn-locked";
      unlockBtn.textContent = currentLang === "am" ? "ምዝገባ ሲጸድቅ ይከፈታል" : "Available after approval";
      unlockBtn.onclick = () => showToast(currentLang === "am"
        ? "ለመክፈት +251 933 510 682 ላይ ይደውሉ።"
        : "Complete enrollment or call +251 933 510 682 for full access.");
      actions.appendChild(unlockBtn);
    } else {
      if (it.has_pdf) {
        const readBtn = document.createElement("button");
        readBtn.className = "btn btn-primary";
        readBtn.textContent = lastPg ? `Resume p.${lastPg}` : "Read";
        readBtn.onclick = () => openReader(it, false, false);
        actions.appendChild(readBtn);
      }
      if (it.has_quiz) {
        const qBtn = document.createElement("button");
        qBtn.className = "btn btn-secondary";
        qBtn.textContent = "Quiz";
        qBtn.onclick = () => openReader(it, false, true);
        actions.appendChild(qBtn);
      }
      if (it.linked_doc_id && itemsById[it.linked_doc_id] && it.category !== "Answer Sheet") {
        const ansBtn = document.createElement("button");
        ansBtn.className = "btn btn-teal";
        ansBtn.textContent = "Answer Key";
        ansBtn.onclick = () => openReader(it, true, false);
        actions.appendChild(ansBtn);
      }
      const sendBtn = document.createElement("button");
      sendBtn.className = "btn btn-secondary";
      sendBtn.textContent = "Offline (TG)";
      sendBtn.onclick = () => sendOfflineTelegram(it);
      actions.appendChild(sendBtn);
    }
    list.appendChild(card);
  });

  const loadMoreBtn = document.getElementById("loadMoreBtn");
  if (filteredItems.length > visibleLimit) {
    loadMoreBtn.classList.remove("hidden");
    loadMoreBtn.textContent = `Show More (${filteredItems.length - visibleLimit} left)`;
  } else loadMoreBtn.classList.add("hidden");
}

async function sendOfflineTelegram(item) {
  showToast(currentLang === "am" ? "በቴሌግራም ውስጥ በመላክ ላይ..." : "Saving protected copy inside Telegram...");
  try {
    const data = await fetchJsonSafe(`/api/file/${item.doc_id}/send`, {
      method: "POST", headers: { Authorization: `Bearer ${sessionToken}` },
    });
    if (data.ok) {
      showToast(currentLang === "am"
        ? "በቴሌግራም ተቀምጧል (ኦፍላይን ለማንበብ ብቻ)።"
        : "Saved in Telegram for offline reading (forwarding and local saving disabled).");
    } else showToast(data.message || "Could not send file.");
  } catch (err) {
    showToast("Error: " + err.message);
  }
}

function renderQuizHub() {
  const quizItems = allItems.filter((it) => it.has_quiz);
  document.getElementById("quizHubHint").textContent = userProfile.tier === "TRIAL"
    ? "Preview mode: first 10 questions per exam are open for grading."
    : `${quizItems.length} past papers have parsed answer keys ready for timed bubble-sheet practice.`;
  const list = document.getElementById("quizHubList");
  list.innerHTML = "";
  quizItems.forEach((it) => {
    const c = document.createElement("div");
    c.className = "card";
    c.innerHTML = `
      <div class="card-title">${escapeHtml(it.file_name)}</div>
      <div class="meta-line" style="margin:4px 0 10px;">${escapeHtml(it.grade)} · ${escapeHtml(it.subject)} · <span class="mono-num">${it.quiz_total_q} Questions</span></div>
      <button class="btn btn-primary" style="width:100%;">Start Timed Practice</button>
    `;
    c.querySelector("button").onclick = () => openReader(it, false, true);
    list.appendChild(c);
  });
  if (!quizItems.length) {
    list.innerHTML = `<div class="surface-card"><p class="muted-p">No parsed quiz keys yet. Run /verify_links in the admin bot to extract answer keys.</p></div>`;
  }
}

async function loadAndRenderPlans() {
  const body = document.getElementById("studyPlanBody");
  if (!cachedPlans) {
    body.innerHTML = `<div class="surface-card"><p class="muted-p">Loading study plans...</p></div>`;
    const data = await fetchJsonSafe("/api/study-plans", { headers: { Authorization: `Bearer ${sessionToken}` } });
    cachedPlans = data.plans || [];
  }

  body.innerHTML = "";
  const customCard = document.createElement("div");
  customCard.className = "plan-card";
  customCard.innerHTML = `
    <h4 style="margin-bottom:8px;color:var(--navy);">${currentLang === "am" ? "የራሴ የጥናት እቅድ" : "Custom Study Checklist"}</h4>
    <div style="display:flex;gap:6px;margin-bottom:8px;">
      <input id="customTaskInput" class="q-input" placeholder="${currentLang === "am" ? "የዛሬ ግብ ይጻፉ..." : "Add task (e.g. Biology Unit 2 + 20 Qs)"}" />
      <button id="addCustomTaskBtn" class="btn btn-primary" style="flex:0 0 auto;">Add</button>
    </div>
    <div id="customTaskList"></div>
  `;
  body.appendChild(customCard);

  const renderCustom = () => {
    const wrap = customCard.querySelector("#customTaskList");
    wrap.innerHTML = "";
    (progress.custom_plan || []).forEach((task, idx) => {
      const row = document.createElement("div");
      row.className = "task-row";
      row.innerHTML = `<input type="checkbox" ${task.done ? "checked" : ""} /><span style="flex:1;" class="${task.done ? "task-done" : ""}">${escapeHtml(task.label)}</span><button class="link-btn" style="color:var(--danger);">Remove</button>`;
      row.querySelector("input").onchange = (e) => { task.done = e.target.checked; saveProgressDebounced(); renderCustom(); };
      row.querySelector("button").onclick = () => { progress.custom_plan.splice(idx, 1); saveProgressDebounced(); renderCustom(); };
      wrap.appendChild(row);
    });
  };
  renderCustom();
  customCard.querySelector("#addCustomTaskBtn").onclick = () => {
    const inp = customCard.querySelector("#customTaskInput");
    if (!inp.value.trim()) return;
    progress.custom_plan.push({ label: inp.value.trim(), done: false });
    inp.value = "";
    saveProgressDebounced();
    renderCustom();
  };

  const sorted = [...cachedPlans].sort((a, b) => (a.stream === userProfile.stream ? -1 : 1));
  sorted.forEach((p) => {
    const done = p.tasks.filter((tk) => progress.plan_progress[tk.id]).length;
    const card = document.createElement("div");
    card.className = "plan-card";
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
        <h4 style="color:var(--navy);">${escapeHtml(p.title)}</h4>
        <span class="doc-tag teal mono-num">${done}/${p.tasks.length}</span>
      </div>
      <p class="muted-p" style="margin-bottom:8px;">${escapeHtml(p.description)}</p>
      <div class="tasks-wrap"></div>
    `;
    const wrap = card.querySelector(".tasks-wrap");
    p.tasks.forEach((tk) => {
      const row = document.createElement("div");
      row.className = "task-row";
      if (tk.locked) {
        row.innerHTML = `<span class="muted-p" style="flex:1;">${escapeHtml(tk.label)} <i>(Available after approval)</i></span>`;
      } else {
        const checked = !!progress.plan_progress[tk.id];
        row.innerHTML = `<input type="checkbox" ${checked ? "checked" : ""} /><span class="${checked ? "task-done" : ""}">${escapeHtml(tk.label)}</span>`;
        row.querySelector("input").onchange = (e) => {
          progress.plan_progress[tk.id] = e.target.checked;
          saveProgressDebounced();
          row.querySelector("span").className = e.target.checked ? "task-done" : "";
        };
      }
      wrap.appendChild(row);
    });
    body.appendChild(card);
  });
}

function renderSavedTab() {
  const body = document.getElementById("savedBody");
  body.innerHTML = `<h4 style="margin-bottom:8px;font-size:14px;color:var(--navy);">${currentLang === "am" ? "በቅርብ የተነበቡ" : "Continue Reading"}</h4>`;
  const recents = Object.entries(progress.last_read || {}).sort((a, b) => (b[1].ts || 0) - (a[1].ts || 0)).slice(0, 6);
  if (!recents.length) body.innerHTML += `<p class="muted-p" style="margin-bottom:14px;">No recently opened PDFs yet.</p>`;
  recents.forEach(([docId, info]) => {
    const it = itemsById[docId];
    if (!it || it.locked) return;
    const c = document.createElement("div");
    c.className = "surface-card";
    c.innerHTML = `<div style="font-weight:600;font-size:13px;margin-bottom:8px;color:var(--navy);">${escapeHtml(it.file_name)}</div><button class="btn btn-primary" style="width:100%;">Resume Page ${info.page}</button>`;
    c.querySelector("button").onclick = () => openReader(it, false, false, info.page);
    body.appendChild(c);
  });

  body.innerHTML += `<h4 style="margin:14px 0 8px;font-size:14px;color:var(--navy);">${currentLang === "am" ? "ምልክት የተደረገባቸው" : "Bookmarked Materials"}</h4>`;
  if (!(progress.bookmarks || []).length) body.innerHTML += `<p class="muted-p">Tap the star icon on any resource to save it here.</p>`;
  (progress.bookmarks || []).forEach((docId) => {
    const it = itemsById[docId];
    if (!it) return;
    const c = document.createElement("div");
    c.className = "surface-card";
    c.innerHTML = `<div style="font-weight:600;font-size:13px;margin-bottom:8px;color:var(--navy);">${escapeHtml(it.file_name)}</div><button class="btn btn-secondary" style="width:100%;">${it.locked ? "Member Access Required" : "Open"}</button>`;
    if (!it.locked) c.querySelector("button").onclick = () => openReader(it, false, false);
    body.appendChild(c);
  });
}

function openReferralModal() {
  document.getElementById("myRefCodeDisplay").textContent = userProfile.referral_code || "QELAL-...";
  document.getElementById("myRefCountDisplay").textContent = userProfile.referral_count || 0;
  document.getElementById("referralModal").classList.remove("hidden");
}
document.getElementById("hdrInviteBtn").onclick = openReferralModal;
document.getElementById("copyRefCodeBtn").onclick = async () => {
  try { await navigator.clipboard.writeText(userProfile.referral_code || ""); showToast("Referral code copied."); } catch {}
};
document.getElementById("shareRefTgBtn").onclick = () => {
  const code = userProfile.referral_code || "";
  const bot = userProfile.bot_username || "";
  const url = bot ? `https://t.me/${bot}?start=ref_${code}` : "";
  const txt = `Join Qelal Learning (Bishoftu) for Grades 1-12 study materials and practice quizzes. Use my referral code: ${code}`;
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(txt)}`;
  if (tg && tg.openTelegramLink) tg.openTelegramLink(shareUrl);
  else window.open(shareUrl, "_blank");
};

function openRequestModal() { document.getElementById("requestModal").classList.remove("hidden"); }
document.getElementById("submitReqBtn").onclick = async () => {
  const subject = document.getElementById("reqSubject").value.trim();
  const details = document.getElementById("reqDetails").value.trim();
  if (!details) return showToast("Please enter what material you need.");
  try {
    await fetchJsonSafe("/api/request-material", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
      body: JSON.stringify({ subject, details }),
    });
    document.getElementById("reqDetails").value = "";
    closeModal("requestModal");
    showToast("Request sent to the team.");
  } catch (err) {
    showToast("Error: " + err.message);
  }
};

// ================= 7. PROTECTED IN-APP PDF READER & BUBBLE SHEET =================
async function openReader(mainItem, startWithAnswer = false, startQuiz = false, jumpToPage = null) {
  readerMainDoc = mainItem;
  readerAnswerDoc = (mainItem.linked_doc_id && itemsById[mainItem.linked_doc_id]) ? itemsById[mainItem.linked_doc_id] : null;
  showingAnswer = startWithAnswer && !!readerAnswerDoc;
  savedMainPage = jumpToPage || progress.last_read[mainItem.doc_id]?.page || 1;
  savedAnswerPage = 1;
  zoomMultiplier = 1.0;
  document.getElementById("zoomLabel").textContent = "100%";

  document.getElementById("toggleAnswerBtn").classList.toggle("hidden", !readerAnswerDoc);
  document.getElementById("toggleQuizBtn").classList.toggle("hidden", !mainItem.has_quiz);
  document.getElementById("bubblePanel").classList.add("hidden");
  stopQuizTimer();

  document.getElementById("readerModal").classList.remove("hidden");
  await loadActiveReaderDoc();
  if (startQuiz && mainItem.has_quiz) await startBubbleSheetMode(mainItem.doc_id);
}

async function loadActiveReaderDoc() {
  const activeDoc = showingAnswer && readerAnswerDoc ? readerAnswerDoc : readerMainDoc;
  document.getElementById("readerTitle").textContent = activeDoc.file_name;

  const ansToggle = document.getElementById("toggleAnswerBtn");
  if (readerAnswerDoc) {
    ansToggle.textContent = showingAnswer ? "Exam Paper" : "Answer Key";
    ansToggle.classList.toggle("active", showingAnswer);
  }

  const loadingEl = document.getElementById("readerLoading");
  document.getElementById("readerLoadText").textContent = "Opening PDF...";
  loadingEl.classList.remove("hidden");

  try {
    const pdfLib = ensurePdfJs();
    const streamUrl = `/api/file/${activeDoc.doc_id}/stream?token=${encodeURIComponent(sessionToken)}`;
    const isLarge = (activeDoc.file_size_mb || 0) > 8;
    const pdfOpts = isLarge
      ? { url: streamUrl, rangeChunkSize: 65536, disableAutoFetch: true, disableStream: true }
      : { url: streamUrl };

    if (currentPdfDoc) try { await currentPdfDoc.destroy(); } catch {}
    try {
      currentPdfDoc = await pdfLib.getDocument(pdfOpts).promise;
    } catch (rangeErr) {
      if (!isLarge) throw rangeErr;
      currentPdfDoc = await pdfLib.getDocument({ url: streamUrl }).promise;
    }
    document.getElementById("pageCount").textContent = currentPdfDoc.numPages;
    currentPage = Math.min(showingAnswer ? savedAnswerPage : savedMainPage, currentPdfDoc.numPages);
    await renderPage(currentPage);
  } catch (err) {
    console.error("PDF load error:", err);
    document.getElementById("readerLoadText").textContent = `Could not open PDF (${err?.message || "error"}). Try Offline (TG).`;
  }
}

async function renderPage(num) {
  if (!currentPdfDoc) return;
  const loadingEl = document.getElementById("readerLoading");
  document.getElementById("readerLoadText").textContent = `Loading page ${num}...`;
  loadingEl.classList.remove("hidden");
  if (renderTask) try { renderTask.cancel(); } catch {}

  const page = await currentPdfDoc.getPage(num);
  const wrap = document.getElementById("canvasWrap");
  const baseViewport = page.getViewport({ scale: 1 });
  const scale = Math.max(0.5, (wrap.clientWidth - 20) / baseViewport.width) * zoomMultiplier;
  const dpr = window.devicePixelRatio || 1;
  const viewport = page.getViewport({ scale });
  const canvas = document.getElementById("pdfCanvas");

  canvas.width = Math.floor(viewport.width * dpr);
  canvas.height = Math.floor(viewport.height * dpr);
  canvas.style.width = `${Math.floor(viewport.width)}px`;
  canvas.style.height = `${Math.floor(viewport.height)}px`;

  renderTask = page.render({ canvasContext: canvas.getContext("2d"), transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null, viewport });
  try {
    await renderTask.promise;
    document.getElementById("pageInput").value = num;
    if (showingAnswer) savedAnswerPage = num;
    else {
      savedMainPage = num;
      progress.last_read[readerMainDoc.doc_id] = { page: num, ts: Date.now() };
      saveProgressDebounced();
    }
    wrap.scrollTop = 0;
  } catch {}
  finally { loadingEl.classList.add("hidden"); }
}

async function startBubbleSheetMode(docId) {
  const panel = document.getElementById("bubblePanel");
  if (!panel.classList.contains("hidden")) { panel.classList.add("hidden"); stopQuizTimer(); return; }
  activeQuizMeta = await fetchJsonSafe(`/api/quiz/${docId}`, { headers: { Authorization: `Bearer ${sessionToken}` } });
  quizAnswers = {};

  document.getElementById("bubbleAnsweredCount").textContent = "0";
  document.getElementById("bubbleTotalCount").textContent = activeQuizMeta.unlocked_q;
  const grid = document.getElementById("bubbleGrid");
  grid.innerHTML = "";

  if (activeQuizMeta.trial_limited) {
    const note = document.createElement("div");
    note.style.cssText = "font-size:11px;color:#fbbf24;padding:4px 0;";
    note.textContent = `Preview quiz: first ${activeQuizMeta.unlocked_q} of ${activeQuizMeta.total_q} questions open. Full exams activate after approval.`;
    grid.appendChild(note);
  }

  for (let q = 1; q <= activeQuizMeta.unlocked_q; q++) {
    const row = document.createElement("div");
    row.className = "b-row";
    row.innerHTML = `<span class="mono-num"><strong>Q${q}</strong></span><div class="b-opts"></div>`;
    const opts = row.querySelector(".b-opts");
    ["A", "B", "C", "D"].forEach((letter) => {
      const b = document.createElement("button");
      b.className = "b-opt";
      b.textContent = letter;
      b.onclick = () => {
        quizAnswers[String(q)] = letter;
        opts.querySelectorAll(".b-opt").forEach((x) => x.classList.remove("selected"));
        b.classList.add("selected");
        document.getElementById("bubbleAnsweredCount").textContent = Object.keys(quizAnswers).length;
      };
      opts.appendChild(b);
    });
    grid.appendChild(row);
  }
  panel.classList.remove("hidden");
  startQuizTimer();
}

function startQuizTimer() {
  stopQuizTimer();
  quizSeconds = 0;
  quizTimerInt = setInterval(() => {
    quizSeconds++;
    const m = String(Math.floor(quizSeconds / 60)).padStart(2, "0");
    const s = String(quizSeconds % 60).padStart(2, "0");
    document.getElementById("quizTimerText").textContent = `${m}:${s}`;
  }, 1000);
}
function stopQuizTimer() { if (quizTimerInt) { clearInterval(quizTimerInt); quizTimerInt = null; } }

document.getElementById("submitQuizBtn").onclick = async () => {
  if (!activeQuizMeta) return;
  stopQuizTimer();
  try {
    const data = await fetchJsonSafe(`/api/quiz/${activeQuizMeta.doc_id}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
      body: JSON.stringify({ answers: quizAnswers }),
    });
    const grid = document.getElementById("bubbleGrid");
    grid.innerHTML = `
      <div style="background:#1e293b;padding:10px;border-radius:8px;margin-bottom:8px;text-align:center;">
        <div class="mono-num" style="font-size:17px;font-weight:700;color:#4ade80;">Score: ${data.score} / ${data.total_graded} (${data.percentage}%)</div>
        ${data.trial_limited ? "<div style='font-size:11px;color:#fbbf24;margin-top:4px;'>Full exam grading activates after enrollment approval.</div>" : ""}
      </div>
    `;
    data.breakdown.forEach((b) => {
      const r = document.createElement("div");
      r.className = "b-row";
      r.innerHTML = `<span class="mono-num"><strong>Q${b.q}</strong></span><span class="mono-num">Yours: <strong>${b.yours}</strong></span><span class="mono-num" style="color:${b.ok ? "#4ade80" : "#f87171"};">${b.ok ? "Correct" : `Key: ${b.correct}`}</span>`;
      grid.appendChild(r);
    });
    parentAnalytics = null;
  } catch (err) {
    showToast("Error grading quiz: " + err.message);
  }
};

// Event Listeners
document.getElementById("topQuizCta").onclick = () => switchTab("tabQuiz");
["searchInput", "gradeFilter", "streamFilter", "subjectFilter", "categoryFilter"].forEach((id) => {
  document.getElementById(id).addEventListener("input", applyFilters);
  document.getElementById(id).addEventListener("change", applyFilters);
});
document.getElementById("clearFiltersBtn").onclick = () => {
  ["searchInput", "gradeFilter", "streamFilter", "subjectFilter", "categoryFilter"].forEach((id) => document.getElementById(id).value = "");
  applyFilters();
};
document.getElementById("refreshBtn").onclick = async () => { await loadLibrary(true); showToast("Library refreshed."); };
document.getElementById("loadMoreBtn").onclick = () => { visibleLimit += 30; renderCards(); };
document.getElementById("closeReaderBtn").onclick = async () => {
  stopQuizTimer();
  document.getElementById("readerModal").classList.add("hidden");
  if (currentPdfDoc) try { await currentPdfDoc.destroy(); } catch {}
  currentPdfDoc = null;
  renderCards();
};
document.getElementById("toggleAnswerBtn").onclick = async () => { showingAnswer = !showingAnswer; await loadActiveReaderDoc(); };
document.getElementById("toggleQuizBtn").onclick = () => readerMainDoc && startBubbleSheetMode(readerMainDoc.doc_id);
document.getElementById("prevPageBtn").onclick = () => { if (currentPage > 1) { currentPage--; renderPage(currentPage); } };
document.getElementById("nextPageBtn").onclick = () => { if (currentPdfDoc && currentPage < currentPdfDoc.numPages) { currentPage++; renderPage(currentPage); } };
document.getElementById("pageInput").onchange = (e) => {
  const v = parseInt(e.target.value, 10);
  if (currentPdfDoc && v >= 1 && v <= currentPdfDoc.numPages) { currentPage = v; renderPage(v); }
};
document.getElementById("zoomInBtn").onclick = () => { zoomMultiplier = Math.min(2.5, zoomMultiplier + 0.25); document.getElementById("zoomLabel").textContent = `${Math.round(zoomMultiplier * 100)}%`; renderPage(currentPage); };
document.getElementById("zoomOutBtn").onclick = () => { zoomMultiplier = Math.max(0.6, zoomMultiplier - 0.25); document.getElementById("zoomLabel").textContent = `${Math.round(zoomMultiplier * 100)}%`; renderPage(currentPage); };
document.getElementById("readerSendChatBtn").onclick = () => {
  const activeDoc = showingAnswer && readerAnswerDoc ? readerAnswerDoc : readerMainDoc;
  if (activeDoc) sendOfflineTelegram(activeDoc);
};

initApp();
