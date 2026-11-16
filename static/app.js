pdfjsLib.GlobalWorkerOptions.workerSrc =
  "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

window.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && ["s", "p", "S", "P"].includes(e.key)) {
    e.preventDefault();
  }
});

// ================= BILINGUAL STRINGS (ENGLISH / AMHARIC) =================
const I18N = {
  en: {
    who_title: "Who is registering?",
    who_sub: "Choose your profile so we tailor your dashboard and exam countdown.",
    role_student: "I am a Student",
    role_student_sub: "Books, bubble-sheet quizzes, study plans & grade countdown",
    role_parent: "I am a Parent / Guardian",
    role_parent_sub: "Progress reports, child linking, sibling discounts + full library",
    prefer_call: "Prefer phone registration? Call:",
    back: "← Back",
    lbl_student_name: "Student Full Name",
    lbl_parent_name: "Parent / Guardian Full Name",
    lbl_phone: "Active Phone Number",
    lbl_grade: "Select Grade (🎯 = National Exam)",
    lbl_stream: "Select Stream (Grades 11–12)",
    stream_nat: "🔬 Natural Science",
    stream_soc: "🌍 Social Science",
    lbl_children: "Your Children",
    add_child: "+ Add Another Child",
    sibling_msg: "🎉 Sibling Discount Unlocked! Registering 2+ children qualifies for tuition discounts on all children!",
    lbl_format: "Preferred Program",
    fmt_weekend: "Weekend Exam Cohort (Bishoftu Hub)",
    fmt_home: "1-on-1 Home Mentorship",
    fmt_digital: "Digital Study Library Only",
    lbl_ref: "Referral Code (Optional)",
    btn_submit_reg: "Complete Registration & Enter Hub",
    my_children: "👨‍👩‍👧 Registered Children",
    progress_reports: "📊 Bi-Weekly Progress Reports",
    quiz_cta_title: "Quiz Me — Interactive Bubble Sheet",
    quiz_cta_go: "Start →",
    search_ph: "Search exam, textbook, year (e.g. 2017 bio)...",
    show_all: "Show All Grades",
    quiz_hub_title: "🎯 Mock Exams & Auto-Grading",
    plan_title: "📅 Interactive Study Plans",
    plan_sub: "Track your daily chapters or build your own checklist.",
    tile_ref: "Referral Program",
    tile_req: "Request Material",
    ref_modal_title: "🎁 Study Squad Referral",
    your_ref_code: "Your Personal Referral Code",
    ref_verified_lbl: "Verified Friends Joined:",
    btn_share_tg: "🚀 Share on Telegram",
    btn_copy_code: "📋 Copy Code",
    ref_how_title: "Study Squad Perks",
    ref_how_body: "Share your code with friends in Bishoftu. When 2 friends register and get approved, you unlock Study Squad same-table seating, a bound formula folder, and tuition savings!",
    req_modal_title: "📩 Request a Material",
    req_desc: "Need a specific past exam, textbook, or answer key? Notify our team directly.",
    btn_send_req: "Send Request to Admin",
    btn_offline_tg: "🔒 Save for Offline Reading (Inside Telegram Only)",
    cd_matric_12: "until Grade 12 ESSLCE (Matric)",
    cd_ministry_8: "until Grade 8 Ministry Exam",
    cd_ministry_6: "until Grade 6 Ministry Exam",
    cd_semester: "until Semester Final Exams",
    days_left: "Days",
    launch_banner: "🎉 Launch Phase Free Access — Unlimited Library & Quizzes!",
    trial_banner: "🎁 Trial Mode: 3 Grade Books Unlocked • 300+ unlock on approval",
  },
  am: {
    who_title: "ማን ነው የሚመዘገበው?",
    who_sub: "ዳሽቦርዱን እና የፈተና ቀን ቆጠራውን ለማስተካከል ሁኔታዎን ይምረጡ።",
    role_student: "ተማሪ ነኝ",
    role_student_sub: "መጽሐፍት፣ ፈጣን ኩዊዞች፣ የጥናት እቅዶች እና የክፍልዎ ፈተና ቆጠራ",
    role_parent: "ወላጅ / አሳዳጊ ነኝ",
    role_parent_sub: "የልጆች ውጤት መከታተያ፣ የልጅ አካውንት ማገናኛ፣ የወንድማማች ቅናሽ + ሙሉ መጽሐፍት",
    prefer_call: "በስልክ መመዝገብ ይመርጣሉ? ይደውሉ:",
    back: "← ተመለስ",
    lbl_student_name: "የተማሪው ሙሉ ስም",
    lbl_parent_name: "የወላጅ / አሳዳጊ ሙሉ ስም",
    lbl_phone: "ንቁ የስልክ ቁጥር",
    lbl_grade: "ክፍል ይምረጡ (🎯 = ብሔራዊ ፈተና)",
    lbl_stream: "ዘርፍ ይምረጡ (11ኛ–12ኛ ክፍል)",
    stream_nat: "🔬 ተፈጥሮ ሳይንስ (Natural)",
    stream_soc: "🌍 ማህበራዊ ሳይንስ (Social)",
    lbl_children: "ልጆችዎ",
    add_child: "+ ሌላ ልጅ ጨምር",
    sibling_msg: "🎉 የወንድማማች/እህትማማች ቅናሽ ተከፍቷል! 2+ ልጆችን ሲያስመዘግቡ በሁሉም ላይ ቅናሽ ያገኛሉ!",
    lbl_format: "የሚፈልጉት ፕሮግራም",
    fmt_weekend: "የሳምንት መጨረሻ ማዕከል (ቢሾፍቱ)",
    fmt_home: "1-ለ-1 የቤት ውስጥ አስጠኚ",
    fmt_digital: "ዲጂታል የጥናት መጽሐፍት ብቻ",
    lbl_ref: "የግብዣ ኮድ / Referral Code (አማራጭ)",
    btn_submit_reg: "ምዝገባውን አጠናቅቅ እና ግባ",
    my_children: "👨‍👩‍👧 የተመዘገቡ ልጆች",
    progress_reports: "📊 የሁለት ሳምንት የውጤት ሪፖርቶች",
    quiz_cta_title: "ፈተና ይለማመዱ — በይነመረብ ባብል ሺት",
    quiz_cta_go: "ጀምር →",
    search_ph: "መጽሐፍ፣ ፈተና ወይም ዓመት ይፈልጉ...",
    show_all: "ሁሉንም ክፍሎች አሳይ",
    quiz_hub_title: "🎯 የፈተና ልምምድ እና አውቶማቲክ እርማት",
    plan_title: "📅 የጥናት እቅዶች",
    plan_sub: "የየቀኑን ምዕራፎች ይከታተሉ ወይም የራስዎን እቅድ ይፍጠሩ።",
    tile_ref: "የግብዣ ፕሮግራም",
    tile_req: "መጽሐፍ / ፈተና ይጠይቁ",
    ref_modal_title: "🎁 የግብዣ ፕሮግራም (Study Squad)",
    your_ref_code: "የእርስዎ የግብዣ ኮድ",
    ref_verified_lbl: "በኮድዎ የገቡ ጓደኞች:",
    btn_share_tg: "🚀 በቴሌግራም አጋራ",
    btn_copy_code: "📋 ኮዱን ቅዳ",
    ref_how_title: "የግብዣ ጥቅሞች",
    ref_how_body: "ኮድዎን በቢሾፍቱ ለሚገኙ ጓደኞችዎ ያጋሩ። 2 ጓደኞች በኮድዎ ሲመዘገቡና ሲጸድቁ የStudy Squad መቀመጫ፣ የፎርሙላ ደብተር እና የክፍያ ቅናሽ ያገኛሉ!",
    req_modal_title: "📩 መጽሐፍ / ፈተና ይጠይቁ",
    req_desc: "የፈለጉትን ፈተና ወይም መጽሐፍ ካጡ ለአስተዳዳሪው በቀጥታ ይላኩ።",
    btn_send_req: "ጥያቄውን ላክ",
    btn_offline_tg: "🔒 ኦፍላይን ለማንበብ በቴሌግራም አስቀምጥ",
    cd_matric_12: "እስከ 12ኛ ክፍል ብሔራዊ ፈተና (ESSLCE)",
    cd_ministry_8: "እስከ 8ኛ ክፍል ሚኒስትሪ ፈተና",
    cd_ministry_6: "እስከ 6ኛ ክፍል ሚኒስትሪ ፈተና",
    cd_semester: "እስከ ሴሚስተር ማጠቃለያ ፈተና",
    days_left: "ቀናት ቀሩ",
    launch_banner: "🎉 የመክፈቻ ነጻ አገልግሎት — ሁሉም መጽሐፍት እና ፈተናዎች ተከፍተዋል!",
    trial_banner: "🎁 የሙከራ አገልግሎት: 3 መጽሐፍት ተከፍተዋል • ሲጸድቅ 300+ ይከፈታሉ",
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
      ? (currentLang === "am" ? "👨‍👩‍👧 ወላጅ" : "👨‍👩‍👧 Parent")
      : (currentLang === "am" ? "🎓 ተማሪ" : "🎓 Student");
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
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ================= 1. BOOT & AUTH =================
async function initApp() {
  const urlParams = new URLSearchParams(window.location.search);
  const urlRef = urlParams.get("ref");
  if (urlRef) document.getElementById("regRefCode").value = urlRef.toUpperCase();

  try {
    const res = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ initData: tg.initData || "" }),
    });
    const raw = await res.text();
    let data = {};
    try { data = JSON.parse(raw); } catch { throw new Error(raw.slice(0, 120) || "Server error"); }

    if (!res.ok) throw new Error(data.detail || "Auth error");

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
      renderParentDashboard();
      switchTab("tabParentHome");
    } else {
      switchTab("tabLibrary");
    }
  } catch (err) {
    document.getElementById("splashView").classList.add("hidden");
    document.getElementById("outsideTitle").textContent = "Connection Error";
    document.getElementById("outsideMsg").textContent = err?.message || "Could not reach server. Please reopen the Mini App.";
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
    btn.textContent = isNat ? `${g} 🎯` : g;
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
      const label = [6, 8, 12].includes(i) ? `${g} 🎯` : g;
      gradeOpts += `<option value="${g}" ${ch.grade === g ? "selected" : ""}>${label}</option>`;
    }

    const showStream = ch.grade === "Grade 11" || ch.grade === "Grade 12";
    const childLbl = currentLang === "am" ? `ልጅ #${idx + 1}` : `Child #${idx + 1}`;
    const namePh = currentLang === "am" ? "የልጁ ሙሉ ስም" : "Child's Full Name";
    const tgPh = currentLang === "am" ? "የልጁ ቴሌግራም (@username ወይም ስልክ - አማራጭ)" : "Child's Telegram (@username or phone - optional)";

    card.innerHTML = `
      <div class="child-card-head">
        <span>${childLbl}</span>
        ${parentChildren.length > 1 ? `<button type="button" class="remove-child-btn">✕ Remove</button>` : ""}
      </div>
      <input class="q-input ch-name" style="margin-bottom:7px;" type="text" placeholder="${namePh}" value="${escapeHtml(ch.name)}" />
      <select class="q-select ch-grade" style="margin-bottom:7px;">${gradeOpts}</select>
      <select class="q-select ch-stream ${showStream ? "" : "hidden"}" style="margin-bottom:7px;">
        <option value="Natural" ${ch.stream === "Natural" ? "selected" : ""}>🔬 Natural Science</option>
        <option value="Social" ${ch.stream === "Social" ? "selected" : ""}>🌍 Social Science</option>
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
  btn.textContent = currentLang === "am" ? "በመመዝገብ ላይ..." : "Creating your hub...";

  try {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        initData: tg.initData || "",
        role: selectedRole,
        lang: currentLang,
        full_name: fullName,
        phone,
        format,
        referral_code: referralCode,
        children: payloadChildren,
      }),
    });
    const rawText = await res.text();
    let data = {};
    try { data = JSON.parse(rawText); } catch { throw new Error(rawText.slice(0, 120) || "Server error"); }
    if (!res.ok || !data.ok) {
      throw new Error(data.detail || "Registration failed");
    }

    document.getElementById("onboardingView").classList.add("hidden");
    document.getElementById("splashView").classList.remove("hidden");
    await initApp();
  } catch (err) {
    showToast("❌ " + err.message);
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
  const firstName = (userProfile.name || "Friend").split(" ")[0];
  document.getElementById("hdrGreeting").textContent = currentLang === "am" ? `ሰላም, ${firstName}` : `Hi, ${firstName}`;
  document.getElementById("hdrMeta").textContent = userProfile.role === "parent"
    ? (currentLang === "am" ? "የወላጅ ዳሽቦርድ" : "Parent Portal")
    : (userProfile.stream && userProfile.stream !== "General" ? `${userProfile.grade} • ${userProfile.stream}` : userProfile.grade);
  document.getElementById("hdrRefCount").textContent = userProfile.referral_count || 0;
  if (userProfile.is_admin) document.getElementById("refreshBtn").classList.remove("hidden");

  const cd = userProfile.countdown;
  if (cd && cd.date) {
    const diff = Math.ceil((new Date(cd.date) - new Date()) / 86400000);
    if (diff > 0) {
      const label = t(`cd_${cd.type}`);
      const cb = document.getElementById("countdownBanner");
      cb.innerHTML = `<span>⏳ <strong>${diff} ${t("days_left")}</strong> ${escapeHtml(label)}</span><span>🎯</span>`;
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
    mb.textContent = `⏰ ${Math.max(0, userProfile.days_left)} day(s) remaining on your monthly pass.`;
    mb.classList.remove("hidden");
  } else {
    mb.classList.add("hidden");
  }
}

function buildBottomNav() {
  const nav = document.getElementById("bottomNav");
  const isParent = userProfile.role === "parent";
  const tabs = isParent
    ? [
        { id: "tabParentHome", ico: "📊", lbl: currentLang === "am" ? "ዋና" : "Home" },
        { id: "tabLibrary", ico: "📚", lbl: currentLang === "am" ? "መጽሐፍት" : "Library" },
        { id: "tabQuiz", ico: "🎯", lbl: currentLang === "am" ? "ፈተና" : "Quiz" },
        { id: "tabPlan", ico: "📅", lbl: currentLang === "am" ? "እቅድ" : "Plan" },
        { id: "tabMore", ico: "⭐", lbl: currentLang === "am" ? "ተጨማሪ" : "Saved" },
      ]
    : [
        { id: "tabLibrary", ico: "📚", lbl: currentLang === "am" ? "መጽሐፍት" : "Library" },
        { id: "tabQuiz", ico: "🎯", lbl: currentLang === "am" ? "ፈተና" : "Quiz" },
        { id: "tabPlan", ico: "📅", lbl: currentLang === "am" ? "እቅድ" : "Plan" },
        { id: "tabMore", ico: "⭐", lbl: currentLang === "am" ? "ተጨማሪ" : "Saved" },
        { id: "__ref", ico: "🎁", lbl: currentLang === "am" ? "ጋብዝ" : "Invite" },
      ];

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
  ["tabParentHome", "tabLibrary", "tabQuiz", "tabPlan", "tabMore"].forEach((id) => {
    document.getElementById(id).classList.toggle("hidden", id !== tabId);
  });
  document.querySelectorAll(".nav-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tabId);
  });
  if (tabId === "tabQuiz") renderQuizHub();
  if (tabId === "tabPlan") loadAndRenderPlans();
  if (tabId === "tabMore") renderSavedTab();
}

// ================= 4. PARENT PROGRESS DASHBOARD =================
function renderParentDashboard() {
  const sc = document.getElementById("parentStatusCard");
  const isTrial = userProfile.tier === "TRIAL";
  sc.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
      <strong>${currentLang === "am" ? "የአባልነት ሁኔታ" : "Membership Status"}</strong>
      <span class="badge ${isTrial ? "gold" : "green"}">${userProfile.launch_mode === "OPEN_LAUNCH" ? "FREE LAUNCH" : userProfile.status}</span>
    </div>
    <p class="muted-p" style="margin-bottom:8px;">
      ${userProfile.sibling_discount ? "🎉 <b>Sibling Discount Active</b> (2+ Children)<br/>" : ""}
      ${userProfile.days_left !== null ? `⏳ Valid for <b>${Math.max(0, userProfile.days_left)}</b> more day(s)` : (isTrial ? t("trial_banner") : t("launch_banner"))}
    </p>
    <button class="btn btn-primary" style="width:100%;" onclick="switchTab('tabLibrary')">
      ${currentLang === "am" ? "📚 ሁሉንም መጽሐፍት እና ፈተናዎች ክፈት" : "📚 Explore Library, Quizzes & Study Plans"}
    </button>
  `;

  const chList = document.getElementById("parentChildrenList");
  chList.innerHTML = "";
  (userProfile.children || []).forEach((ch) => {
    const card = document.createElement("div");
    card.className = "child-dash-card";
    const linkedBadge = ch.is_linked
      ? `<span class="badge green">✅ Telegram Linked</span>`
      : `<span class="badge gold">⏳ Not Linked</span>`;
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <strong>🎓 ${escapeHtml(ch.student_name)}</strong>
        ${linkedBadge}
      </div>
      <div class="badges" style="margin-bottom:8px;">
        <span class="badge">${escapeHtml(ch.grade)}</span>
        ${ch.stream && ch.stream !== "General" ? `<span class="badge">${escapeHtml(ch.stream)}</span>` : ""}
        <span class="badge gray">${escapeHtml(ch.format)}</span>
      </div>
      ${!ch.is_linked && ch.invite_url ? `
        <div class="actions">
          <button class="btn btn-primary share-ch-btn">📲 Send Child Invite Link</button>
          <button class="btn btn-secondary copy-ch-btn">📋 Copy</button>
        </div>
      ` : ""}
    `;
    const shareBtn = card.querySelector(".share-ch-btn");
    if (shareBtn) {
      shareBtn.onclick = () => {
        const txt = `Tap this link to open your Qelal Learning Student Hub (${ch.grade}):`;
        tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(ch.invite_url)}&text=${encodeURIComponent(txt)}`);
      };
      card.querySelector(".copy-ch-btn").onclick = async () => {
        try { await navigator.clipboard.writeText(ch.invite_url); showToast("📋 Invite link copied!"); } catch {}
      };
    }
    chList.appendChild(card);
  });

  const rpList = document.getElementById("parentReportsList");
  rpList.innerHTML = "";
  const reports = userProfile.reports || [];
  if (!reports.length) {
    rpList.innerHTML = `
      <div class="surface-card">
        <p class="muted-p">${currentLang === "am"
          ? "የልጆችዎ የሁለት ሳምንት የውጤት ሪፖርቶች ሲዘጋጁ እዚህ ይታያሉ።"
          : "No published progress reports yet. Bi-weekly attendance & quiz progress reports will appear here automatically once reviewed by Qelal."}</p>
      </div>
    `;
    return;
  }
  reports.forEach((rp) => {
    const c = document.createElement("div");
    c.className = "report-card";
    c.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <strong>${escapeHtml(rp.student_name)} (${escapeHtml(rp.grade)})</strong>
        <span class="badge green">${escapeHtml(rp.period)}</span>
      </div>
      <p style="font-size:13px;margin-bottom:4px;"><b>✅ Attendance:</b> ${escapeHtml(rp.attendance)}</p>
      <p style="font-size:13px;margin-bottom:4px;"><b>📈 Scores:</b> ${escapeHtml(rp.scores_text)}</p>
      <p style="font-size:13px;margin-bottom:4px;color:#4ade80;"><b>🔼 Improved:</b> ${escapeHtml(rp.improved_note)}</p>
      <p style="font-size:13px;color:var(--gold);"><b>🎯 Next Focus:</b> ${escapeHtml(rp.focus_note)}</p>
    `;
    rpList.appendChild(c);
  });
}

// ================= 5. LIBRARY, FILTERS & PROGRESS =================
async function loadProgress() {
  try {
    const local = localStorage.getItem("qelal_prog");
    if (local) progress = { ...progress, ...JSON.parse(local) };
    const res = await fetch("/api/progress", { headers: { Authorization: `Bearer ${sessionToken}` } });
    const d = await res.json();
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
  const res = await fetch(forceRefresh ? "/api/library?refresh=true" : "/api/library", {
    headers: { Authorization: `Bearer ${sessionToken}` },
  });
  const data = await res.json();
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
  document.getElementById("resultCount").textContent = `${filteredItems.length} resource${filteredItems.length === 1 ? "" : "s"}`;
  list.innerHTML = "";

  filteredItems.slice(0, visibleLimit).forEach((it) => {
    const card = document.createElement("div");
    card.className = `card ${it.locked ? "locked" : ""}`;
    const isStarred = progress.bookmarks.includes(it.doc_id);
    const lastPg = progress.last_read[it.doc_id]?.page;

    const badges = [
      it.locked ? `<span class="badge red">🔒 Locked</span>` : (it.is_trial_pick && userProfile.tier === "TRIAL" ? `<span class="badge green">🎁 Free Trial</span>` : ""),
      it.grade ? `<span class="badge">${escapeHtml(it.grade)}</span>` : "",
      it.subject ? `<span class="badge">${escapeHtml(it.subject)}</span>` : "",
      it.category ? `<span class="badge gray">${escapeHtml(it.category)}</span>` : "",
      it.year ? `<span class="badge gold">${escapeHtml(it.year)}</span>` : "",
      it.linked_doc_id && it.category !== "Answer Sheet" ? `<span class="badge green">🔑 Answer Key</span>` : "",
      it.has_quiz ? `<span class="badge" style="background:rgba(139,92,246,0.18);color:#a78bfa;">🎯 Quiz (${it.quiz_total_q} Qs)</span>` : "",
      lastPg ? `<span class="badge gold">📖 p.${lastPg}</span>` : "",
    ].join("");

    card.innerHTML = `
      <div class="card-top">
        <div class="card-title">${escapeHtml(it.file_name)}</div>
        <button class="star-btn">${isStarred ? "⭐" : "☆"}</button>
      </div>
      <div class="badges">${badges}</div>
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
      unlockBtn.textContent = currentLang === "am" ? "🔒 ሲጸድቅ ይከፈታል (300+)" : "🔒 Unlock on Approval (300+ PDFs)";
      unlockBtn.onclick = () => showToast(currentLang === "am"
        ? "ለመክፈት እባክዎ ክፍያዎን ያጠናቅቁ ወይም +251 933 510 682 ይደውሉ።"
        : "Complete registration payment or call +251 933 510 682 to unlock!");
      actions.appendChild(unlockBtn);
    } else {
      if (it.has_pdf) {
        const readBtn = document.createElement("button");
        readBtn.className = "btn btn-primary";
        readBtn.textContent = lastPg ? `📖 Continue (p.${lastPg})` : "📖 Read Here";
        readBtn.onclick = () => openReader(it, false, false);
        actions.appendChild(readBtn);
      }
      if (it.has_quiz) {
        const qBtn = document.createElement("button");
        qBtn.className = "btn btn-quiz";
        qBtn.textContent = "🎯 Quiz Me";
        qBtn.onclick = () => openReader(it, false, true);
        actions.appendChild(qBtn);
      }
      if (it.linked_doc_id && itemsById[it.linked_doc_id] && it.category !== "Answer Sheet") {
        const ansBtn = document.createElement("button");
        ansBtn.className = "btn btn-answer";
        ansBtn.textContent = "🔑 Answer";
        ansBtn.onclick = () => openReader(it, true, false);
        actions.appendChild(ansBtn);
      }
      const sendBtn = document.createElement("button");
      sendBtn.className = "btn btn-secondary";
      sendBtn.textContent = "🔒 Offline (TG)";
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
    const res = await fetch(`/api/file/${item.doc_id}/send`, {
      method: "POST", headers: { Authorization: `Bearer ${sessionToken}` },
    });
    const data = await res.json();
    if (data.ok) {
      showToast(currentLang === "am"
        ? "🔒 በቴሌግራም ተቀምጧል (ኦፍላይን ለማንበብ ብቻ — አይላክም)!"
        : "🔒 Saved inside Telegram (Offline reading only — cannot be forwarded or saved locally)!");
    } else showToast(data.message || "Could not send file.");
  } catch {
    showToast("❌ Network error.");
  }
}

// ================= 6. QUIZ HUB, STUDY PLANS, SAVED, REFERRAL & REQUEST =================
function renderQuizHub() {
  const quizItems = allItems.filter((it) => it.has_quiz);
  document.getElementById("quizHubHint").textContent = userProfile.tier === "TRIAL"
    ? "Trial Mode: First 10 questions per exam unlocked. Full 100+ Q exams unlock on approval!"
    : `${quizItems.length} interactive mock exams ready. Tap any exam to launch Bubble Sheet + Timer!`;
  const list = document.getElementById("quizHubList");
  list.innerHTML = "";
  quizItems.forEach((it) => {
    const c = document.createElement("div");
    c.className = "card";
    c.innerHTML = `
      <div class="card-title">${escapeHtml(it.file_name)}</div>
      <div class="badges">
        <span class="badge">${escapeHtml(it.grade)}</span>
        <span class="badge">${escapeHtml(it.subject)}</span>
        <span class="badge gold">🎯 ${it.quiz_total_q} Questions</span>
      </div>
      <button class="btn btn-quiz" style="width:100%;">🚀 Start Bubble-Sheet Practice</button>
    `;
    c.querySelector("button").onclick = () => openReader(it, false, true);
    list.appendChild(c);
  });
  if (!quizItems.length) {
    list.innerHTML = `<div class="surface-card"><p class="muted-p">No parsed quiz keys yet — Admin can run /verify_links to extract answer keys!</p></div>`;
  }
}

async function loadAndRenderPlans() {
  const body = document.getElementById("studyPlanBody");
  if (!cachedPlans) {
    body.innerHTML = `<div class="surface-card"><p class="muted-p">Loading study plans...</p></div>`;
    const res = await fetch("/api/study-plans", { headers: { Authorization: `Bearer ${sessionToken}` } });
    const data = await res.json();
    cachedPlans = data.plans || [];
  }

  body.innerHTML = "";
  const customCard = document.createElement("div");
  customCard.className = "plan-card";
  customCard.innerHTML = `
    <h4 style="margin-bottom:8px;">✍️ ${currentLang === "am" ? "የራሴ የጥናት እቅድ" : "My Custom Study Plan"}</h4>
    <div style="display:flex;gap:6px;margin-bottom:8px;">
      <input id="customTaskInput" class="q-input" placeholder="${currentLang === "am" ? "የዛሬ ግብ ይጻፉ..." : "Add daily goal (e.g. Bio Unit 2 + 20 Qs)"}" />
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
      row.innerHTML = `<input type="checkbox" ${task.done ? "checked" : ""} /><span style="flex:1;" class="${task.done ? "task-done" : ""}">${escapeHtml(task.label)}</span><button class="link-btn" style="color:#f87171;">✕</button>`;
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
        <h4>${escapeHtml(p.title)}</h4>
        <span class="badge green">${done}/${p.tasks.length}</span>
      </div>
      <p class="muted-p" style="margin-bottom:8px;">${escapeHtml(p.description)}</p>
      <div class="tasks-wrap"></div>
    `;
    const wrap = card.querySelector(".tasks-wrap");
    p.tasks.forEach((tk) => {
      const row = document.createElement("div");
      row.className = "task-row";
      if (tk.locked) {
        row.innerHTML = `<span>🔒</span><span class="muted-p" style="flex:1;">${escapeHtml(tk.label)} <i>(Unlock on Approval)</i></span>`;
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
  body.innerHTML = `<h4 style="margin-bottom:8px;">🕒 ${currentLang === "am" ? "በቅርብ የተነበቡ" : "Continue Reading"}</h4>`;
  const recents = Object.entries(progress.last_read || {}).sort((a, b) => (b[1].ts || 0) - (a[1].ts || 0)).slice(0, 6);
  if (!recents.length) body.innerHTML += `<p class="muted-p" style="margin-bottom:14px;">No recently opened PDFs yet.</p>`;
  recents.forEach(([docId, info]) => {
    const it = itemsById[docId];
    if (!it || it.locked) return;
    const c = document.createElement("div");
    c.className = "surface-card";
    c.innerHTML = `<div style="font-weight:600;font-size:13px;margin-bottom:8px;">${escapeHtml(it.file_name)}</div><button class="btn btn-primary" style="width:100%;">📖 Resume Page ${info.page}</button>`;
    c.querySelector("button").onclick = () => openReader(it, false, false, info.page);
    body.appendChild(c);
  });

  body.innerHTML += `<h4 style="margin:14px 0 8px;">⭐ ${currentLang === "am" ? "ምልክት የተደረገባቸው" : "Bookmarked Resources"}</h4>`;
  if (!(progress.bookmarks || []).length) body.innerHTML += `<p class="muted-p">Tap ☆ on any book to bookmark it here.</p>`;
  (progress.bookmarks || []).forEach((docId) => {
    const it = itemsById[docId];
    if (!it) return;
    const c = document.createElement("div");
    c.className = "surface-card";
    c.innerHTML = `<div style="font-weight:600;font-size:13px;margin-bottom:8px;">${escapeHtml(it.file_name)}</div><button class="btn btn-secondary" style="width:100%;">${it.locked ? "🔒 Locked" : "📖 Open"}</button>`;
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
  try { await navigator.clipboard.writeText(userProfile.referral_code || ""); showToast("📋 Referral code copied!"); } catch {}
};
document.getElementById("shareRefTgBtn").onclick = () => {
  const code = userProfile.referral_code || "";
  const bot = userProfile.bot_username || "";
  const url = bot ? `https://t.me/${bot}?start=ref_${code}` : "";
  const txt = `Join me at Qelal Learning (Bishoftu) for Grades 1-12 Exam Prep, Notes & Quizzes! Use my code: ${code}`;
  tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(txt)}`);
};

function openRequestModal() { document.getElementById("requestModal").classList.remove("hidden"); }
document.getElementById("submitReqBtn").onclick = async () => {
  const subject = document.getElementById("reqSubject").value.trim();
  const details = document.getElementById("reqDetails").value.trim();
  if (!details) return showToast("Please describe what you need.");
  const res = await fetch("/api/request-material", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
    body: JSON.stringify({ subject, details }),
  });
  if ((await res.json()).ok) {
    document.getElementById("reqDetails").value = "";
    closeModal("requestModal");
    showToast("✅ Request sent to admin!");
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
    ansToggle.textContent = showingAnswer ? "📄 Exam" : "🔑 Key";
    ansToggle.classList.toggle("active", showingAnswer);
  }

  const loadingEl = document.getElementById("readerLoading");
  document.getElementById("readerLoadText").textContent = "Opening PDF...";
  loadingEl.classList.remove("hidden");

  const streamUrl = `/api/file/${activeDoc.doc_id}/stream?token=${encodeURIComponent(sessionToken)}`;
  const isLarge = (activeDoc.file_size_mb || 0) > 8;
  const pdfOpts = isLarge
    ? { url: streamUrl, rangeChunkSize: 65536, disableAutoFetch: true, disableStream: true }
    : { url: streamUrl };

  try {
    if (currentPdfDoc) try { await currentPdfDoc.destroy(); } catch {}
    try {
      currentPdfDoc = await pdfjsLib.getDocument(pdfOpts).promise;
    } catch (rangeErr) {
      if (!isLarge) throw rangeErr;
      currentPdfDoc = await pdfjsLib.getDocument({ url: streamUrl }).promise;
    }
    document.getElementById("pageCount").textContent = currentPdfDoc.numPages;
    currentPage = Math.min(showingAnswer ? savedAnswerPage : savedMainPage, currentPdfDoc.numPages);
    await renderPage(currentPage);
  } catch (err) {
    console.error("PDF load error:", err);
    document.getElementById("readerLoadText").textContent = `Could not open PDF (${err?.message || "error"}). Try 'Offline (TG)'.`;
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
  const res = await fetch(`/api/quiz/${docId}`, { headers: { Authorization: `Bearer ${sessionToken}` } });
  activeQuizMeta = await res.json();
  quizAnswers = {};

  document.getElementById("bubbleAnsweredCount").textContent = "0";
  document.getElementById("bubbleTotalCount").textContent = activeQuizMeta.unlocked_q;
  const grid = document.getElementById("bubbleGrid");
  grid.innerHTML = "";

  if (activeQuizMeta.trial_limited) {
    const note = document.createElement("div");
    note.style.cssText = "font-size:11px;color:#fbbf24;padding:4px 0;";
    note.textContent = `🎁 Trial Quiz: First ${activeQuizMeta.unlocked_q} of ${activeQuizMeta.total_q} questions unlocked. Complete approval for full exams!`;
    grid.appendChild(note);
  }

  for (let q = 1; q <= activeQuizMeta.unlocked_q; q++) {
    const row = document.createElement("div");
    row.className = "b-row";
    row.innerHTML = `<span><b>Q${q}</b></span><div class="b-opts"></div>`;
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
  const res = await fetch(`/api/quiz/${activeQuizMeta.doc_id}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken}` },
    body: JSON.stringify({ answers: quizAnswers }),
  });
  const data = await res.json();
  const grid = document.getElementById("bubbleGrid");
  grid.innerHTML = `
    <div style="background:#1e293b;padding:10px;border-radius:10px;margin-bottom:8px;text-align:center;">
      <div style="font-size:18px;font-weight:800;color:#4ade80;">Score: ${data.score} / ${data.total_graded} (${data.percentage}%)</div>
      ${data.trial_limited ? "<div style='font-size:11px;color:#fbbf24;margin-top:4px;'>Upgrade after approval to grade all 100+ questions!</div>" : ""}
    </div>
  `;
  data.breakdown.forEach((b) => {
    const r = document.createElement("div");
    r.className = "b-row";
    r.innerHTML = `<span><b>Q${b.q}</b></span><span>Yours: <b>${b.yours}</b></span><span style="color:${b.ok ? "#4ade80" : "#f87171"};">${b.ok ? "✅ Correct" : `❌ Key: ${b.correct}`}</span>`;
    grid.appendChild(r);
  });
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
document.getElementById("refreshBtn").onclick = async () => { await loadLibrary(true); showToast("✅ Refreshed!"); };
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
