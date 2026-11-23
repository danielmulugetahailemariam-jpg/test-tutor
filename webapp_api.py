(function () {
  "use strict";

  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try {
      tg.ready();
      tg.expand();
      if (typeof tg.setHeaderColor === "function") tg.setHeaderColor("#0F2342");
      if (typeof tg.setBackgroundColor === "function") tg.setBackgroundColor("#F5F3EE");
    } catch (_) {}
  }

  if (window.pdfjsLib) {
    window.pdfjsLib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
  }

  const GRADES = [
    "Grade 1", "Grade 2", "Grade 3",
    "Grade 4", "Grade 5", "Grade 6",
    "Grade 7", "Grade 8", "Grade 9",
    "Grade 10", "Grade 11", "Grade 12",
  ];

  // ==================== TRILINGUAL DICTIONARY (EN / AM / OM) ====================
  const I18N = {
    en: {
      brandSub: "Bishoftu Study & Exam Hub",
      loading: "Opening Qelal Learning...",
      outsideTitle: "Open inside Telegram",
      outsideBody:
        "This study portal runs inside Telegram so your reading progress, practice quizzes, and family dashboard stay connected. Open the Qelal Learning bot in Telegram and send /start.",
      retry: "Try again",
      regSub: "Bishoftu Study & Exam Hub · Grades 1–12",
      regLangLabel: "Select your language",
      regIntro:
        "Register once to read textbooks and past national exams, check quiz answers automatically, and reserve a seat for weekend coaching or 1-on-1 home tutoring in Bishoftu.",
      regRolePrompt: "Who is registering?",
      roleStudent: "Student",
      roleParent: "Parent / Guardian",
      fullNameStudent: "Student full name",
      fullNameParent: "Parent / Guardian full name",
      phoneLabel: "Phone number",
      gradeLevel: "Grade level (1–12)",
      examTag68: "Ministry Exam",
      examTag12: "National Exam",
      streamLabel: "Academic stream",
      streamNatural: "Natural Science",
      streamSocial: "Social Science",
      formatStudentLabel: "Preferred study format",
      formatParentLabel: "Default study format",
      formatWeekend: "Weekend Study Hub",
      formatHome: "1-on-1 Home Tutoring",
      childrenHeading: "Children",
      addChild: "+ Add another child",
      removeChild: "Remove",
      childCardTitle: "Child",
      childNameLabel: "Child's full name",
      childContactLabel: "Child's Telegram @username or phone (optional)",
      childContactHint:
        "If your child uses Telegram, enter their @username or phone number so their account links automatically without duplicates.",
      siblingDiscountNote:
        "Sibling discount applies automatically when 2 or more children are registered.",
      refLabel: "Referral or Study Squad code (optional)",
      legalPrefix: "By registering, you agree to Qelal Learning's",
      legalTerms: "Enrollment Terms",
      legalAnd: "and",
      legalPrivacy: "Privacy Policy",
      submitReg: "Complete registration",
      submitting: "Saving...",
      errNamePhone: "Please enter both full name and phone number.",
      errChildName: "Please enter a name for every child.",
      errGeneric: "Registration could not be completed. Please try again.",
      gradeWord: "Grade",
      navParent: "Child Progress",
      navLibrary: "Library",
      navPlans: "Study Plans",
      navAccount: "Account",
      navAdmin: "Admin",
      countdownMatric: "Grade 12 National Exam",
      countdownG8: "Grade 8 Ministry Exam",
      countdownG6: "Grade 6 Ministry Exam",
      countdownSem: "Semester Exam Target",
      daysLeftUnit: "days left",
      targetDate: "Target date",
      trialBanner:
        "Trial mode: 3 starter books for your grade and the first 10 questions of each quiz are open. Call +251 933 510 682 or +251 988 666 328 to activate full membership.",
      continueReading: "Continue reading",
      pageWord: "Page",
      searchPlaceholder: "Search books, exams, subjects...",
      allGrades: "All grades",
      myGrade: "My grade",
      allSubjects: "All subjects",
      allCategories: "All categories",
      savedBtn: "Saved",
      showingDocs: "resources",
      noDocsMatch: "No study materials matched your filters.",
      readPdf: "Read PDF",
      takeQuiz: "Quiz",
      quizPreview: "10-Q Quiz Preview",
      answerSheet: "Answer Sheet",
      sendToChat: "Send to Chat",
      saveDoc: "Save",
      savedDoc: "Saved",
      lockedFull: "Full Member",
      setTrialPick: "Trial Pick: Off",
      isTrialPick: "Trial Pick: On",
      reqPrompt: "Missing a textbook or past paper?",
      reqToggle: "Request material",
      reqSubject: "Subject & grade",
      reqDetails: "Book or exam details",
      reqSend: "Send request",
      reqSent: "Request sent to Qelal team.",
      reqEmpty: "Enter details of the material you need.",
      plansTrialNote:
        "Trial mode: the first 3 tasks of each study plan are open. Full members unlock complete multi-week schedules.",
      customPlanTitle: "Personal study checklist",
      customTaskPlaceholder: "Add a topic or revision task...",
      addBtn: "Add",
      deleteBtn: "Remove",
      doneLabel: "completed",
      lockedTask: "Full Member",
      childSwitchLabel: "Select child",
      notLinkedNote:
        "This child has not opened Telegram with their own account yet. Send the link below if they have Telegram, or share this phone to use Library and Study Plans together.",
      sharedPhoneTag: "Shared phone / Not linked",
      linkedTag: "Account linked",
      copyInvite: "Copy invite link",
      shareTg: "Share in Telegram",
      copied: "Copied",
      kpiPdfs: "Books Opened",
      kpiViews: "total opens",
      kpiQuizzes: "Quizzes Taken",
      kpiAvg: "avg",
      kpiPlan: "Study Plan",
      kpiSaved: "Saved Offline",
      kpiBookmarks: "bookmarks",
      chart7d: "7-Day Study Activity",
      quizTrendTitle: "Recent Quiz Scores",
      noQuizzesYet: "No quizzes submitted yet.",
      subjBreakdownTitle: "Activity by Subject",
      subjCol: "Subject",
      viewsCol: "Opens",
      quizzesCol: "Quizzes",
      avgCol: "Avg",
      recentActivityTitle: "Recent Reading & Bookmarks",
      biweeklyReportsTitle: "Bi-Weekly Tutor Progress Reports",
      noReportsYet: "No bi-weekly reports published yet.",
      attendanceLbl: "Attendance",
      scoresLbl: "Scores",
      improvedLbl: "Improved",
      focusLbl: "Next focus",
      accountTitle: "Account & Membership",
      nameLbl: "Name",
      roleLbl: "Role",
      statusLbl: "Status",
      tierLbl: "Access Tier",
      daysRemainLbl: "Days Left",
      squadTitle: "Study Squad & Referrals",
      squadDesc:
        "Share your code with classmates or parents in Bishoftu. Referring 2 friends qualifies for Study Squad seating and bound formula folders.",
      yourCode: "Your referral code",
      verifiedRefs: "Verified referrals",
      copyCode: "Copy code",
      childrenSectionTitle: "Registered Students",
      supportTitle: "Bishoftu Center Support",
      closeBtn: "Close",
      prevBtn: "Prev",
      nextBtn: "Next",
      quizTabBubbles: "Answer Bubbles",
      quizTabPaper: "Exam Paper (PDF)",
      quizTrialBanner:
        "Trial preview: questions 1 to 10 are graded below. Activate full membership to grade the entire exam.",
      gradeMyAnswers: "Grade my answers",
      retakeQuiz: "Retake quiz",
      scoreLabel: "Score",
      yoursCol: "Yours",
      keyCol: "Key",
      pdfLoading: "Loading document...",
      pdfError: "Could not display PDF inline.",
      pdfTryFrame: "Open fallback viewer",
      sentChatOk: "Sent to your Telegram chat.",
      adminSyncTitle: "Google Drive Sync & PDF Verification",
      syncDriveBtn: "Sync Google Drive",
      verifyLinksBtn: "Verify PDF Links (40)",
      forceVerifyBtn: "Force Re-Verify",
      refreshAdminBtn: "Refresh Data",
      adminPdfTitle: "PDF Library Status",
      confirmLinkBtn: "Confirm Match",
      unlinkBtn: "Unlink",
      showMoreBtn: "Show more",
      adminConfigTitle: "System Configuration",
      saveConfig: "Save settings",
      adminPublishTitle: "Publish Bi-Weekly Progress Report",
      publishReportBtn: "Approve & Send Report",
      adminBroadcastTitle: "Send Announcement",
      sendBroadcastBtn: "Send Broadcast",
      adminAccountsTitle: "Accounts & Renewals",
      approve30d: "Approve 30d",
      renew30d: "Renew +30d",
      markLeft: "Mark Left",
      rejectBtn: "Reject",
      actionDone: "Updated successfully.",
    },
    am: {
      brandSub: "የቢሾፍቱ የጥናትና የፈተና ማዕከል",
      loading: "ቀላልን በመክፈት ላይ...",
      outsideTitle: "በቴሌግራም ውስጥ ይክፈቱ",
      outsideBody:
        "ይህ የጥናት መተግበሪያ የንባብ ሂደትዎን፣ የሙከራ ፈተናዎችንና የወላጅ መከታተያን ለማገናኘት በቴሌግራም ውስጥ ይሰራል። በቴሌግራም ውስጥ የቀላል ቦትን ከፍተው /start ይላኩ።",
      retry: "እንደገና ይሞክሩ",
      regSub: "የቢሾፍቱ የጥናትና የፈተና ማዕከል · ከ1ኛ–12ኛ ክፍል",
      regLangLabel: "ቋንቋ ይምረጡ",
      regIntro:
        "መጽሐፍትንና ያለፉ ብሔራዊ ፈተናዎችን ለማንበብ፣ ራስ-ሰር የፈተና ልምምዶችን ለመስራት እና በቢሾፍቱ የቅዳሜና እሁድ ወይም የቤት ለቤት ትምህርት ቦታ ለመያዝ አንዴ ይመዝገቡ።",
      regRolePrompt: "ማን ነው የሚመዘገበው?",
      roleStudent: "ተማሪ",
      roleParent: "ወላጅ / አሳዳጊ",
      fullNameStudent: "የተማሪው ሙሉ ስም",
      fullNameParent: "የወላጅ / አሳዳጊ ሙሉ ስም",
      phoneLabel: "ስልክ ቁጥር",
      gradeLevel: "ክፍል (1ኛ–12ኛ)",
      examTag68: "ሚኒስትሪ",
      examTag12: "ብሔራዊ ፈተና",
      streamLabel: "የትምህርት ዘርፍ",
      streamNatural: "ተፈጥሮ ሳይንስ",
      streamSocial: "ማህበራዊ ሳይንስ",
      formatStudentLabel: "የትምህርት አሰጣጥ ምርጫ",
      formatParentLabel: "ዋና የትምህርት አሰጣጥ ምርጫ",
      formatWeekend: "የቅዳሜና እሁድ ማዕከል",
      formatHome: "የቤት ለቤት 1-ለ-1",
      childrenHeading: "ልጆች",
      addChild: "+ ሌላ ልጅ ጨምር",
      removeChild: "አስወግድ",
      childCardTitle: "ልጅ",
      childNameLabel: "የልጁ ሙሉ ስም",
      childContactLabel: "የልጁ ቴሌግራም @username ወይም ስልክ (አማራጭ)",
      childContactHint:
        "ልጅዎ ቴሌግራም የሚጠቀም ከሆነ @username ወይም ስልክ ቁጥሩን ያስገቡ፤ ቦቱን ሲከፍቱ አካውንታቸው በቀጥታ ይገናኛል።",
      siblingDiscountNote:
        "2 እና ከዚያ በላይ ልጆችን ሲመዘግቡ የወንድማማች/እህትማማች ቅናሽ በቀጥታ ይታሰባል።",
      refLabel: "የግብዣ (Referral) ኮድ (አማራጭ)",
      legalPrefix: "በመመዝገብዎ የቀላልን",
      legalTerms: "የምዝገባ ውል",
      legalAnd: "እና",
      legalPrivacy: "የግላዊነት ፖሊሲ",
      submitReg: "ምዝገባውን አጠናቅቅ",
      submitting: "በመመዝገብ ላይ...",
      errNamePhone: "እባክዎ ሙሉ ስም እና ስልክ ቁጥር ያስገቡ።",
      errChildName: "እባክዎ የእያንዳንዱን ልጅ ስም ያስገቡ።",
      errGeneric: "ምዝገባው አልተሳካም። እባክዎ እንደገና ይሞክሩ።",
      gradeWord: "ክፍል",
      navParent: "የልጅ ሂደት",
      navLibrary: "ቤተ-መጽሐፍት",
      navPlans: "የጥናት እቅድ",
      navAccount: "አካውንት",
      navAdmin: "አስተዳዳሪ",
      countdownMatric: "የ12ኛ ክፍል ብሔራዊ ፈተና",
      countdownG8: "የ8ኛ ክፍል ሚኒስትሪ ፈተና",
      countdownG6: "የ6ኛ ክፍል ሚኒስትሪ ፈተና",
      countdownSem: "የሴሚስተር ፈተና ቀጠሮ",
      daysLeftUnit: "ቀናት ቀሩ",
      targetDate: "የታቀደ ቀን",
      trialBanner:
        "የሙከራ ጊዜ፡ ለክፍልዎ 3 መጽሐፍትና የእያንዳንዱ ፈተና የመጀመሪያ 10 ጥያቄዎች ተከፍተዋል። ሙሉ አገልግሎት ለማግኘት +251 933 510 682 / +251 988 666 328 ይደውሉ።",
      continueReading: "ንባብ ይቀጥሉ",
      pageWord: "ገጽ",
      searchPlaceholder: "መጽሐፍትን፣ ፈተናዎችን፣ ትምህርቶችን ይፈልጉ...",
      allGrades: "ሁሉም ክፍሎች",
      myGrade: "የኔ ክፍል",
      allSubjects: "ሁሉም ትምህርቶች",
      allCategories: "ሁሉም አይነቶች",
      savedBtn: "የተቀመጡ",
      showingDocs: "መጽሐፍት/ፋይሎች",
      noDocsMatch: "ከፍለጋዎ ጋር የሚመሳሰል ፋይል አልተገኘም።",
      readPdf: "አንብብ (PDF)",
      takeQuiz: "ፈተና ስራ",
      quizPreview: "10 ጥያቄ ሙከራ",
      answerSheet: "መልስ መመልከቻ",
      sendToChat: "ወደ ቴሌግራም ላክ",
      saveDoc: "አስቀምጥ",
      savedDoc: "ተቀምጧል",
      lockedFull: "ሙሉ አባል",
      setTrialPick: "ለሙከራ አድርግ",
      isTrialPick: "የሙከራ ምርጫ: በርቷል",
      reqPrompt: "የሚፈልጉት መጽሐፍ ወይም ፈተና ጠፋ?",
      reqToggle: "ፋይል ይጠይቁ",
      reqSubject: "ትምህርት እና ክፍል",
      reqDetails: "የመጽሐፉ ወይም የፈተናው ዝርዝር",
      reqSend: "ጥያቄ ላክ",
      reqSent: "ጥያቄዎ ለቀላል ቡድን ተልኳል።",
      reqEmpty: "እባክዎ የሚፈልጉትን ዝርዝር ይጻፉ።",
      plansTrialNote:
        "የሙከራ ጊዜ፡ የእያንዳንዱ የጥናት እቅድ የመጀመሪያ 3 ተግባራት ተከፍተዋል። ሙሉ አባላት ሙሉውን እቅድ ያገኛሉ።",
      customPlanTitle: "የግል የጥናት ዝርዝር",
      customTaskPlaceholder: "የሚጠና ርዕስ ወይም ተግባር ይጨምሩ...",
      addBtn: "ጨምር",
      deleteBtn: "አጥፋ",
      doneLabel: "ተጠናቅቋል",
      lockedTask: "ሙሉ አባል",
      childSwitchLabel: "ልጅ ይምረጡ",
      notLinkedNote:
        "ልጅዎ ገና በራሳቸው ቴሌግራም አካውንት አልገቡም። የራሳቸው ቴሌግራም ካላቸው ከታች ያለውን ሊንክ ይላኩላቸው፤ ወይም ይህንኑ ስልክ በጋራ ተጠቅመው ቤተ-መጽሐፍቱን ይክፈቱ።",
      sharedPhoneTag: "ያልተገናኘ / በጋራ ስልክ",
      linkedTag: "አካውንት ተገናኝቷል",
      copyInvite: "የግብዣ ሊንክ ቅዳ",
      shareTg: "በቴሌግራም ላክ",
      copied: "ተቀድቷል",
      kpiPdfs: "የተከፈቱ መጽሐፍት",
      kpiViews: "ጠቅላላ ንባቦች",
      kpiQuizzes: "የተሰሩ ፈተናዎች",
      kpiAvg: "አማካይ",
      kpiPlan: "የጥናት እቅድ",
      kpiSaved: "ለኦፍላይን የተላኩ",
      kpiBookmarks: "የተቀመጡ",
      chart7d: "የ7 ቀናት የጥናት እንቅስቃሴ",
      quizTrendTitle: "የቅርብ ጊዜ የፈተና ውጤቶች",
      noQuizzesYet: "እስካሁን የተሰራ የሙከራ ፈተና የለም።",
      subjBreakdownTitle: "በየትምህርቱ የተደረገ እንቅስቃሴ",
      subjCol: "ትምህርት",
      viewsCol: "ንባብ",
      quizzesCol: "ፈተና",
      avgCol: "አማካይ",
      recentActivityTitle: "የቅርብ ጊዜ ንባብ እና የተቀመጡ",
      biweeklyReportsTitle: "የሁለት ሳምንት የአስጠኚ ሪፖርቶች",
      noReportsYet: "ገና የታተመ የሁለት ሳምንት ሪፖርት የለም።",
      attendanceLbl: "ክትትል",
      scoresLbl: "ውጤቶች",
      improvedLbl: "መሻሻል",
      focusLbl: "ቀጣይ ትኩረት",
      accountTitle: "አካውንት እና አባልነት",
      nameLbl: "ስም",
      roleLbl: "ሚና",
      statusLbl: "ሁኔታ",
      tierLbl: "የአገልግሎት ደረጃ",
      daysRemainLbl: "የቀሩ ቀናት",
      squadTitle: "የጥናት ቡድን እና ግብዣ",
      squadDesc:
        "ኮድዎን በቢሾፍቱ ለሚገኙ ጓደኞች ወይም ወላጆች ያጋሩ። 2 ጓደኞችን ሲጋብዙ የጥናት ቡድን መቀመጫና የፎርሙላ ማህደር ያገኛሉ።",
      yourCode: "የእርስዎ የግብዣ ኮድ",
      verifiedRefs: "የጸደቁ ግብዣዎች",
      copyCode: "ኮድ ቅዳ",
      childrenSectionTitle: "የተመዘገቡ ልጆች",
      supportTitle: "የቢሾፍቱ ማዕከል ድጋፍ",
      closeBtn: "ዝጋ",
      prevBtn: "ቀዳሚ",
      nextBtn: "ቀጣይ",
      quizTabBubbles: "መልስ መሙያ",
      quizTabPaper: "የፈተና ወረቀት (PDF)",
      quizTrialBanner:
        "የሙከራ እይታ፡ ከ1 እስከ 10 ያሉ ጥያቄዎች ይታረማሉ። ሙሉውን ፈተና ለማረም ሙሉ አባል ይሁኑ።",
      gradeMyAnswers: "መልሶቼን አርም",
      retakeQuiz: "እንደገና ስራ",
      scoreLabel: "ውጤት",
      yoursCol: "የእርስዎ",
      keyCol: "ትክክለኛ",
      pdfLoading: "ሰነዱን በመጫን ላይ...",
      pdfError: "ፋይሉን እዚህ ማሳየት አልተቻለም።",
      pdfTryFrame: "በተለዋጭ መክፈቻ ክፈት",
      sentChatOk: "ወደ ቴሌግራም ቻትዎ ተልኳል።",
      adminSyncTitle: "የGoogle Drive እና PDF ማገናኛ",
      syncDriveBtn: "Google Drive አስምር",
      verifyLinksBtn: "PDF አረጋግጥ (40)",
      forceVerifyBtn: "እንደገና አረጋግጥ",
      refreshAdminBtn: "መረጃ አድስ",
      adminPdfTitle: "የPDF መጽሐፍት ሁኔታ",
      confirmLinkBtn: "አጽድቅ",
      unlinkBtn: "አላቅቅ",
      showMoreBtn: "ተጨማሪ አሳይ",
      adminConfigTitle: "የስርዓት ማስተካከያ",
      saveConfig: "ቅንብሮችን አስቀምጥ",
      adminPublishTitle: "የሁለት ሳምንት ሪፖርት ላክ",
      publishReportBtn: "አጽድቅና ለወላጅ ላክ",
      adminBroadcastTitle: "ማስታወቂያ ላክ",
      sendBroadcastBtn: "መልዕክት ላክ",
      adminAccountsTitle: "አካውንቶች እና እድሳት",
      approve30d: "አጽድቅ (30 ቀን)",
      renew30d: "አድስ (+30 ቀን)",
      markLeft: "ወጥቷል በል",
      rejectBtn: "አትቀበል",
      actionDone: "ተስተካክሏል።",
    },
    om: {
      brandSub: "Giddugala Qo'annoo fi Qormaataa Bishooftuu",
      loading: "Qelal Learning banamaa jira...",
      outsideTitle: "Telegram keessatti banaa",
      outsideBody:
        "Appiin qo'annoo kun dubbisa keessan, qormaata shaakalaa fi hordoffii maatii walitti qabsiisuuf Telegram keessatti hojjeta. Botii Qelal Learning Telegram keessatti banuun /start ergaa.",
      retry: "Irra deebi'ii yaali",
      regSub: "Giddugala Qo'annoo fi Qormaataa Bishooftuu · Kutaa 1–12",
      regLangLabel: "Afaan keessan filadhaa",
      regIntro:
        "Kitaabota fi qormaata biyyaalessaa darban dubbisuuf, deebii qormaataa battalumatti sirreeffachuuf, akkasumas teessoo qo'annoo Sanbataa fi Dilbataa yookiin barsiisaa manaa Bishooftuu keessatti qabachuuf al tokko galmaa'aa.",
      regRolePrompt: "Eenyutu galmaa'aa jira?",
      roleStudent: "Barataa / Barattuu",
      roleParent: "Maatii / Guddistuu",
      fullNameStudent: "Maqaa guutuu barataa",
      fullNameParent: "Maqaa guutuu maatii / guddistuu",
      phoneLabel: "Lakkoofsa bilbilaa",
      gradeLevel: "Kutaa (1–12)",
      examTag68: "Ministirii",
      examTag12: "Qormaata Biyyaalessaa",
      streamLabel: "Gosa barumsaa",
      streamNatural: "Saayinsii Uumamaa",
      streamSocial: "Saayinsii Hawaasaa",
      formatStudentLabel: "Haala qo'annoo filatamu",
      formatParentLabel: "Haala qo'annoo ijoo",
      formatWeekend: "Giddugala Sanbataa & Dilbataa",
      formatHome: "Barsiisaa Manaa 1-if-1",
      childrenHeading: "Ijoollee",
      addChild: "+ Ijoollee biraa dabali",
      removeChild: "Haqi",
      childCardTitle: "Mucaa",
      childNameLabel: "Maqaa guutuu mucaa",
      childContactLabel: "Telegram @username ykn bilbila mucaa (dirqama miti)",
      childContactHint:
        "Mucaan keessan Telegram yoo qabaate @username ykn lakkoofsa bilbilaa galchaa; yommuu botii banan herregni isaanii ofumaan walqabata.",
      siblingDiscountNote:
        "Ijoollee 2 fi isaa ol yoo galmeessitan hir'inni kaffaltii obbolaa ofumaan hojjeta.",
      refLabel: "Koodii afeerraa / Study Squad (dirqama miti)",
      legalPrefix: "Galmaa'uun keessan",
      legalTerms: "Waliigaltee Galmee",
      legalAnd: "fi",
      legalPrivacy: "Imaammata Iccitii",
      submitReg: "Galmee xumuri",
      submitting: "Galmaa'aa jira...",
      errNamePhone: "Maaloo maqaa guutuu fi lakkoofsa bilbilaa galchaa.",
      errChildName: "Maaloo maqaa mucaa hundaa galchaa.",
      errGeneric: "Galmeen hin milkoofne. Maaloo irra deebi'aa yaalaa.",
      gradeWord: "Kutaa",
      navParent: "Hordoffii Mucaa",
      navLibrary: "Mana Kitaabaa",
      navPlans: "Karoora Qo'annoo",
      navAccount: "Herrega",
      navAdmin: "Bulchaa",
      countdownMatric: "Qormaata Biyyaalessaa Kutaa 12",
      countdownG8: "Qormaata Ministirii Kutaa 8",
      countdownG6: "Qormaata Ministirii Kutaa 6",
      countdownSem: "Qormaata Seemeestiraa",
      daysLeftUnit: "guyyoota hafe",
      targetDate: "Guyyaa qormaataa",
      trialBanner:
        "Haala Yaalii: Kitaabota jalqabaa 3 kutaa keessanii fi gaaffilee 10 jalqabaa qormaata hundaa banamaniiru. Miseensa guutuu ta'uuf +251 933 510 682 / +251 988 666 328 bilbilaa.",
      continueReading: "Dubbisa itti fufi",
      pageWord: "Fuula",
      searchPlaceholder: "Kitaabota, qormaata, gosa barumsaa barbaadi...",
      allGrades: "Kutaa hundaa",
      myGrade: "Kutaa koo",
      allSubjects: "Gosa barumsaa hundaa",
      allCategories: "Gosa qabiyyee hundaa",
      savedBtn: "Ol-kaa'ame",
      showingDocs: "qabiyyeewwan",
      noDocsMatch: "Qabiyyeen barbaacha keessaniin walsimu hin argamne.",
      readPdf: "Dubbisi (PDF)",
      takeQuiz: "Qormaata",
      quizPreview: "Yaalii Gaaffii 10",
      answerSheet: "Waraqaa Deebii",
      sendToChat: "Gara Chaatii Ergi",
      saveDoc: "Ol-kaa'i",
      savedDoc: "Ol-kaa'ameera",
      lockedFull: "Miseensa Guutuu",
      setTrialPick: "Yaalii Godhi",
      isTrialPick: "Filannoo Yaalii: Banaa",
      reqPrompt: "Kitaaba ykn qormaata barbaaddan dhabdanii?",
      reqToggle: "Qabiyyee gaafadhaa",
      reqSubject: "Gosa barumsaa fi kutaa",
      reqDetails: "Maqaa kitaabaa ykn bara qormaataa",
      reqSend: "Gaaffii ergi",
      reqSent: "Gaaffiin keessan garee Qelal tiif ergameera.",
      reqEmpty: "Maaloo waan barbaaddan barreessaa.",
      plansTrialNote:
        "Haala Yaalii: Hojiiwwan jalqabaa 3 karoora hundaa banamaniiru. Miseensonni guutuun karoora torban hedduu argatu.",
      customPlanTitle: "Tarree qo'annoo dhuunfaa",
      customTaskPlaceholder: "Mata-duree ykn hojii qo'annoo dabali...",
      addBtn: "Dabali",
      deleteBtn: "Haqi",
      doneLabel: "xumurameera",
      lockedTask: "Miseensa Guutuu",
      childSwitchLabel: "Mucaa filadhu",
      notLinkedNote:
        "Mucaan keessan ammallee Telegram dhuunfaa isaaniitiin hin banne. Telegram yoo qabaatan liinkii gadii ergaafii, yookiin bilbila kana waliin fayyadamuun Mana Kitaabaa fi Karoora banaa.",
      sharedPhoneTag: "Wal hin qabanne / Bilbila waliinii",
      linkedTag: "Herregni walqabateera",
      copyInvite: "Liinkii afeerraa garagalchi",
      shareTg: "Telegram irratti ergi",
      copied: "Garagalfameera",
      kpiPdfs: "Kitaabota Banaman",
      kpiViews: "baninsa waliigalaa",
      kpiQuizzes: "Qormaata Hojjataman",
      kpiAvg: "giddugaleessa",
      kpiPlan: "Karoora Qo'annoo",
      kpiSaved: "Offline Ol-kaa'ame",
      kpiBookmarks: "mallatteeffame",
      chart7d: "Sochii Qo'annoo Guyyoota 7",
      quizTrendTitle: "Qabxii Qormaataa Dhihoo",
      noQuizzesYet: "Ammatti qormaatni hojjatame hin jiru.",
      subjBreakdownTitle: "Sochii Gosa Barumsaatiin",
      subjCol: "Barumsa",
      viewsCol: "Baninsa",
      quizzesCol: "Qormaata",
      avgCol: "Giddugaleessa",
      recentActivityTitle: "Dubbisa Dhihoo fi Ol-kaa'aman",
      biweeklyReportsTitle: "Gabaasa Barsiisaa Torban Lamaa",
      noReportsYet: "Ammatti gabaasni torban lamaa hin maxxanfamne.",
      attendanceLbl: "Hirmaannaa",
      scoresLbl: "Qabxiiwwan",
      improvedLbl: "Fooyya'iinsa",
      focusLbl: "Xiyyeeffannoo itti aanu",
      accountTitle: "Herrega fi Miseensummaa",
      nameLbl: "Maqaa",
      roleLbl: "Gahee",
      statusLbl: "Haala",
      tierLbl: "Sadarkaa Tajaajilaa",
      daysRemainLbl: "Guyyoota Hafe",
      squadTitle: "Garee Qo'annoo fi Afeerraa",
      squadDesc:
        "Koodii keessan hiriyoota ykn maatii Bishooftuu jiraniif qoodaa. Hiriyoota 2 yoo afeertan teessoo Study Squad fi galmee foormulaa argattu.",
      yourCode: "Koodii afeerraa keessan",
      verifiedRefs: "Afeerraawwan mirkanaa'an",
      copyCode: "Koodii garagalchi",
      childrenSectionTitle: "Barattoota Galmaa'an",
      supportTitle: "Deeggarsa Giddugala Bishooftuu",
      closeBtn: "Cufi",
      prevBtn: "Kan duraa",
      nextBtn: "Itti aanu",
      quizTabBubbles: "Waraqaa Deebii",
      quizTabPaper: "Waraqaa Qormaataa (PDF)",
      quizTrialBanner:
        "Yaalii: Gaaffilee 1 hanga 10 sirreeffamu. Qormaata guutuu sirreeffachuuf miseensa guutuu ta'aa.",
      gradeMyAnswers: "Deebii koo sirreessi",
      retakeQuiz: "Irra deebi'ii hojjadhu",
      scoreLabel: "Qabxii",
      yoursCol: "Keessan",
      keyCol: "Sirrii",
      pdfLoading: "Sanadni fe'amaa jira...",
      pdfError: "PDF asitti mul'isuun hin danda'amne.",
      pdfTryFrame: "Banaa biraatiin yaali",
      sentChatOk: "Gara chaatii Telegram keessaniitti ergameera.",
      adminSyncTitle: "Qindaa'ina Google Drive fi Mirkaneessa PDF",
      syncDriveBtn: "Google Drive Qindeessi",
      verifyLinksBtn: "PDF Mirkaneessi (40)",
      forceVerifyBtn: "Irra Deebi'ii Mirkaneessi",
      refreshAdminBtn: "Haaromsi",
      adminPdfTitle: "Haala Mana Kitaabaa PDF",
      confirmLinkBtn: "Mirkaneessi",
      unlinkBtn: "Addaan Baasi",
      showMoreBtn: "Dabalata agarsiisi",
      adminConfigTitle: "Qindaa'ina Sirnaa",
      saveConfig: "Qindaa'ina ol-kaa'i",
      adminPublishTitle: "Gabaasa Torban Lamaa Ergi",
      publishReportBtn: "Mirkaneessii Ergi",
      adminBroadcastTitle: "Beeksisa Ergi",
      sendBroadcastBtn: "Beeksisa Ergi",
      adminAccountsTitle: "Herregaa fi Haaromsa",
      approve30d: "Mirkaneessi (30g)",
      renew30d: "Haaromsi (+30g)",
      markLeft: "Baheera jedhi",
      rejectBtn: "Diduu",
      actionDone: "Haalaan haaromfameera.",
    },
  };

  // ==================== APP STATE ====================
  const state = {
    lang: "en",
    token: "",
    auth: null,
    activeTab: "library",
    regRole: "student",
    regStudentGrade: "Grade 12",
    regStudentStream: "Natural",
    regStudentFormat: "Weekend Hub",
    regParentFormat: "Weekend Hub",
    regChildren: [
      { name: "", grade: "Grade 8", stream: "Natural", format: "Weekend Hub", child_contact: "" },
    ],
    libraryItems: [],
    libraryLoaded: false,
    filterGrade: "MY_GRADE",
    filterSubject: "ALL",
    filterCategory: "ALL",
    filterSavedOnly: false,
    searchQuery: "",
    progress: { bookmarks: [], last_read: {}, plan_progress: {}, custom_plan: [] },
    studyPlans: [],
    parentAnalytics: null,
    activeChildIdx: 0,
    adminOverview: null,
    adminAccountFilter: "ALL",
    adminAccountSearch: "",
    adminPdfFilter: "ALL",
    adminPdfSearch: "",
    adminPdfLimit: 40,
    adminPollTimer: null,
    pdfDocId: null,
    pdfDocObj: null,
    pdfPage: 1,
    pdfTotalPages: 1,
    pdfScale: 1.15,
    pdfRenderTask: null,
    pdfSaveTimer: null,
    quizDocId: null,
    quizMeta: null,
    quizAnswers: {},
    quizPane: "bubbles",
    quizPdfDocObj: null,
    quizPdfPage: 1,
    quizPdfTotal: 1,
    quizPdfScale: 1.05,
    quizPdfRenderTask: null,
  };

  function t(key) {
    return (I18N[state.lang] && I18N[state.lang][key]) || I18N.en[key] || key;
  }

  function esc(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatGradeLabel(gradeStr) {
    const m = /^Grade\s+(\d+)$/i.exec(String(gradeStr || "").trim());
    if (!m) return gradeStr || "";
    const n = m[1];
    if (state.lang === "am") return `${n}ኛ ክፍል`;
    if (state.lang === "om") return `Kutaa ${n}`;
    return `Grade ${n}`;
  }

  function setHidden(id, hide) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle("hidden", hide);
    el.style.display = hide ? "none" : "";
  }

  function showBootError(msg) {
    setHidden("screenLoading", false);
    const box = document.getElementById("loadingText") || document.getElementById("screenLoading");
    if (box) {
      box.textContent = "Error: " + msg;
      box.style.color = "#B91C1C";
    }
  }

  function showToast(msg, isError = false) {
    const box = document.getElementById("toastRegion");
    if (!box) return;
    const el = document.createElement("div");
    el.className = "toast" + (isError ? " is-error" : "");
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(() => {
      el.remove();
    }, 3200);
  }

  async function apiFetch(url, options = {}) {
    const headers = Object.assign({}, options.headers || {});
    if (state.token) {
      headers["Authorization"] = "Bearer " + state.token;
    }
    if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeoutMs || 20000);
    try {
      const resp = await fetch(url, Object.assign({}, options, { headers, signal: controller.signal }));
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(data.detail || `HTTP ${resp.status}`);
      }
      return data;
    } catch (err) {
      if (err && err.name === "AbortError") {
        throw new Error("Server took too long to respond. Tap Try again.");
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  // ==================== LANGUAGE SWITCHING ====================
  async function setLanguage(lang, persist = false) {
    if (!["en", "am", "om"].includes(lang)) return;
    state.lang = lang;
    document.documentElement.lang = lang;

    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
    document.querySelectorAll(".lang-card").forEach((card) => {
      card.classList.toggle("active", card.dataset.lang === lang);
    });

    applyStaticTranslations();

    if (state.auth && (state.auth.registered || state.auth.ok)) {
      state.auth.lang = lang;
      populateLibraryFilterOptions();
      renderPortalHeader();
      renderNav();
      renderActiveView();
    } else {
      renderRegistrationDynamicParts();
    }

    if (persist && state.token) {
      try {
        await apiFetch("/api/set-lang", { method: "POST", body: JSON.stringify({ lang }) });
      } catch (_) {}
    }
  }

  function applyStaticTranslations() {
    const setText = (id, key) => {
      const el = document.getElementById(id);
      if (el) el.textContent = t(key);
    };
    const setPlaceholder = (id, key) => {
      const el = document.getElementById(id);
      if (el) el.placeholder = t(key);
    };

    setText("loadingText", "loading");
    setText("outsideTitle", "outsideTitle");
    setText("outsideBody", "outsideBody");
    setText("outsideRetryBtn", "retry");

    setText("regHeaderSub", "regSub");
    setText("regLangLabel", "regLangLabel");
    setText("regIntroText", "regIntro");
    setText("regRolePrompt", "regRolePrompt");
    setText("roleStudentText", "roleStudent");
    setText("roleParentText", "roleParent");
    setText("regNameLabel", state.regRole === "parent" ? "fullNameParent" : "fullNameStudent");
    setText("regPhoneLabel", "phoneLabel");
    setText("regStudentGradeLabel", "gradeLevel");
    setText("regStudentStreamLabel", "streamLabel");
    setText("regStudentFormatLabel", "formatStudentLabel");
    setText("regParentFormatLabel", "formatParentLabel");
    setText("regChildrenHeading", "childrenHeading");
    setText("btnAddChild", "addChild");
    setText("regSiblingBanner", "siblingDiscountNote");
    setText("regRefLabel", "refLabel");
    setText("regLegalPrefix", "legalPrefix");
    setText("btnOpenTermsReg", "legalTerms");
    setText("regLegalAnd", "legalAnd");
    setText("btnOpenPrivacyReg", "legalPrivacy");
    setText("btnSubmitReg", "submitReg");

    document.querySelectorAll('[data-stream="Natural"]').forEach((b) => (b.textContent = t("streamNatural")));
    document.querySelectorAll('[data-stream="Social"]').forEach((b) => (b.textContent = t("streamSocial")));
    document.querySelectorAll('[data-format="Weekend Hub"]').forEach((b) => (b.textContent = t("formatWeekend")));
    document.querySelectorAll('[data-format="1-on-1 Home"]').forEach((b) => (b.textContent = t("formatHome")));

    setText("continueReadingTitle", "continueReading");
    setPlaceholder("libSearch", "searchPlaceholder");
    setText("filterSavedBtn", "savedBtn");
    setText("reqPromptText", "reqPrompt");
    setText("reqToggleBtn", "reqToggle");
    setText("reqSubjectLabel", "reqSubject");
    setText("reqDetailsLabel", "reqDetails");
    setText("reqSendBtn", "reqSend");

    setText("plansTrialNote", "plansTrialNote");
    setText("customPlanTitle", "customPlanTitle");
    setPlaceholder("customTaskInput", "customTaskPlaceholder");
    setText("btnAddCustomTask", "addBtn");

    setText("btnOpenTermsFooter", "legalTerms");
    setText("btnOpenPrivacyFooter", "legalPrivacy");

    setText("btnPdfClose", "closeBtn");
    setText("btnPdfPrev", "prevBtn");
    setText("btnPdfNext", "nextBtn");
    setText("btnPdfSendChat", "sendToChat");
    setText("btnQuizClose", "closeBtn");
    setText("tabQuizBubbles", "quizTabBubbles");
    setText("tabQuizPaper", "quizTabPaper");
    setText("btnQuizPdfPrev", "prevBtn");
    setText("btnQuizPdfNext", "nextBtn");
    setText("btnQuizSubmit", "gradeMyAnswers");
    setText("btnLegalClose", "closeBtn");
  }

  // ==================== REGISTRATION SCREEN ====================
  function initRegistrationScreen(firstName = "") {
    setHidden("screenLoading", true);
    setHidden("screenOutside", true);
    setHidden("screenPortal", true);
    setHidden("appHeader", true);
    setHidden("screenRegister", false);

    const nameEl = document.getElementById("regName");
    if (nameEl && firstName && !nameEl.value) {
      nameEl.value = firstName;
    }

    const params = new URLSearchParams(window.location.search);
    const refParam = params.get("ref") || (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) || "";
    const regRefEl = document.getElementById("regReferral");
    if (refParam && regRefEl) {
      const cleanRef = refParam.replace(/^ref_/i, "").toUpperCase();
      if (cleanRef && !cleanRef.startsWith("CHILD_") && cleanRef !== "PARENT" && cleanRef !== "STUDENT") {
        regRefEl.value = cleanRef;
      }
      if (refParam.toLowerCase() === "parent") {
        setRegRole("parent");
      }
    }

    applyStaticTranslations();
    renderRegistrationDynamicParts();
  }

  function setRegRole(role) {
    state.regRole = role === "parent" ? "parent" : "student";
    document.querySelectorAll(".role-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.role === state.regRole);
    });
    setHidden("regStudentBlock", state.regRole !== "student");
    setHidden("regParentBlock", state.regRole !== "parent");
    const lbl = document.getElementById("regNameLabel");
    if (lbl) lbl.textContent = t(state.regRole === "parent" ? "fullNameParent" : "fullNameStudent");
    renderRegistrationDynamicParts();
  }

  function renderGradeButtonsHtml(selectedGrade) {
    return GRADES.map((g) => {
      const num = g.replace("Grade ", "");
      const isSelected = selectedGrade === g;
      let tagHtml = "";
      if (num === "6" || num === "8") tagHtml = `<span class="grade-btn-tag">${esc(t("examTag68"))}</span>`;
      if (num === "12") tagHtml = `<span class="grade-btn-tag">${esc(t("examTag12"))}</span>`;
      return `
        <button type="button" class="grade-btn ${isSelected ? "active" : ""}" data-grade="${esc(g)}">
          <span class="grade-btn-num">${esc(formatGradeLabel(g))}</span>
          ${tagHtml}
        </button>
      `;
    }).join("");
  }

  function renderRegistrationDynamicParts() {
    const sGrid = document.getElementById("regStudentGradeGrid");
    if (sGrid) {
      sGrid.innerHTML = renderGradeButtonsHtml(state.regStudentGrade);
      sGrid.querySelectorAll(".grade-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          state.regStudentGrade = btn.dataset.grade;
          renderRegistrationDynamicParts();
        });
      });
    }

    const needsStream = state.regStudentGrade === "Grade 11" || state.regStudentGrade === "Grade 12";
    setHidden("regStudentStreamBlock", !needsStream);

    const cList = document.getElementById("regChildrenList");
    const sibBanner = document.getElementById("regSiblingBanner");
    if (sibBanner) {
      sibBanner.classList.toggle("hidden", state.regChildren.length < 2);
      sibBanner.textContent = t("siblingDiscountNote");
    }

    if (cList) {
      cList.innerHTML = state.regChildren
        .map((ch, idx) => {
          const showStream = ch.grade === "Grade 11" || ch.grade === "Grade 12";
          return `
            <div class="child-form-card" data-child-idx="${idx}">
              <div class="child-form-head">
                <strong class="h3-sub">${esc(t("childCardTitle"))} ${idx + 1}</strong>
                ${
                  state.regChildren.length > 1
                    ? `<button type="button" class="btn btn-danger btn-sm btn-remove-child" data-idx="${idx}">${esc(t("removeChild"))}</button>`
                    : ""
                }
              </div>
              <div class="field-group">
                <label class="field-label">${esc(t("childNameLabel"))}</label>
                <input type="text" class="input child-name-input" data-idx="${idx}" value="${esc(ch.name)}" required />
              </div>
              <div class="field-group">
                <label class="field-label">${esc(t("gradeLevel"))}</label>
                <div class="grade-grid child-grade-grid" data-idx="${idx}">
                  ${renderGradeButtonsHtml(ch.grade)}
                </div>
              </div>
              ${
                showStream
                  ? `
                <div class="field-group">
                  <label class="field-label">${esc(t("streamLabel"))}</label>
                  <div class="seg-row child-stream-row" data-idx="${idx}">
                    <button type="button" class="seg-btn ${ch.stream === "Natural" ? "active" : ""}" data-stream="Natural">${esc(t("streamNatural"))}</button>
                    <button type="button" class="seg-btn ${ch.stream === "Social" ? "active" : ""}" data-stream="Social">${esc(t("streamSocial"))}</button>
                  </div>
                </div>
              `
                  : ""
              }
              <div class="field-group" style="margin-bottom:0;">
                <label class="field-label">${esc(t("childContactLabel"))}</label>
                <input type="text" class="input child-contact-input" data-idx="${idx}" placeholder="@username / 09..." value="${esc(ch.child_contact)}" />
                <div class="meta-line" style="margin-top:4px;">${esc(t("childContactHint"))}</div>
              </div>
            </div>
          `;
        })
        .join("");

      cList.querySelectorAll(".child-name-input").forEach((inp) => {
        inp.addEventListener("input", (e) => {
          state.regChildren[Number(e.target.dataset.idx)].name = e.target.value;
        });
      });
      cList.querySelectorAll(".child-contact-input").forEach((inp) => {
        inp.addEventListener("input", (e) => {
          state.regChildren[Number(e.target.dataset.idx)].child_contact = e.target.value;
        });
      });
      cList.querySelectorAll(".child-grade-grid .grade-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.closest(".child-grade-grid").dataset.idx);
          state.regChildren[idx].grade = btn.dataset.grade;
          renderRegistrationDynamicParts();
        });
      });
      cList.querySelectorAll(".child-stream-row .seg-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.closest(".child-stream-row").dataset.idx);
          state.regChildren[idx].stream = btn.dataset.stream;
          renderRegistrationDynamicParts();
        });
      });
      cList.querySelectorAll(".btn-remove-child").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.dataset.idx);
          state.regChildren.splice(idx, 1);
          renderRegistrationDynamicParts();
        });
      });
    }
  }

  async function handleRegisterSubmit(e) {
    e.preventDefault();
    const errEl = document.getElementById("regErrorMsg");
    if (errEl) errEl.classList.add("hidden");

    const fullName = (document.getElementById("regName")?.value || "").trim();
    const phone = (document.getElementById("regPhone")?.value || "").trim();
    const refCode = (document.getElementById("regReferral")?.value || "").trim().toUpperCase();

    if (!fullName || !phone) {
      if (errEl) {
        errEl.textContent = t("errNamePhone");
        errEl.classList.remove("hidden");
      }
      return;
    }

    let childrenPayload = [];
    let chosenFormat = state.regStudentFormat;

    if (state.regRole === "student") {
      const streamVal =
        state.regStudentGrade === "Grade 11" || state.regStudentGrade === "Grade 12"
          ? state.regStudentStream
          : "General";
      childrenPayload = [
        {
          name: fullName,
          grade: state.regStudentGrade,
          stream: streamVal,
          format: state.regStudentFormat,
          child_contact: phone,
        },
      ];
    } else {
      chosenFormat = state.regParentFormat;
      for (const ch of state.regChildren) {
        if (!ch.name.trim()) {
          if (errEl) {
            errEl.textContent = t("errChildName");
            errEl.classList.remove("hidden");
          }
          return;
        }
      }
      childrenPayload = state.regChildren.map((ch) => ({
        name: ch.name.trim(),
        grade: ch.grade,
        stream: ch.grade === "Grade 11" || ch.grade === "Grade 12" ? ch.stream : "General",
        format: state.regParentFormat,
        child_contact: ch.child_contact.trim(),
      }));
    }

    const submitBtn = document.getElementById("btnSubmitReg");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = t("submitting");
    }

    try {
      await apiFetch("/api/register", {
        method: "POST",
        body: JSON.stringify({
          initData: tg ? tg.initData : "",
          role: state.regRole,
          lang: state.lang,
          full_name: fullName,
          phone: phone,
          format: chosenFormat,
          referral_code: refCode,
          children: childrenPayload,
        }),
      });
      await authenticate();
    } catch (err) {
      if (errEl) {
        errEl.textContent = err.message || t("errGeneric");
        errEl.classList.remove("hidden");
      }
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = t("submitReg");
      }
    }
  }

  // ==================== AUTH & PORTAL BOOT ====================
  async function authenticate() {
    setHidden("screenLoading", false);
    setHidden("screenOutside", true);
    setHidden("screenRegister", true);
    setHidden("screenPortal", true);

    const loadTxt = document.getElementById("loadingText");
    if (loadTxt) {
      loadTxt.textContent = t("loading");
      loadTxt.style.color = "";
    }

    try {
      const initData = tg ? tg.initData : "";
      const data = await apiFetch("/api/auth", {
        method: "POST",
        body: JSON.stringify({ initData }),
      });

      if (!data.ok) {
        if (data.status === "NOT_REGISTERED") {
          initRegistrationScreen(data.tg_first_name || "");
          return;
        }
        setHidden("screenLoading", true);
        setHidden("screenOutside", false);
        applyStaticTranslations();
        return;
      }

      state.auth = data;
      state.token = data.token;
      state.lang = ["en", "am", "om"].includes(data.lang) ? data.lang : "en";

      setHidden("screenLoading", true);
      setHidden("appHeader", false);
      setHidden("screenPortal", false);

      state.activeTab = data.role === "parent" ? "parent" : "library";

      await Promise.allSettled([loadProgress(), loadLibrary()]);
      await setLanguage(state.lang, false);
    } catch (err) {
      const outsideEl = document.getElementById("screenOutside");
      if (outsideEl) {
        setHidden("screenLoading", true);
        setHidden("screenOutside", false);
        const det = document.getElementById("outsideDetail");
        if (det) {
          det.textContent = err.message || "";
          det.classList.toggle("hidden", !err.message);
        }
      } else {
        showBootError(err.message || "Authentication failed");
      }
    }
  }

  function renderPortalHeader() {
    if (!state.auth) return;
    const titleEl = document.getElementById("headerTitle");
    if (titleEl) titleEl.textContent = "Qelal Learning (ቀላል)";
    const subParts = [state.auth.name];
    if (state.auth.role === "parent") {
      subParts.push(t("roleParent"));
    } else if (state.auth.grade) {
      subParts.push(formatGradeLabel(state.auth.grade));
    }
    const subEl = document.getElementById("headerSub");
    if (subEl) subEl.textContent = subParts.join(" · ");
  }

  function renderNav() {
    const nav = document.getElementById("mainNav");
    if (!nav) return;
    const tabs = [];
    if (state.auth.role === "parent") {
      tabs.push({ id: "parent", label: t("navParent") });
    }
    tabs.push({ id: "library", label: t("navLibrary") });
    tabs.push({ id: "plans", label: t("navPlans") });
    tabs.push({ id: "account", label: t("navAccount") });
    if (state.auth.is_admin) {
      tabs.push({ id: "admin", label: t("navAdmin") });
    }

    if (!tabs.some((tb) => tb.id === state.activeTab)) {
      state.activeTab = tabs[0].id;
    }

    nav.innerHTML = tabs
      .map(
        (tb) =>
          `<button type="button" class="nav-tab ${state.activeTab === tb.id ? "active" : ""}" data-tab="${tb.id}">${esc(tb.label)}</button>`
      )
      .join("");

    nav.querySelectorAll(".nav-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.activeTab = btn.dataset.tab;
        renderNav();
        renderActiveView();
      });
    });
  }

  function renderActiveView() {
    if (state.activeTab !== "admin") {
      stopAdminJobPolling();
    }
    ["viewParent", "viewLibrary", "viewPlans", "viewAccount", "viewAdmin"].forEach((id) => {
      setHidden(id, true);
    });

    if (state.activeTab === "parent") {
      setHidden("viewParent", false);
      renderParentView();
    } else if (state.activeTab === "library") {
      setHidden("viewLibrary", false);
      renderLibraryView();
    } else if (state.activeTab === "plans") {
      setHidden("viewPlans", false);
      renderPlansView();
    } else if (state.activeTab === "account") {
      setHidden("viewAccount", false);
      renderAccountView();
    } else if (state.activeTab === "admin" && state.auth.is_admin) {
      setHidden("viewAdmin", false);
      renderAdminView();
    }
  }

  // ==================== PROGRESS SYNC ====================
  async function loadProgress() {
    try {
      const data = await apiFetch("/api/progress");
      state.progress = {
        bookmarks: Array.isArray(data.bookmarks) ? data.bookmarks : [],
        last_read: data.last_read || {},
        plan_progress: data.plan_progress || {},
        custom_plan: Array.isArray(data.custom_plan) ? data.custom_plan : [],
      };
    } catch (_) {}
  }

  async function saveProgress() {
    try {
      await apiFetch("/api/progress", {
        method: "POST",
        body: JSON.stringify(state.progress),
      });
    } catch (_) {}
  }

  // ==================== LIBRARY VIEW ====================
  async function loadLibrary(forceRefresh = false) {
    try {
      const url = forceRefresh ? "/api/library?refresh=true" : "/api/library";
      const data = await apiFetch(url);
      state.libraryItems = data.items || [];
      state.libraryLoaded = true;
      populateLibraryFilterOptions();
      if (state.activeTab === "library") renderLibraryView();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  function populateLibraryFilterOptions() {
    const gradeSel = document.getElementById("filterGrade");
    const subjSel = document.getElementById("filterSubject");
    const catSel = document.getElementById("filterCategory");
    if (!gradeSel || !subjSel || !catSel) return;

    const gradesSet = new Set(GRADES);
    const subjSet = new Set();
    const catSet = new Set();
    state.libraryItems.forEach((it) => {
      if (it.grade) gradesSet.add(it.grade);
      if (it.subject) subjSet.add(it.subject);
      if (it.category) catSet.add(it.category);
    });

    const userGrade = (state.auth && state.auth.grade) || "";
    gradeSel.innerHTML = [
      `<option value="MY_GRADE">${esc(t("myGrade"))} (${esc(formatGradeLabel(userGrade))})</option>`,
      `<option value="ALL">${esc(t("allGrades"))}</option>`,
      ...Array.from(gradesSet).map((g) => `<option value="${esc(g)}">${esc(formatGradeLabel(g))}</option>`),
    ].join("");
    if (Array.from(gradeSel.options).some((o) => o.value === state.filterGrade)) {
      gradeSel.value = state.filterGrade;
    } else {
      state.filterGrade = "ALL";
      gradeSel.value = "ALL";
    }

    subjSel.innerHTML =
      `<option value="ALL">${esc(t("allSubjects"))}</option>` +
      Array.from(subjSet)
        .sort()
        .map((s) => `<option value="${esc(s)}">${esc(s)}</option>`)
        .join("");
    subjSel.value = Array.from(subjSel.options).some((o) => o.value === state.filterSubject) ? state.filterSubject : "ALL";

    catSel.innerHTML =
      `<option value="ALL">${esc(t("allCategories"))}</option>` +
      Array.from(catSet)
        .sort()
        .map((c) => `<option value="${esc(c)}">${esc(c)}</option>`)
        .join("");
    catSel.value = Array.from(catSel.options).some((o) => o.value === state.filterCategory) ? state.filterCategory : "ALL";
  }

  function matchesUserGradeFilter(itemGrade, targetGrade) {
    if (!targetGrade) return true;
    if (itemGrade === targetGrade) return true;
    if (["Grade 9", "Grade 10", "Grade 11", "Grade 12"].includes(targetGrade) && itemGrade === "Grade 9-12") return true;
    if (["Grade 11", "Grade 12"].includes(targetGrade) && itemGrade === "Grade 11-12") return true;
    if (["Grade 9", "Grade 10"].includes(targetGrade) && itemGrade === "Grade 9-10") return true;
    return false;
  }

  function renderLibraryView() {
    const cdCard = document.getElementById("countdownCard");
    if (cdCard) {
      if (state.auth && state.auth.countdown && state.auth.countdown.date) {
        const cd = state.auth.countdown;
        const target = new Date(cd.date + "T00:00:00+03:00");
        const now = new Date();
        const diffDays = Math.max(0, Math.ceil((target - now) / (1000 * 60 * 60 * 24)));
        const labelMap = {
          matric_12: t("countdownMatric"),
          ministry_8: t("countdownG8"),
          ministry_6: t("countdownG6"),
          semester: t("countdownSem"),
        };
        cdCard.innerHTML = `
          <div>
            <div class="h3-sub">${esc(labelMap[cd.type] || t("countdownSem"))}</div>
            <div class="meta-line">${esc(t("targetDate"))}: <span class="mono-num">${esc(cd.date)}</span></div>
          </div>
          <div style="text-align:right;">
            <div class="countdown-days">${diffDays}</div>
            <div class="meta-line">${esc(t("daysLeftUnit"))}</div>
          </div>
        `;
        cdCard.classList.remove("hidden");
      } else {
        cdCard.classList.add("hidden");
      }
    }

    const trialEl = document.getElementById("trialBanner");
    if (trialEl) {
      if (state.auth && state.auth.tier === "TRIAL") {
        trialEl.textContent = t("trialBanner");
        trialEl.classList.remove("hidden");
      } else {
        trialEl.classList.add("hidden");
      }
    }

    const contWrap = document.getElementById("continueReadingSection");
    const contList = document.getElementById("continueReadingList");
    const byId = {};
    state.libraryItems.forEach((it) => (byId[it.doc_id] = it));
    const recentEntries = Object.entries(state.progress.last_read || {})
      .filter(([did]) => byId[did] && !byId[did].locked && byId[did].has_pdf)
      .sort((a, b) => (b[1].ts || 0) - (a[1].ts || 0))
      .slice(0, 3);

    if (contWrap && contList) {
      if (recentEntries.length > 0) {
        contWrap.classList.remove("hidden");
        contList.innerHTML = recentEntries
          .map(([did, info]) => {
            const item = byId[did];
            return `
              <div class="compact-row">
                <div style="min-width:0;">
                  <div class="doc-title">${esc(item.file_name)}</div>
                  <div class="doc-meta">${esc(item.subject)} · ${esc(t("pageWord"))} <span class="mono-num">${info.page || 1}</span></div>
                </div>
                <button type="button" class="btn btn-primary btn-sm btn-open-pdf" data-doc-id="${esc(did)}">${esc(t("readPdf"))}</button>
              </div>
            `;
          })
          .join("");
        contList.querySelectorAll(".btn-open-pdf").forEach((b) => {
          b.addEventListener("click", () => openPdfReader(b.dataset.docId));
        });
      } else {
        contWrap.classList.add("hidden");
      }
    }

    const q = state.searchQuery.trim().toLowerCase();
    const filtered = state.libraryItems.filter((it) => {
      if (state.filterGrade === "MY_GRADE") {
        if (!matchesUserGradeFilter(it.grade, state.auth.grade)) return false;
      } else if (state.filterGrade !== "ALL" && it.grade !== state.filterGrade) {
        return false;
      }
      if (state.filterSubject !== "ALL" && it.subject !== state.filterSubject) return false;
      if (state.filterCategory !== "ALL" && it.category !== state.filterCategory) return false;
      if (state.filterSavedOnly && !state.progress.bookmarks.includes(it.doc_id)) return false;
      if (q) {
        const hay = `${it.file_name} ${it.subject} ${it.category} ${it.grade} ${it.year}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    filtered.sort((a, b) => Number(a.locked) - Number(b.locked));

    const countEl = document.getElementById("libCountText");
    if (countEl) countEl.textContent = `${filtered.length} ${t("showingDocs")}`;
    const savedBtn = document.getElementById("filterSavedBtn");
    if (savedBtn) savedBtn.classList.toggle("active", state.filterSavedOnly);

    const listEl = document.getElementById("libList");
    if (!listEl) return;
    if (!filtered.length) {
      listEl.innerHTML = `<div class="ledger-row"><p class="muted-text">${esc(t("noDocsMatch"))}</p></div>`;
      return;
    }

    listEl.innerHTML = filtered
      .slice(0, 120)
      .map((it) => {
        const isBookmarked = state.progress.bookmarks.includes(it.doc_id);
        const metaParts = [
          formatGradeLabel(it.grade),
          it.stream && it.stream !== "General" ? it.stream : "",
          it.subject,
          it.category,
          it.year,
          it.file_size_mb ? `${it.file_size_mb} MB` : "",
        ].filter(Boolean);

        const actions = [];
        if (!it.locked) {
          if (it.has_pdf) {
            actions.push(`<button type="button" class="btn btn-primary btn-sm act-read" data-id="${esc(it.doc_id)}">${esc(t("readPdf"))}</button>`);
          }
          actions.push(`<button type="button" class="btn btn-secondary btn-sm act-send" data-id="${esc(it.doc_id)}">${esc(t("sendToChat"))}</button>`);
          if (it.linked_doc_id && it.category !== "Answer Sheet" && byId[it.linked_doc_id]) {
            actions.push(`<button type="button" class="btn btn-secondary btn-sm act-read" data-id="${esc(it.linked_doc_id)}">${esc(t("answerSheet"))}</button>`);
          }
        }
        if (it.has_quiz) {
          const qLabel = state.auth.tier === "TRIAL" ? t("quizPreview") : `${t("takeQuiz")} (${it.quiz_total_q})`;
          actions.push(`<button type="button" class="btn btn-secondary btn-sm act-quiz" data-id="${esc(it.doc_id)}">${esc(qLabel)}</button>`);
        }
        actions.push(
          `<button type="button" class="btn btn-secondary btn-sm act-bookmark ${isBookmarked ? "active" : ""}" data-id="${esc(it.doc_id)}">${esc(
            isBookmarked ? t("savedDoc") : t("saveDoc")
          )}</button>`
        );
        if (state.auth.is_admin) {
          actions.push(
            `<button type="button" class="btn btn-secondary btn-sm act-trial ${it.is_trial ? "active" : ""}" data-id="${esc(it.doc_id)}" data-trial="${it.is_trial ? "1" : "0"}">${esc(
              it.is_trial ? t("isTrialPick") : t("setTrialPick")
            )}</button>`
          );
        }

        return `
          <article class="ledger-row">
            <div class="ledger-row-head">
              <div style="min-width:0;">
                <div class="doc-title">${esc(it.file_name)}</div>
                <div class="doc-meta">${esc(metaParts.join(" · "))}</div>
              </div>
              ${it.locked ? `<span class="status-tag is-warn">${esc(t("lockedFull"))}</span>` : ""}
            </div>
            <div class="btn-row">${actions.join("")}</div>
          </article>
        `;
      })
      .join("");

    listEl.querySelectorAll(".act-read").forEach((b) => b.addEventListener("click", () => openPdfReader(b.dataset.id)));
    listEl.querySelectorAll(".act-send").forEach((b) => b.addEventListener("click", () => sendFileToTelegram(b.dataset.id, b)));
    listEl.querySelectorAll(".act-quiz").forEach((b) => b.addEventListener("click", () => openQuizRunner(b.dataset.id)));
    listEl.querySelectorAll(".act-bookmark").forEach((b) => b.addEventListener("click", () => toggleBookmark(b.dataset.id)));
    listEl.querySelectorAll(".act-trial").forEach((b) =>
      b.addEventListener("click", () => toggleAdminTrialPick(b.dataset.id, b.dataset.trial !== "1"))
    );
  }

  async function toggleBookmark(docId) {
    const idx = state.progress.bookmarks.indexOf(docId);
    if (idx >= 0) {
      state.progress.bookmarks.splice(idx, 1);
    } else {
      state.progress.bookmarks.push(docId);
    }
    if (state.activeTab === "library") renderLibraryView();
    updatePdfBookmarkBtn();
    await saveProgress();
  }

  async function sendFileToTelegram(docId, btnEl) {
    if (btnEl) btnEl.disabled = true;
    try {
      const res = await apiFetch(`/api/file/${encodeURIComponent(docId)}/send`, { method: "POST" });
      if (res.too_large) {
        showToast(res.message || "File exceeds Telegram limit; open in viewer.", true);
      } else {
        showToast(t("sentChatOk"));
      }
    } catch (err) {
      showToast(err.message, true);
    } finally {
      if (btnEl) btnEl.disabled = false;
    }
  }

  async function toggleAdminTrialPick(docId, nextState) {
    try {
      await apiFetch("/api/admin/toggle-trial", {
        method: "POST",
        body: JSON.stringify({ doc_id: docId, is_trial: nextState }),
      });
      await loadLibrary(true);
    } catch (err) {
      showToast(err.message, true);
    }
  }

  // ==================== IN-APP PDF READER (PDF.JS + FALLBACK) ====================
  function updatePdfBookmarkBtn() {
    const btn = document.getElementById("btnPdfBookmark");
    if (!btn || !state.pdfDocId) return;
    const saved = state.progress.bookmarks.includes(state.pdfDocId);
    btn.textContent = saved ? t("savedDoc") : t("saveDoc");
    btn.classList.toggle("active", saved);
  }

  async function loadPdfDocumentWithFallback(streamUrl) {
    if (!window.pdfjsLib) {
      throw new Error("PDF engine unavailable");
    }
    try {
      return await window.pdfjsLib.getDocument({ url: streamUrl, rangeChunkSize: 65536 }).promise;
    } catch (_) {
      const resp = await fetch(streamUrl);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const buf = await resp.arrayBuffer();
      return await window.pdfjsLib.getDocument({ data: buf }).promise;
    }
  }

  async function openPdfReader(docId) {
    const item = state.libraryItems.find((x) => x.doc_id === docId);
    state.pdfDocId = docId;
    state.pdfDocObj = null;
    state.pdfScale = 1.15;

    const savedPage = (state.progress.last_read && state.progress.last_read[docId] && state.progress.last_read[docId].page) || 1;
    state.pdfPage = savedPage;

    document.getElementById("pdfModalTitle").textContent = item ? item.file_name : docId;
    document.getElementById("pdfZoomLabel").textContent = "115%";
    document.getElementById("pdfCanvas").classList.remove("hidden");
    document.getElementById("pdfFallbackFrame").classList.add("hidden");
    const overlay = document.getElementById("pdfStatusOverlay");
    overlay.textContent = t("pdfLoading");
    overlay.classList.remove("hidden");

    updatePdfBookmarkBtn();
    setHidden("modalPdf", false);

    const streamUrl = `/api/file/${encodeURIComponent(docId)}/stream?token=${encodeURIComponent(state.token)}`;
    try {
      const pdfDoc = await loadPdfDocumentWithFallback(streamUrl);
      if (state.pdfDocId !== docId) return;
      state.pdfDocObj = pdfDoc;
      state.pdfTotalPages = pdfDoc.numPages;
      if (state.pdfPage > state.pdfTotalPages) state.pdfPage = 1;
      document.getElementById("pdfPageTotal").textContent = String(state.pdfTotalPages);
      overlay.classList.add("hidden");
      await renderMainPdfPage();
    } catch (_) {
      if (state.pdfDocId !== docId) return;
      overlay.innerHTML = `
        <p>${esc(t("pdfError"))}</p>
        <button type="button" id="btnTriggerFrameFallback" class="btn btn-primary btn-sm">${esc(t("pdfTryFrame"))}</button>
      `;
      document.getElementById("btnTriggerFrameFallback").addEventListener("click", () => {
        overlay.classList.add("hidden");
        document.getElementById("pdfCanvas").classList.add("hidden");
        const frame = document.getElementById("pdfFallbackFrame");
        frame.src = streamUrl;
        frame.classList.remove("hidden");
      });
    }
  }

  async function renderMainPdfPage() {
    if (!state.pdfDocObj) return;
    if (state.pdfRenderTask) {
      try {
        state.pdfRenderTask.cancel();
      } catch (_) {}
    }

    const pageNum = Math.max(1, Math.min(state.pdfPage, state.pdfTotalPages));
    state.pdfPage = pageNum;
    document.getElementById("pdfPageInput").value = String(pageNum);
    document.getElementById("pdfZoomLabel").textContent = Math.round(state.pdfScale * 100) + "%";

    const page = await state.pdfDocObj.getPage(pageNum);
    const viewportEl = document.getElementById("pdfViewport");
    const availW = Math.max(280, viewportEl.clientWidth - 28);
    const baseVp = page.getViewport({ scale: 1 });
    const fitScale = (availW / baseVp.width) * state.pdfScale;
    const vp = page.getViewport({ scale: fitScale });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const canvas = document.getElementById("pdfCanvas");
    const ctx = canvas.getContext("2d");
    canvas.width = Math.floor(vp.width * dpr);
    canvas.height = Math.floor(vp.height * dpr);
    canvas.style.width = Math.floor(vp.width) + "px";
    canvas.style.height = Math.floor(vp.height) + "px";

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const task = page.render({ canvasContext: ctx, viewport: vp });
    state.pdfRenderTask = task;

    try {
      await task.promise;
      state.progress.last_read[state.pdfDocId] = { page: pageNum, ts: Date.now() };
      clearTimeout(state.pdfSaveTimer);
      state.pdfSaveTimer = setTimeout(() => saveProgress(), 1200);
    } catch (_) {}
  }

  function closePdfReader() {
    setHidden("modalPdf", true);
    const frame = document.getElementById("pdfFallbackFrame");
    if (frame) frame.src = "about:blank";
    if (state.pdfDocObj) {
      try {
        state.pdfDocObj.destroy();
      } catch (_) {}
    }
    state.pdfDocObj = null;
    state.pdfDocId = null;
    if (state.activeTab === "library") renderLibraryView();
  }

  // ==================== BUBBLE-SHEET QUIZ RUNNER ====================
  async function openQuizRunner(docId) {
    state.quizDocId = docId;
    state.quizAnswers = {};
    state.quizPane = "bubbles";
    state.quizPdfDocObj = null;
    state.quizPdfPage = 1;
    state.quizPdfScale = 1.05;

    const item = state.libraryItems.find((x) => x.doc_id === docId);
    document.getElementById("quizModalTitle").textContent = item ? item.file_name : docId;
    document.getElementById("quizBubblesList").innerHTML = `<div class="ledger-row"><p class="muted-text">${esc(t("loading"))}</p></div>`;
    document.getElementById("quizResultPane").classList.add("hidden");
    document.getElementById("quizBubblesList").classList.remove("hidden");
    document.getElementById("quizSubmitBar").classList.remove("hidden");
    setHidden("modalQuiz", false);

    const hasPdf = item && item.has_pdf && !item.locked;
    document.getElementById("quizViewTabs").classList.toggle("hidden", !hasPdf);
    setQuizPane("bubbles");

    try {
      const meta = await apiFetch(`/api/quiz/${encodeURIComponent(docId)}`);
      state.quizMeta = meta;
      renderQuizBubbles();
    } catch (err) {
      document.getElementById("quizBubblesList").innerHTML = `<div class="ledger-row"><p class="error-inline">${esc(err.message)}</p></div>`;
    }
  }

  function setQuizPane(pane) {
    state.quizPane = pane;
    document.querySelectorAll(".quiz-subtab").forEach((b) => b.classList.toggle("active", b.dataset.pane === pane));
    document.getElementById("quizBubblePane").classList.toggle("hidden", pane !== "bubbles");
    document.getElementById("quizPdfPane").classList.toggle("hidden", pane !== "paper");

    if (pane === "paper" && !state.quizPdfDocObj && state.quizDocId) {
      loadQuizExamPdf();
    }
  }

  async function loadQuizExamPdf() {
    const statusEl = document.getElementById("quizPdfStatus");
    statusEl.textContent = t("pdfLoading");
    statusEl.classList.remove("hidden");
    const url = `/api/file/${encodeURIComponent(state.quizDocId)}/stream?token=${encodeURIComponent(state.token)}`;
    try {
      const pdfDoc = await loadPdfDocumentWithFallback(url);
      state.quizPdfDocObj = pdfDoc;
      state.quizPdfTotal = pdfDoc.numPages;
      statusEl.classList.add("hidden");
      await renderQuizPdfPage();
    } catch (_) {
      statusEl.textContent = t("pdfError");
    }
  }

  async function renderQuizPdfPage() {
    if (!state.quizPdfDocObj) return;
    if (state.quizPdfRenderTask) {
      try {
        state.quizPdfRenderTask.cancel();
      } catch (_) {}
    }
    const p = Math.max(1, Math.min(state.quizPdfPage, state.quizPdfTotal));
    state.quizPdfPage = p;
    document.getElementById("quizPdfPageLabel").textContent = `${p} / ${state.quizPdfTotal}`;

    const page = await state.quizPdfDocObj.getPage(p);
    const vpEl = document.getElementById("quizPdfViewport");
    const availW = Math.max(280, vpEl.clientWidth - 28);
    const baseVp = page.getViewport({ scale: 1 });
    const vp = page.getViewport({ scale: (availW / baseVp.width) * state.quizPdfScale });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const canvas = document.getElementById("quizPdfCanvas");
    const ctx = canvas.getContext("2d");
    canvas.width = Math.floor(vp.width * dpr);
    canvas.height = Math.floor(vp.height * dpr);
    canvas.style.width = Math.floor(vp.width) + "px";
    canvas.style.height = Math.floor(vp.height) + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const task = page.render({ canvasContext: ctx, viewport: vp });
    state.quizPdfRenderTask = task;
    try {
      await task.promise;
    } catch (_) {}
  }

  function renderQuizBubbles() {
    const meta = state.quizMeta;
    if (!meta) return;

    document.getElementById("quizMetaInfo").textContent = [meta.subject, meta.year, `${meta.unlocked_q} / ${meta.total_q} Q`]
      .filter(Boolean)
      .join(" · ");
    const trialNote = document.getElementById("quizTrialNote");
    if (meta.trial_limited && meta.total_q > meta.unlocked_q) {
      trialNote.textContent = t("quizTrialBanner");
      trialNote.classList.remove("hidden");
    } else {
      trialNote.classList.add("hidden");
    }

    const sectionStarts = {};
    if (Array.isArray(meta.sections)) {
      meta.sections.forEach((sec) => {
        if (sec && typeof sec === "object") {
          const st = Number(sec.start || sec.q_start);
          const lbl = sec.title || sec.name || sec.label;
          if (st && lbl) sectionStarts[st] = lbl;
        }
      });
    }

    let html = "";
    for (let q = 1; q <= meta.unlocked_q; q++) {
      if (sectionStarts[q]) {
        html += `<div class="bubble-section-head">${esc(sectionStarts[q])}</div>`;
      }
      const chosen = state.quizAnswers[String(q)] || "";
      html += `
        <div class="bubble-row">
          <span class="bubble-qnum">Q${q}</span>
          <div class="bubble-opts">
            ${["A", "B", "C", "D"]
              .map(
                (opt) =>
                  `<button type="button" class="bubble-opt ${chosen === opt ? "selected" : ""}" data-q="${q}" data-opt="${opt}">${opt}</button>`
              )
              .join("")}
          </div>
        </div>
      `;
    }

    const listEl = document.getElementById("quizBubblesList");
    listEl.innerHTML = html;
    updateQuizAnsweredCounter();

    listEl.querySelectorAll(".bubble-opt").forEach((btn) => {
      btn.addEventListener("click", () => {
        const q = btn.dataset.q;
        const opt = btn.dataset.opt;
        if (state.quizAnswers[q] === opt) {
          delete state.quizAnswers[q];
        } else {
          state.quizAnswers[q] = opt;
        }
        btn.parentElement.querySelectorAll(".bubble-opt").forEach((b) => {
          b.classList.toggle("selected", state.quizAnswers[q] === b.dataset.opt);
        });
        updateQuizAnsweredCounter();
      });
    });
  }

  function updateQuizAnsweredCounter() {
    if (!state.quizMeta) return;
    const count = Object.keys(state.quizAnswers).length;
    document.getElementById("quizAnsweredCounter").textContent = `${count} / ${state.quizMeta.unlocked_q}`;
  }

  async function submitQuizAnswers() {
    if (!state.quizDocId) return;
    const btn = document.getElementById("btnQuizSubmit");
    btn.disabled = true;
    try {
      const res = await apiFetch(`/api/quiz/${encodeURIComponent(state.quizDocId)}/submit`, {
        method: "POST",
        body: JSON.stringify({ answers: state.quizAnswers }),
      });

      document.getElementById("quizBubblesList").classList.add("hidden");
      document.getElementById("quizSubmitBar").classList.add("hidden");

      const rPane = document.getElementById("quizResultPane");
      rPane.classList.remove("hidden");
      rPane.innerHTML = `
        <div class="quiz-result-summary">
          <div class="meta-line">${esc(t("scoreLabel"))}</div>
          <div class="result-score-big">${res.score} / ${res.total_graded} (${res.percentage}%)</div>
          <div class="btn-row" style="margin-top:10px;">
            <button type="button" id="btnQuizRetake" class="btn btn-primary btn-sm">${esc(t("retakeQuiz"))}</button>
          </div>
        </div>
        <div class="breakdown-grid">
          ${(res.breakdown || [])
            .map(
              (b) => `
            <div class="bd-cell ${b.ok ? "ok" : "miss"}">
              <div><strong>Q${b.q}</strong> ${b.ok ? "OK" : "X"}</div>
              <div>${esc(t("yoursCol"))}: ${esc(b.yours)} | ${esc(t("keyCol"))}: ${esc(b.correct)}</div>
            </div>
          `
            )
            .join("")}
        </div>
      `;
      document.getElementById("btnQuizRetake").addEventListener("click", () => {
        state.quizAnswers = {};
        rPane.classList.add("hidden");
        document.getElementById("quizBubblesList").classList.remove("hidden");
        document.getElementById("quizSubmitBar").classList.remove("hidden");
        renderQuizBubbles();
      });
    } catch (err) {
      showToast(err.message, true);
    } finally {
      btn.disabled = false;
    }
  }

  function closeQuizRunner() {
    setHidden("modalQuiz", true);
    if (state.quizPdfDocObj) {
      try {
        state.quizPdfDocObj.destroy();
      } catch (_) {}
    }
    state.quizPdfDocObj = null;
    state.quizDocId = null;
  }

  // ==================== STUDY PLANS VIEW ====================
  async function renderPlansView() {
    const listEl = document.getElementById("plansList");
    if (!listEl) return;
    if (!state.studyPlans.length) {
      listEl.innerHTML = `<div class="panel-compact"><p class="muted-text">${esc(t("loading"))}</p></div>`;
      try {
        const res = await apiFetch("/api/study-plans");
        state.studyPlans = res.plans || [];
      } catch (err) {
        listEl.innerHTML = `<div class="panel-compact"><p class="error-inline">${esc(err.message)}</p></div>`;
        return;
      }
    }

    const trialNote = document.getElementById("plansTrialNote");
    const isTrial = state.auth && state.auth.tier === "TRIAL";
    if (trialNote) {
      trialNote.textContent = t("plansTrialNote");
      trialNote.classList.toggle("hidden", !isTrial);
    }

    listEl.innerHTML = state.studyPlans
      .map((pl) => {
        const total = pl.tasks.length;
        const doneCount = pl.tasks.filter((tk) => state.progress.plan_progress[tk.id]).length;
        const pct = total ? Math.round((doneCount / total) * 100) : 0;

        return `
          <article class="panel-compact">
            <div class="plan-head">
              <h2 class="h2-section" style="margin:0;">${esc(pl.title)}</h2>
              <span class="meta-line mono-num">${doneCount}/${total} (${pct}%)</span>
            </div>
            <div class="meta-line">${esc([formatGradeLabel(pl.grade), pl.stream].filter(Boolean).join(" · "))}</div>
            <p class="muted-text" style="margin-top:4px;">${esc(pl.description)}</p>
            <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
            <div class="task-list">
              ${pl.tasks
                .map((tk) => {
                  const checked = !!state.progress.plan_progress[tk.id];
                  return `
                    <div class="task-item ${tk.locked ? "task-locked" : ""}">
                      <label class="task-check-label">
                        <input type="checkbox" class="plan-task-cb" data-tid="${esc(tk.id)}" ${checked ? "checked" : ""} ${tk.locked ? "disabled" : ""} />
                        <span class="${checked ? "task-done" : ""}">${esc(tk.label)}</span>
                      </label>
                      ${tk.locked ? `<span class="status-tag is-warn">${esc(t("lockedTask"))}</span>` : ""}
                    </div>
                  `;
                })
                .join("")}
            </div>
          </article>
        `;
      })
      .join("");

    listEl.querySelectorAll(".plan-task-cb").forEach((cb) => {
      cb.addEventListener("change", async () => {
        state.progress.plan_progress[cb.dataset.tid] = cb.checked;
        renderPlansView();
        await saveProgress();
      });
    });

    renderCustomTasks();
  }

  function renderCustomTasks() {
    const cList = document.getElementById("customTaskList");
    if (!cList) return;
    const items = state.progress.custom_plan || [];
    if (!items.length) {
      cList.innerHTML = `<p class="muted-text" style="margin-top:8px;">—</p>`;
      return;
    }

    cList.innerHTML = items
      .map(
        (tk, idx) => `
      <div class="task-item">
        <label class="task-check-label">
          <input type="checkbox" class="custom-cb" data-idx="${idx}" ${tk.done ? "checked" : ""} />
          <span class="${tk.done ? "task-done" : ""}">${esc(tk.text)}</span>
        </label>
        <button type="button" class="btn btn-danger btn-sm custom-del" data-idx="${idx}">${esc(t("deleteBtn"))}</button>
      </div>
    `
      )
      .join("");

    cList.querySelectorAll(".custom-cb").forEach((cb) => {
      cb.addEventListener("change", async () => {
        state.progress.custom_plan[Number(cb.dataset.idx)].done = cb.checked;
        renderCustomTasks();
        await saveProgress();
      });
    });
    cList.querySelectorAll(".custom-del").forEach((btn) => {
      btn.addEventListener("click", async () => {
        state.progress.custom_plan.splice(Number(btn.dataset.idx), 1);
        renderCustomTasks();
        await saveProgress();
      });
    });
  }

  // ==================== PARENT ANALYTICS & REPORTS VIEW ====================
  async function renderParentView() {
    const view = document.getElementById("viewParent");
    if (!view) return;
    if (!state.parentAnalytics) {
      view.innerHTML = `<div class="panel-compact"><p class="muted-text">${esc(t("loading"))}</p></div>`;
      try {
        const res = await apiFetch("/api/parent/analytics");
        state.parentAnalytics = res.children_analytics || [];
      } catch (err) {
        view.innerHTML = `<div class="panel-compact"><p class="error-inline">${esc(err.message)}</p></div>`;
        return;
      }
    }

    const kids = state.parentAnalytics;
    if (!kids.length) {
      view.innerHTML = `<div class="panel-compact"><p class="muted-text">—</p></div>`;
      return;
    }

    if (state.activeChildIdx >= kids.length) state.activeChildIdx = 0;
    const ch = kids[state.activeChildIdx];
    const k = ch.kpis;
    const childReports = (state.auth.reports || []).filter((r) => r.student_id === ch.student_id);

    const maxDay = Math.max(1, ...ch.daily_7d.map((d) => d.count));
    const barW = 28;
    const gap = 14;
    const svgW = ch.daily_7d.length * (barW + gap) + gap;
    const svgBars = ch.daily_7d
      .map((d, i) => {
        const h = Math.round((d.count / maxDay) * 70);
        const x = gap + i * (barW + gap);
        const y = 86 - h;
        return `
          <rect x="${x}" y="${y}" width="${barW}" height="${Math.max(2, h)}" fill="${d.count > 0 ? "#1A4F8B" : "#D6D1C6"}" rx="2"></rect>
          <text x="${x + barW / 2}" y="106" text-anchor="middle" font-size="11" fill="#525C6A" font-family="IBM Plex Mono, monospace">${esc(d.day)}</text>
          <text x="${x + barW / 2}" y="${Math.max(12, y - 5)}" text-anchor="middle" font-size="11" fill="#121923" font-family="IBM Plex Mono, monospace">${d.count}</text>
        `;
      })
      .join("");

    view.innerHTML = `
      ${
        state.auth.sibling_discount
          ? `<div class="notice-bar notice-pass">${esc(t("siblingDiscountNote"))}</div>`
          : ""
      }

      ${
        kids.length > 1
          ? `
        <div class="panel-compact">
          <div class="field-label">${esc(t("childSwitchLabel"))}</div>
          <div class="child-tabs">
            ${kids
              .map(
                (kid, idx) =>
                  `<button type="button" class="btn btn-secondary btn-sm child-switch-btn ${idx === state.activeChildIdx ? "active" : ""}" data-idx="${idx}">${esc(
                    kid.student_name
                  )} (${esc(formatGradeLabel(kid.grade))})</button>`
              )
              .join("")}
          </div>
        </div>
      `
          : ""
      }

      <div class="panel-compact">
        <div class="ledger-row-head">
          <div>
            <h2 class="h2-section" style="margin:0;">${esc(ch.student_name)}</h2>
            <div class="doc-meta">${esc(formatGradeLabel(ch.grade))} · ${esc(ch.format)}${ch.stream && ch.stream !== "General" ? " · " + esc(ch.stream) : ""}</div>
          </div>
          <span class="status-tag ${ch.is_linked ? "is-pass" : "is-warn"}">${esc(ch.is_linked ? t("linkedTag") : t("sharedPhoneTag"))}</span>
        </div>
        ${
          !ch.is_linked && ch.invite_url
            ? `
          <div class="notice-bar notice-info" style="margin-top:10px; margin-bottom:0;">
            <p style="margin:0 0 8px 0;">${esc(t("notLinkedNote"))}</p>
            <div class="btn-row">
              <button type="button" class="btn btn-primary btn-sm" id="btnCopyChildInv">${esc(t("copyInvite"))}</button>
              <a class="btn btn-secondary btn-sm" target="_blank" href="https://t.me/share/url?url=${encodeURIComponent(ch.invite_url)}">${esc(t("shareTg"))}</a>
            </div>
          </div>
        `
            : ""
        }
      </div>

      <div class="kpi-ledger">
        <div class="kpi-cell">
          <div class="kpi-value">${k.pdfs_opened}</div>
          <div class="kpi-label">${esc(t("kpiPdfs"))}</div>
          <div class="kpi-sub">${k.total_views} ${esc(t("kpiViews"))}</div>
        </div>
        <div class="kpi-cell">
          <div class="kpi-value">${k.quizzes_taken}</div>
          <div class="kpi-label">${esc(t("kpiQuizzes"))}</div>
          <div class="kpi-sub">${k.avg_quiz_pct != null ? `${t("kpiAvg")}: ${k.avg_quiz_pct}%` : "—"}</div>
        </div>
        <div class="kpi-cell">
          <div class="kpi-value">${k.plan_pct}%</div>
          <div class="kpi-label">${esc(t("kpiPlan"))}</div>
          <div class="kpi-sub">${k.plan_done}/${k.plan_total} ${esc(t("doneLabel"))}</div>
        </div>
        <div class="kpi-cell">
          <div class="kpi-value">${k.offline_saved}</div>
          <div class="kpi-label">${esc(t("kpiSaved"))}</div>
          <div class="kpi-sub">${k.bookmarks_count} ${esc(t("kpiBookmarks"))}</div>
        </div>
      </div>

      <div class="panel-compact">
        <h3 class="h3-sub">${esc(t("chart7d"))}</h3>
        <div class="chart-wrap">
          <svg class="activity-svg" viewBox="0 0 ${svgW} 120" preserveAspectRatio="xMidYMid meet">
            <line x1="0" y1="86" x2="${svgW}" y2="86" stroke="#D6D1C6" stroke-width="1" />
            ${svgBars}
          </svg>
        </div>
      </div>

      <div class="panel-compact">
        <h3 class="h3-sub">${esc(t("quizTrendTitle"))}</h3>
        ${
          ch.quiz_trend.length
            ? `
          <table class="data-table">
            <thead><tr><th>Quiz</th><th>${esc(t("subjCol"))}</th><th>${esc(t("scoreLabel"))}</th></tr></thead>
            <tbody>
              ${ch.quiz_trend
                .map(
                  (q) =>
                    `<tr><td>${esc(q.label)}</td><td>${esc(q.subject)}</td><td class="mono-num">${esc(q.score_text)}</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        `
            : `<p class="muted-text">${esc(t("noQuizzesYet"))}</p>`
        }
      </div>

      ${
        ch.subject_stats.length
          ? `
        <div class="panel-compact">
          <h3 class="h3-sub">${esc(t("subjBreakdownTitle"))}</h3>
          <table class="data-table">
            <thead><tr><th>${esc(t("subjCol"))}</th><th>${esc(t("viewsCol"))}</th><th>${esc(t("quizzesCol"))}</th><th>${esc(t("avgCol"))}</th></tr></thead>
            <tbody>
              ${ch.subject_stats
                .map(
                  (s) =>
                    `<tr><td>${esc(s.subject)}</td><td class="mono-num">${s.views}</td><td class="mono-num">${s.quizzes}</td><td class="mono-num">${
                      s.avg_pct != null ? s.avg_pct + "%" : "—"
                    }</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `
          : ""
      }

      ${
        ch.recent_reads.length
          ? `
        <div class="panel-compact">
          <h3 class="h3-sub">${esc(t("recentActivityTitle"))}</h3>
          <div class="compact-list">
            ${ch.recent_reads
              .map(
                (r) =>
                  `<div class="compact-row"><span class="doc-title">${esc(r.file_name)}</span><span class="meta-line mono-num">${esc(t("pageWord"))} ${r.page}</span></div>`
              )
              .join("")}
          </div>
        </div>
      `
          : ""
      }

      <div class="panel-compact">
        <h3 class="h3-sub">${esc(t("biweeklyReportsTitle"))}</h3>
        ${
          childReports.length
            ? `<div class="stack-gap">${childReports
                .map(
                  (rp) => `
                <article class="report-block">
                  <div class="ledger-row-head">
                    <strong>${esc(rp.period)}</strong>
                    <span class="meta-line">${esc(rp.tutor_name || "")}</span>
                  </div>
                  <div class="report-grid">
                    <div><strong>${esc(t("attendanceLbl"))}:</strong> ${esc(rp.attendance)}</div>
                    <div><strong>${esc(t("scoresLbl"))}:</strong> ${esc(rp.scores_text)}</div>
                    <div><strong>${esc(t("improvedLbl"))}:</strong> ${esc(rp.improved_note)}</div>
                    <div><strong>${esc(t("focusLbl"))}:</strong> ${esc(rp.focus_note)}</div>
                  </div>
                </article>
              `
                )
                .join("")}</div>`
            : `<p class="muted-text">${esc(t("noReportsYet"))}</p>`
        }
      </div>
    `;

    view.querySelectorAll(".child-switch-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.activeChildIdx = Number(btn.dataset.idx);
        renderParentView();
      });
    });

    const copyBtn = document.getElementById("btnCopyChildInv");
    if (copyBtn && ch.invite_url) {
      copyBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(ch.invite_url);
          showToast(t("copied"));
        } catch (_) {}
      });
    }
  }

  // ==================== ACCOUNT & SQUAD VIEW ====================
  function renderAccountView() {
    const a = state.auth;
    const view = document.getElementById("viewAccount");
    if (!view || !a) return;
    const statusClass =
      a.status === "APPROVED" ? "is-pass" : a.status === "EXPIRED" || a.status === "LEFT" ? "is-rubric" : "is-warn";

    const botUser = a.bot_username || "";
    const inviteLink = botUser && a.referral_code ? `https://t.me/${botUser}?start=ref_${a.referral_code}` : "";

    view.innerHTML = `
      <div class="panel-compact">
        <h2 class="h2-section">${esc(t("accountTitle"))}</h2>
        <table class="data-table">
          <tbody>
            <tr><th>${esc(t("nameLbl"))}</th><td>${esc(a.name)}</td></tr>
            <tr><th>${esc(t("roleLbl"))}</th><td>${esc(a.role === "parent" ? t("roleParent") : t("roleStudent"))}</td></tr>
            <tr><th>${esc(t("gradeWord"))}</th><td>${esc(formatGradeLabel(a.grade))}${a.stream && a.stream !== "General" ? " (" + esc(a.stream) + ")" : ""}</td></tr>
            <tr><th>${esc(t("statusLbl"))}</th><td><span class="status-tag ${statusClass}">${esc(a.status)}</span></td></tr>
            <tr><th>${esc(t("tierLbl"))}</th><td><span class="mono-num">${esc(a.tier)}</span></td></tr>
            ${
              a.days_left != null
                ? `<tr><th>${esc(t("daysRemainLbl"))}</th><td class="mono-num">${a.days_left}</td></tr>`
                : ""
            }
          </tbody>
        </table>
      </div>

      ${
        a.children && a.children.length
          ? `
        <div class="panel-compact">
          <h2 class="h2-section">${esc(t("childrenSectionTitle"))}</h2>
          <div class="compact-list">
            ${a.children
              .map(
                (ch) => `
              <div class="compact-row">
                <div>
                  <div class="doc-title">${esc(ch.student_name)}</div>
                  <div class="doc-meta">${esc(formatGradeLabel(ch.grade))} · ${esc(ch.format)}</div>
                </div>
                <span class="status-tag ${ch.is_linked ? "is-pass" : "is-warn"}">${esc(ch.is_linked ? t("linkedTag") : t("sharedPhoneTag"))}</span>
              </div>
            `
              )
              .join("")}
          </div>
        </div>
      `
          : ""
      }

      ${
        a.referral_code
          ? `
        <div class="panel-compact">
          <h2 class="h2-section">${esc(t("squadTitle"))}</h2>
          <p class="muted-text" style="margin-bottom:10px;">${esc(t("squadDesc"))}</p>
          <table class="data-table" style="margin-bottom:10px;">
            <tbody>
              <tr><th>${esc(t("yourCode"))}</th><td class="mono-num"><strong>${esc(a.referral_code)}</strong></td></tr>
              <tr><th>${esc(t("verifiedRefs"))}</th><td class="mono-num">${a.referral_count || 0}</td></tr>
            </tbody>
          </table>
          <div class="btn-row">
            <button type="button" id="btnCopyRefCode" class="btn btn-primary btn-sm">${esc(t("copyCode"))}</button>
            ${
              inviteLink
                ? `<a class="btn btn-secondary btn-sm" target="_blank" href="https://t.me/share/url?url=${encodeURIComponent(inviteLink)}&text=${encodeURIComponent(
                    "Join Qelal Learning (Bishoftu) with my Study Squad code: " + a.referral_code
                  )}">${esc(t("shareTg"))}</a>`
                : ""
            }
          </div>
        </div>
      `
          : ""
      }

      <div class="panel-compact">
        <h2 class="h2-section">${esc(t("supportTitle"))}</h2>
        <div class="btn-row">
          <a href="tel:+251933510682" class="btn btn-secondary btn-sm">+251 933 510 682</a>
          <a href="tel:+251988666328" class="btn btn-secondary btn-sm">+251 988 666 328</a>
        </div>
      </div>
    `;

    const refBtn = document.getElementById("btnCopyRefCode");
    if (refBtn) {
      refBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(a.referral_code);
          showToast(t("copied"));
        } catch (_) {}
      });
    }
  }

  // ==================== ADMIN CONSOLE VIEW ====================
  function stopAdminJobPolling() {
    if (state.adminPollTimer) {
      clearInterval(state.adminPollTimer);
      state.adminPollTimer = null;
    }
  }

  function renderAdminJobsBox(jobs) {
    const box = document.getElementById("adminJobsBox");
    if (!box) return;
    const sync = (jobs && jobs.sync) || {};
    const verify = (jobs && jobs.verify) || {};

    const syncTag = sync.running ? "is-warn" : sync.ok === false ? "is-rubric" : sync.ok === true ? "is-pass" : "";
    const verifyTag = verify.running ? "is-warn" : verify.ok === false ? "is-rubric" : verify.ok === true ? "is-pass" : "";

    box.innerHTML = `
      <div class="compact-list">
        <div class="compact-row">
          <div style="min-width:0;">
            <div class="doc-title">Google Drive Sync</div>
            <div class="doc-meta">${esc(sync.running ? sync.message || "Running..." : sync.last_summary || sync.message || "Idle")}${sync.updated_at ? " · " + esc(sync.updated_at) : ""}</div>
          </div>
          <span class="status-tag ${syncTag}">${esc(sync.running ? "RUNNING" : sync.ok === false ? "FAILED" : sync.ok === true ? "DONE" : "IDLE")}</span>
        </div>
        <div class="compact-row">
          <div style="min-width:0;">
            <div class="doc-title">PDF Link Verification</div>
            <div class="doc-meta">${esc(verify.running ? verify.message || "Running..." : verify.last_summary || verify.message || "Idle")}${verify.updated_at ? " · " + esc(verify.updated_at) : ""}</div>
          </div>
          <span class="status-tag ${verifyTag}">${esc(verify.running ? "RUNNING" : verify.ok === false ? "FAILED" : verify.ok === true ? "DONE" : "IDLE")}</span>
        </div>
      </div>
    `;

    const btnSync = document.getElementById("btnAdminSyncDrive");
    const btnVerify = document.getElementById("btnAdminVerifyLinks");
    const btnForce = document.getElementById("btnAdminForceVerify");
    if (btnSync) btnSync.disabled = !!sync.running;
    if (btnVerify) btnVerify.disabled = !!verify.running;
    if (btnForce) btnForce.disabled = !!verify.running;
  }

  function startAdminJobPolling() {
    if (state.adminPollTimer) return;
    state.adminPollTimer = setInterval(async () => {
      if (state.activeTab !== "admin") {
        stopAdminJobPolling();
        return;
      }
      try {
        const res = await apiFetch("/api/admin/job-status");
        const jobs = res.jobs || {};
        const prevSync = state.adminOverview && state.adminOverview.jobs && state.adminOverview.jobs.sync && state.adminOverview.jobs.sync.running;
        const prevVerify = state.adminOverview && state.adminOverview.jobs && state.adminOverview.jobs.verify && state.adminOverview.jobs.verify.running;
        if (state.adminOverview) {
          state.adminOverview.jobs = jobs;
        }
        renderAdminJobsBox(jobs);

        const nowRunning = !!(jobs.sync && jobs.sync.running) || !!(jobs.verify && jobs.verify.running);
        if (!nowRunning) {
          stopAdminJobPolling();
          if (prevSync || prevVerify) {
            await renderAdminView(true);
            await loadLibrary(true);
          }
        }
      } catch (_) {}
    }, 4000);
  }

  function renderAdminAccountsList() {
    const listEl = document.getElementById("admAccountsList");
    const headEl = document.getElementById("admAccountsCount");
    if (!listEl || !state.adminOverview) return;

    const regs = (state.adminOverview.registrations || []).filter((r) => {
      if (state.adminAccountFilter !== "ALL" && r.status !== state.adminAccountFilter) return false;
      if (state.adminAccountSearch) {
        const hay = `${r.name} ${r.phone} ${r.grade} ${r.referral_code}`.toLowerCase();
        if (!hay.includes(state.adminAccountSearch.toLowerCase())) return false;
      }
      return true;
    });

    if (headEl) headEl.textContent = `${esc(t("adminAccountsTitle"))} (${regs.length})`;

    listEl.innerHTML = regs.length
      ? regs
          .map(
            (r) => `
          <div class="ledger-row">
            <div class="ledger-row-head">
              <div>
                <div class="doc-title">${esc(r.name)} <span class="meta-line">(${esc(r.role)})</span></div>
                <div class="doc-meta">${esc(r.grade)} · ${esc(r.phone)} · M${r.months_paid || 0} ${r.expires_on ? "· Exp " + esc(r.expires_on) : ""}</div>
              </div>
              <span class="status-tag ${r.status === "APPROVED" ? "is-pass" : r.status === "NEW" ? "is-warn" : "is-rubric"}">${esc(r.status)}</span>
            </div>
            <div class="btn-row">
              ${
                r.status === "NEW"
                  ? `<button type="button" class="btn btn-primary btn-sm adm-act-btn" data-tg="${esc(r.tg_id)}" data-act="approve">${esc(t("approve30d"))}</button>`
                  : `<button type="button" class="btn btn-primary btn-sm adm-act-btn" data-tg="${esc(r.tg_id)}" data-act="mark_paid">${esc(t("renew30d"))}</button>`
              }
              <button type="button" class="btn btn-secondary btn-sm adm-act-btn" data-tg="${esc(r.tg_id)}" data-act="mark_left">${esc(t("markLeft"))}</button>
              <button type="button" class="btn btn-danger btn-sm adm-act-btn" data-tg="${esc(r.tg_id)}" data-act="reject">${esc(t("rejectBtn"))}</button>
            </div>
          </div>
        `
          )
          .join("")
      : `<div class="ledger-row"><p class="muted-text">—</p></div>`;

    listEl.querySelectorAll(".adm-act-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await apiFetch("/api/admin/student-action", {
            method: "POST",
            body: JSON.stringify({ tg_id: btn.dataset.tg, action: btn.dataset.act }),
          });
          showToast(t("actionDone"));
          await renderAdminView(true);
        } catch (err) {
          showToast(err.message, true);
          btn.disabled = false;
        }
      });
    });
  }

  function renderAdminPdfsList() {
    const listEl = document.getElementById("admPdfsList");
    const headEl = document.getElementById("admPdfsCount");
    const moreWrap = document.getElementById("admPdfsMoreWrap");
    if (!listEl || !state.adminOverview) return;

    const allPdfs = state.adminOverview.pdfs || [];
    const filtered = allPdfs.filter((p) => {
      if (state.adminPdfFilter === "VERIFIED") {
        if (p.link_status !== "AUTO_VERIFIED" && p.link_status !== "MANUAL_VERIFIED") return false;
      } else if (state.adminPdfFilter === "NEEDS_REVIEW") {
        if (p.link_status !== "NEEDS_REVIEW") return false;
      } else if (state.adminPdfFilter === "REJECTED") {
        if (p.link_status !== "REJECTED_MISMATCH") return false;
      } else if (state.adminPdfFilter === "UNVERIFIED") {
        if (p.link_status && p.link_status !== "UNVERIFIED") return false;
      } else if (state.adminPdfFilter === "HAS_QUIZ") {
        if (!p.has_quiz) return false;
      } else if (state.adminPdfFilter === "TRIAL_PICK") {
        if (!p.is_trial) return false;
      }

      if (state.adminPdfSearch) {
        const hay = `${p.doc_id} ${p.file_name} ${p.grade} ${p.subject} ${p.category} ${p.link_status}`.toLowerCase();
        if (!hay.includes(state.adminPdfSearch.toLowerCase())) return false;
      }
      return true;
    });

    if (headEl) headEl.textContent = `${esc(t("adminPdfTitle"))} (${filtered.length})`;

    const shown = filtered.slice(0, state.adminPdfLimit);
    listEl.innerHTML = shown.length
      ? shown
          .map((p) => {
            const st = p.link_status || "UNVERIFIED";
            const tagClass =
              st === "AUTO_VERIFIED" || st === "MANUAL_VERIFIED"
                ? "is-pass"
                : st === "NEEDS_REVIEW"
                ? "is-warn"
                : st === "REJECTED_MISMATCH"
                ? "is-rubric"
                : "";
            const metaLine = [
              p.doc_id,
              p.grade,
              p.subject,
              p.category,
              p.file_size_mb ? `${p.file_size_mb} MB` : "",
              p.source,
              p.has_quiz ? `Quiz ${p.quiz_total_q}Q` : "",
            ]
              .filter(Boolean)
              .join(" · ");
            const linkLine = p.linked_doc_id
              ? `<div class="doc-meta">Linked: ${esc(p.linked_doc_id)}${p.linked_file_name ? " — " + esc(p.linked_file_name) : ""}</div>`
              : "";

            return `
              <div class="ledger-row">
                <div class="ledger-row-head">
                  <div style="min-width:0;">
                    <div class="doc-title">${esc(p.file_name)}</div>
                    <div class="doc-meta">${esc(metaLine)}</div>
                    ${linkLine}
                  </div>
                  <span class="status-tag ${tagClass}">${esc(st)}</span>
                </div>
                <div class="btn-row">
                  <button type="button" class="btn btn-secondary btn-sm adm-pdf-trial ${p.is_trial ? "active" : ""}" data-doc="${esc(p.doc_id)}" data-trial="${p.is_trial ? "1" : "0"}">${esc(
                    p.is_trial ? t("isTrialPick") : t("setTrialPick")
                  )}</button>
                  ${
                    p.linked_doc_id && st === "NEEDS_REVIEW"
                      ? `<button type="button" class="btn btn-primary btn-sm adm-pdf-link" data-doc="${esc(p.doc_id)}" data-act="confirm">${esc(t("confirmLinkBtn"))}</button>
                         <button type="button" class="btn btn-danger btn-sm adm-pdf-link" data-doc="${esc(p.doc_id)}" data-act="unlink">${esc(t("unlinkBtn"))}</button>`
                      : p.linked_doc_id
                      ? `<button type="button" class="btn btn-danger btn-sm adm-pdf-link" data-doc="${esc(p.doc_id)}" data-act="unlink">${esc(t("unlinkBtn"))}</button>`
                      : ""
                  }
                </div>
              </div>
            `;
          })
          .join("")
      : `<div class="ledger-row"><p class="muted-text">—</p></div>`;

    if (moreWrap) {
      if (filtered.length > shown.length) {
        moreWrap.innerHTML = `<button type="button" id="btnAdmPdfsMore" class="btn btn-secondary btn-sm">${esc(t("showMoreBtn"))} (${filtered.length - shown.length})</button>`;
        document.getElementById("btnAdmPdfsMore").addEventListener("click", () => {
          state.adminPdfLimit += 40;
          renderAdminPdfsList();
        });
      } else {
        moreWrap.innerHTML = "";
      }
    }

    listEl.querySelectorAll(".adm-pdf-trial").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          const nextTrial = btn.dataset.trial !== "1";
          await apiFetch("/api/admin/toggle-trial", {
            method: "POST",
            body: JSON.stringify({ doc_id: btn.dataset.doc, is_trial: nextTrial }),
          });
          showToast(t("actionDone"));
          await renderAdminView(true);
          await loadLibrary(true);
        } catch (err) {
          showToast(err.message, true);
          btn.disabled = false;
        }
      });
    });

    listEl.querySelectorAll(".adm-pdf-link").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await apiFetch("/api/admin/link-action", {
            method: "POST",
            body: JSON.stringify({ doc_id: btn.dataset.doc, action: btn.dataset.act }),
          });
          showToast(t("actionDone"));
          await renderAdminView(true);
          await loadLibrary(true);
        } catch (err) {
          showToast(err.message, true);
          btn.disabled = false;
        }
      });
    });
  }

  async function renderAdminView(forceReload = false) {
    const view = document.getElementById("viewAdmin");
    if (!view) return;
    if (!state.adminOverview || forceReload) {
      view.innerHTML = `<div class="panel-compact"><p class="muted-text">${esc(t("loading"))}</p></div>`;
      try {
        const url = forceReload ? "/api/admin/overview?refresh=true" : "/api/admin/overview";
        state.adminOverview = await apiFetch(url);
      } catch (err) {
        view.innerHTML = `<div class="panel-compact"><p class="error-inline">${esc(err.message)}</p></div>`;
        return;
      }
    }

    const ov = state.adminOverview;
    const sum = ov.summary || {};
    const cfg = ov.config || {};
    const jobs = ov.jobs || {};

    const pdfFilterTabs = [
      { id: "ALL", label: `ALL (${sum.total_pdfs || 0})` },
      { id: "VERIFIED", label: `VERIFIED (${sum.verified_links || 0})` },
      { id: "NEEDS_REVIEW", label: `REVIEW (${sum.needs_review || 0})` },
      { id: "REJECTED", label: `REJECTED (${sum.rejected_links || 0})` },
      { id: "UNVERIFIED", label: `UNVERIFIED (${sum.unverified_links || 0})` },
      { id: "HAS_QUIZ", label: `QUIZ (${sum.quiz_keys || 0})` },
      { id: "TRIAL_PICK", label: `TRIAL (${sum.trial_picks || 0})` },
    ];

    view.innerHTML = `
      <div class="kpi-ledger">
        <div class="kpi-cell"><div class="kpi-value">${sum.APPROVED || 0}</div><div class="kpi-label">Approved</div></div>
        <div class="kpi-cell"><div class="kpi-value">${sum.NEW || 0}</div><div class="kpi-label">Pending NEW</div></div>
        <div class="kpi-cell"><div class="kpi-value">${sum.total_students || 0}</div><div class="kpi-label">Students</div></div>
        <div class="kpi-cell"><div class="kpi-value">${sum.total_pdfs || 0}</div><div class="kpi-label">PDFs (${sum.quiz_keys || 0} keys)</div></div>
      </div>

      <section class="admin-section">
        <div class="ledger-row-head">
          <h2 class="h2-section" style="margin:0;">${esc(t("adminSyncTitle"))}</h2>
          <button type="button" id="btnAdminRefreshAll" class="btn btn-secondary btn-sm">${esc(t("refreshAdminBtn"))}</button>
        </div>
        <div id="adminJobsBox"></div>
        <div class="btn-row">
          <button type="button" id="btnAdminSyncDrive" class="btn btn-primary btn-sm">${esc(t("syncDriveBtn"))}</button>
          <button type="button" id="btnAdminVerifyLinks" class="btn btn-primary btn-sm">${esc(t("verifyLinksBtn"))}</button>
          <button type="button" id="btnAdminForceVerify" class="btn btn-secondary btn-sm">${esc(t("forceVerifyBtn"))}</button>
        </div>
      </section>

      <section class="admin-section">
        <h2 id="admPdfsCount" class="h2-section" style="margin:0;">${esc(t("adminPdfTitle"))} (${sum.total_pdfs || 0})</h2>
        <div class="btn-row">
          ${pdfFilterTabs
            .map(
              (tb) =>
                `<button type="button" class="btn btn-secondary btn-sm adm-pdf-filter-btn ${state.adminPdfFilter === tb.id ? "active" : ""}" data-pf="${tb.id}">${esc(tb.label)}</button>`
            )
            .join("")}
        </div>
        <input id="admPdfSearchInput" type="search" class="input" placeholder="Search DOC-ID, file name, grade, subject..." value="${esc(state.adminPdfSearch)}" />
        <div id="admPdfsList" class="ledger-list"></div>
        <div id="admPdfsMoreWrap" style="margin-top:8px;"></div>
      </section>

      <section class="admin-section">
        <h2 class="h2-section" style="margin:0;">${esc(t("adminConfigTitle"))}</h2>
        <div class="form-row-2">
          <div class="field-group" style="margin:0;">
            <label class="field-label">Launch Mode</label>
            <select id="admCfgMode" class="select">
              <option value="OPEN_LAUNCH" ${cfg.LAUNCH_MODE === "OPEN_LAUNCH" ? "selected" : ""}>OPEN_LAUNCH</option>
              <option value="PAID_GATED" ${cfg.LAUNCH_MODE === "PAID_GATED" ? "selected" : ""}>PAID_GATED</option>
            </select>
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Grade 12 Matric Date</label>
            <input id="admCfgMatric" type="date" class="input" value="${esc(cfg.MATRIC_DATE || "")}" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Grade 8 Ministry Date</label>
            <input id="admCfgG8" type="date" class="input" value="${esc(cfg.GRADE8_MINISTRY_DATE || "")}" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Grade 6 Ministry Date</label>
            <input id="admCfgG6" type="date" class="input" value="${esc(cfg.GRADE6_MINISTRY_DATE || "")}" />
          </div>
        </div>
        <div class="field-group" style="margin:0;">
          <label class="field-label">Semester Target Date</label>
          <input id="admCfgSem" type="date" class="input" value="${esc(cfg.SEMESTER_DATE || "")}" />
        </div>
        <div>
          <button type="button" id="btnSaveAdminCfg" class="btn btn-primary btn-sm">${esc(t("saveConfig"))}</button>
        </div>
      </section>

      <section class="admin-section">
        <h2 class="h2-section" style="margin:0;">${esc(t("adminPublishTitle"))}</h2>
        <div class="form-row-2">
          <div class="field-group" style="margin:0;">
            <label class="field-label">Student</label>
            <select id="admRptStudent" class="select">
              ${(ov.students || [])
                .map((s) => `<option value="${esc(s.student_id)}">${esc(s.student_name)} (${esc(s.grade)})</option>`)
                .join("")}
            </select>
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Period</label>
            <input id="admRptPeriod" type="text" class="input" placeholder="e.g. Week 1–2" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Attendance</label>
            <input id="admRptAtt" type="text" class="input" placeholder="e.g. 4/4 sessions" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Tutor</label>
            <input id="admRptTutor" type="text" class="input" value="Qelal Coordinator" />
          </div>
        </div>
        <div class="field-group" style="margin:0;">
          <label class="field-label">Diagnostic &amp; Quiz Scores</label>
          <input id="admRptScores" type="text" class="input" placeholder="e.g. Math 84%, Physics 78%" />
        </div>
        <div class="form-row-2">
          <div class="field-group" style="margin:0;">
            <label class="field-label">What Improved</label>
            <input id="admRptImproved" type="text" class="input" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Next 2-Week Focus</label>
            <input id="admRptFocus" type="text" class="input" />
          </div>
        </div>
        <div>
          <button type="button" id="btnAdminPubReport" class="btn btn-primary btn-sm">${esc(t("publishReportBtn"))}</button>
        </div>
      </section>

      <section class="admin-section">
        <h2 class="h2-section" style="margin:0;">${esc(t("adminBroadcastTitle"))}</h2>
        <div class="field-group" style="margin:0;">
          <label class="field-label">Target Audience</label>
          <select id="admBcTarget" class="select">
            <option value="all">All Registered Accounts</option>
            <option value="parents">All Parents</option>
            <option value="approved">Approved Accounts</option>
            <option value="new">Pending (NEW) Accounts</option>
            <option value="natural">Natural Science Students</option>
            <option value="social">Social Science Students</option>
            <option value="grade_12">Grade 12</option>
            <option value="grade_8">Grade 8</option>
            <option value="grade_6">Grade 6</option>
          </select>
        </div>
        <textarea id="admBcMsg" class="textarea" placeholder="Write announcement message..."></textarea>
        <div>
          <button type="button" id="btnAdminBroadcast" class="btn btn-primary btn-sm">${esc(t("sendBroadcastBtn"))}</button>
        </div>
      </section>

      <section class="admin-section">
        <h2 id="admAccountsCount" class="h2-section" style="margin:0;">${esc(t("adminAccountsTitle"))}</h2>
        <div class="btn-row">
          ${["ALL", "NEW", "APPROVED", "EXPIRED", "LEFT"]
            .map(
              (st) =>
                `<button type="button" class="btn btn-secondary btn-sm adm-filter-btn ${state.adminAccountFilter === st ? "active" : ""}" data-st="${st}">${st}</button>`
            )
            .join("")}
        </div>
        <input id="admSearchInput" type="search" class="input" placeholder="Filter by name, phone, grade..." value="${esc(state.adminAccountSearch)}" />
        <div id="admAccountsList" class="ledger-list"></div>
      </section>
    `;

    renderAdminJobsBox(jobs);
    renderAdminPdfsList();
    renderAdminAccountsList();

    if ((jobs.sync && jobs.sync.running) || (jobs.verify && jobs.verify.running)) {
      startAdminJobPolling();
    } else {
      stopAdminJobPolling();
    }

    document.getElementById("btnAdminRefreshAll").addEventListener("click", () => renderAdminView(true));

    document.getElementById("btnAdminSyncDrive").addEventListener("click", async () => {
      try {
        const res = await apiFetch("/api/admin/sync-drive", { method: "POST" });
        if (res.jobs) {
          state.adminOverview.jobs = res.jobs;
          renderAdminJobsBox(res.jobs);
        }
        startAdminJobPolling();
        showToast(res.already_running ? res.detail : "Google Drive sync started...");
      } catch (err) {
        showToast(err.message, true);
      }
    });

    const triggerVerify = async (force) => {
      try {
        const res = await apiFetch("/api/admin/verify-links", {
          method: "POST",
          body: JSON.stringify({ force }),
        });
        if (res.jobs) {
          state.adminOverview.jobs = res.jobs;
          renderAdminJobsBox(res.jobs);
        }
        startAdminJobPolling();
        showToast(res.already_running ? res.detail : "PDF verification started...");
      } catch (err) {
        showToast(err.message, true);
      }
    };
    document.getElementById("btnAdminVerifyLinks").addEventListener("click", () => triggerVerify(false));
    document.getElementById("btnAdminForceVerify").addEventListener("click", () => triggerVerify(true));

    view.querySelectorAll(".adm-pdf-filter-btn").forEach((b) => {
      b.addEventListener("click", () => {
        state.adminPdfFilter = b.dataset.pf;
        state.adminPdfLimit = 40;
        view.querySelectorAll(".adm-pdf-filter-btn").forEach((x) =>
          x.classList.toggle("active", x.dataset.pf === state.adminPdfFilter)
        );
        renderAdminPdfsList();
      });
    });

    document.getElementById("admPdfSearchInput").addEventListener("input", (e) => {
      state.adminPdfSearch = e.target.value;
      state.adminPdfLimit = 40;
      renderAdminPdfsList();
    });

    document.getElementById("btnSaveAdminCfg").addEventListener("click", async () => {
      try {
        await apiFetch("/api/admin/config", {
          method: "POST",
          body: JSON.stringify({
            LAUNCH_MODE: document.getElementById("admCfgMode").value,
            MATRIC_DATE: document.getElementById("admCfgMatric").value,
            GRADE8_MINISTRY_DATE: document.getElementById("admCfgG8").value,
            GRADE6_MINISTRY_DATE: document.getElementById("admCfgG6").value,
            SEMESTER_DATE: document.getElementById("admCfgSem").value,
          }),
        });
        showToast(t("actionDone"));
        await authenticate();
      } catch (err) {
        showToast(err.message, true);
      }
    });

    document.getElementById("btnAdminPubReport").addEventListener("click", async () => {
      try {
        await apiFetch("/api/admin/publish-report", {
          method: "POST",
          body: JSON.stringify({
            student_id: document.getElementById("admRptStudent").value,
            period: document.getElementById("admRptPeriod").value,
            attendance: document.getElementById("admRptAtt").value,
            scores_text: document.getElementById("admRptScores").value,
            improved_note: document.getElementById("admRptImproved").value,
            focus_note: document.getElementById("admRptFocus").value,
            tutor_name: document.getElementById("admRptTutor").value,
          }),
        });
        showToast(t("actionDone"));
        document.getElementById("admRptScores").value = "";
        document.getElementById("admRptImproved").value = "";
        document.getElementById("admRptFocus").value = "";
      } catch (err) {
        showToast(err.message, true);
      }
    });

    document.getElementById("btnAdminBroadcast").addEventListener("click", async () => {
      const target = document.getElementById("admBcTarget").value;
      const message = document.getElementById("admBcMsg").value.trim();
      if (!message) return;
      try {
        const res = await apiFetch("/api/admin/broadcast", {
          method: "POST",
          body: JSON.stringify({ target, message }),
        });
        document.getElementById("admBcMsg").value = "";
        showToast(`Sent: ${res.sent} | Failed: ${res.failed}`);
      } catch (err) {
        showToast(err.message, true);
      }
    });

    view.querySelectorAll(".adm-filter-btn").forEach((b) => {
      b.addEventListener("click", () => {
        state.adminAccountFilter = b.dataset.st;
        view.querySelectorAll(".adm-filter-btn").forEach((x) =>
          x.classList.toggle("active", x.dataset.st === state.adminAccountFilter)
        );
        renderAdminAccountsList();
      });
    });

    document.getElementById("admSearchInput").addEventListener("input", (e) => {
      state.adminAccountSearch = e.target.value;
      renderAdminAccountsList();
    });
  }

  // ==================== LEGAL MODALS ====================
  function openLegalModal(kind) {
    const titleEl = document.getElementById("legalModalTitle");
    const bodyEl = document.getElementById("legalModalBody");
    if (!titleEl || !bodyEl) return;

    if (kind === "terms") {
      titleEl.textContent = t("legalTerms");
      bodyEl.innerHTML = `
        <h3>1. Program Scope &amp; Tuition</h3>
        <p>Qelal Learning (ቀላል) operates weekend exam preparation cohorts, 1-on-1 home tutoring in Bishoftu, and the Qelal Digital Study Hub inside Telegram for Grades 1–12. Monthly tuition for in-person programs is payable upfront prior to the first session of each 30-day cycle.</p>
        <h3>2. Digital Access &amp; Copyright</h3>
        <p>Study materials, unit notes, and answer keys inside the Qelal Digital Study Hub are licensed solely for personal study by registered Qelal students and parents. Forwarding, reselling, or mass-distributing protected documents is prohibited.</p>
        <h3>3. First-Session Fit Guarantee</h3>
        <p>For 1-on-1 home tutoring, if the assigned mentor is not the right learning fit after the first session, Qelal Learning will rematch the student with another vetted instructor at no extra cost. Cancellations or reschedules require 24 hours' notice.</p>
        <h3>4. Direct Payment &amp; Non-Circumvention</h3>
        <p>All tuition payments are made directly to Qelal Learning rather than directly to tutors. Families agree not to engage Qelal-introduced tutors privately outside the platform during active enrollment and for 12 months following the final session. Private off-platform arrangements void Qelal progress reports, practice packs, and digital vault access.</p>
        <h3>5. Bishoftu Support</h3>
        <p>Questions regarding billing, schedules, or membership renewals can be directed to +251 933 510 682 or +251 988 666 328.</p>
      `;
    } else {
      titleEl.textContent = t("legalPrivacy");
      bodyEl.innerHTML = `
        <h3>1. Information Collected</h3>
        <p>When you register in Qelal Learning, we store your Telegram user ID, Telegram username (if set), full name, phone number, selected grade/stream, preferred tutoring format, and any child profiles or referral codes you provide.</p>
        <h3>2. Study &amp; Assessment Activity</h3>
        <p>To power your Continue Reading history, Study Plan checklist, and Parent Analytics dashboard, the portal records documents opened, last page read, bookmarks, quiz scores, and bi-weekly tutor progress notes.</p>
        <h3>3. Parent–Child Linking</h3>
        <p>If a parent provides a child's phone number or Telegram @username, Qelal automatically links the student and parent records so progress reports and study activity appear accurately without creating duplicate student accounts.</p>
        <h3>4. Data Storage &amp; Access</h3>
        <p>Account records are stored securely in Qelal Learning's administrative database and verified using Telegram cryptographic initData signatures. We never sell or share student or parent contact details with third-party advertisers.</p>
        <h3>5. Updates &amp; Deletion</h3>
        <p>To update your phone number, change your grade track, or request account removal, call +251 933 510 682 or +251 988 666 328.</p>
      `;
    }

    setHidden("modalLegal", false);
  }

  // ==================== SAFE EVENT WIRING ====================
  function safeAddEvent(id, event, callback) {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener(event, callback);
    } else {
      console.warn(`Warning: Element ID #${id} not found in HTML. Skipping listener.`);
    }
  }

  function wireGlobalEvents() {
    document.querySelectorAll("#langBar .lang-btn").forEach((btn) => {
      btn.addEventListener("click", () => setLanguage(btn.dataset.lang, true));
    });
    document.querySelectorAll("#regLangCards .lang-card").forEach((card) => {
      card.addEventListener("click", () => setLanguage(card.dataset.lang, false));
    });

    safeAddEvent("outsideRetryBtn", "click", authenticate);

    document.querySelectorAll(".role-btn").forEach((btn) => {
      btn.addEventListener("click", () => setRegRole(btn.dataset.role));
    });

    document.querySelectorAll("#regStudentStreamBtns .seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.regStudentStream = btn.dataset.stream;
        document.querySelectorAll("#regStudentStreamBtns .seg-btn").forEach((b) =>
          b.classList.toggle("active", b.dataset.stream === state.regStudentStream)
        );
      });
    });

    document.querySelectorAll("#regStudentFormatBtns .seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.regStudentFormat = btn.dataset.format;
        document.querySelectorAll("#regStudentFormatBtns .seg-btn").forEach((b) =>
          b.classList.toggle("active", b.dataset.format === state.regStudentFormat)
        );
      });
    });

    document.querySelectorAll("#regParentFormatBtns .seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.regParentFormat = btn.dataset.format;
        document.querySelectorAll("#regParentFormatBtns .seg-btn").forEach((b) =>
          b.classList.toggle("active", b.dataset.format === state.regParentFormat)
        );
      });
    });

    safeAddEvent("btnAddChild", "click", () => {
      state.regChildren.push({
        name: "",
        grade: "Grade 6",
        stream: "Natural",
        format: state.regParentFormat,
        child_contact: "",
      });
      renderRegistrationDynamicParts();
    });

    safeAddEvent("regForm", "submit", handleRegisterSubmit);

    safeAddEvent("btnOpenTermsReg", "click", () => openLegalModal("terms"));
    safeAddEvent("btnOpenPrivacyReg", "click", () => openLegalModal("privacy"));
    safeAddEvent("btnOpenTermsFooter", "click", () => openLegalModal("terms"));
    safeAddEvent("btnOpenPrivacyFooter", "click", () => openLegalModal("privacy"));
    safeAddEvent("btnLegalClose", "click", () => setHidden("modalLegal", true));

    const legalModal = document.getElementById("modalLegal");
    if (legalModal) {
      legalModal.addEventListener("click", (e) => {
        if (e.target.id === "modalLegal") setHidden("modalLegal", true);
      });
    }

    safeAddEvent("libSearch", "input", (e) => {
      state.searchQuery = e.target.value;
      renderLibraryView();
    });
    safeAddEvent("filterGrade", "change", (e) => {
      state.filterGrade = e.target.value;
      renderLibraryView();
    });
    safeAddEvent("filterSubject", "change", (e) => {
      state.filterSubject = e.target.value;
      renderLibraryView();
    });
    safeAddEvent("filterCategory", "change", (e) => {
      state.filterCategory = e.target.value;
      renderLibraryView();
    });
    safeAddEvent("filterSavedBtn", "click", () => {
      state.filterSavedOnly = !state.filterSavedOnly;
      renderLibraryView();
    });

    safeAddEvent("reqToggleBtn", "click", () => {
      const box = document.getElementById("reqBox");
      if (box) box.classList.toggle("hidden");
    });
    safeAddEvent("reqSendBtn", "click", async () => {
      const subject = (document.getElementById("reqSubject")?.value || "").trim();
      const details = (document.getElementById("reqDetails")?.value || "").trim();
      const statusEl = document.getElementById("reqStatusMsg");
      if (!details) {
        if (statusEl) statusEl.textContent = t("reqEmpty");
        return;
      }
      try {
        await apiFetch("/api/request-material", {
          method: "POST",
          body: JSON.stringify({ subject, details }),
        });
        if (document.getElementById("reqSubject")) document.getElementById("reqSubject").value = "";
        if (document.getElementById("reqDetails")) document.getElementById("reqDetails").value = "";
        if (statusEl) statusEl.textContent = t("reqSent");
      } catch (err) {
        if (statusEl) statusEl.textContent = err.message;
      }
    });

    const addCustomTask = async () => {
      const inp = document.getElementById("customTaskInput");
      if (!inp) return;
      const text = inp.value.trim();
      if (!text) return;
      state.progress.custom_plan.push({ id: "cust_" + Date.now(), text, done: false });
      inp.value = "";
      renderCustomTasks();
      await saveProgress();
    };
    safeAddEvent("btnAddCustomTask", "click", addCustomTask);
    safeAddEvent("customTaskInput", "keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addCustomTask();
      }
    });

    safeAddEvent("btnPdfClose", "click", closePdfReader);
    safeAddEvent("btnPdfBookmark", "click", () => {
      if (state.pdfDocId) toggleBookmark(state.pdfDocId);
    });
    safeAddEvent("btnPdfSendChat", "click", (e) => {
      if (state.pdfDocId) sendFileToTelegram(state.pdfDocId, e.currentTarget);
    });
    safeAddEvent("btnPdfPrev", "click", () => {
      if (state.pdfPage > 1) {
        state.pdfPage--;
        renderMainPdfPage();
      }
    });
    safeAddEvent("btnPdfNext", "click", () => {
      if (state.pdfPage < state.pdfTotalPages) {
        state.pdfPage++;
        renderMainPdfPage();
      }
    });
    safeAddEvent("pdfPageInput", "change", (e) => {
      const p = parseInt(e.target.value, 10);
      if (!isNaN(p)) {
        state.pdfPage = Math.max(1, Math.min(p, state.pdfTotalPages));
        renderMainPdfPage();
      }
    });
    safeAddEvent("btnPdfZoomOut", "click", () => {
      state.pdfScale = Math.max(0.65, Number((state.pdfScale - 0.15).toFixed(2)));
      renderMainPdfPage();
    });
    safeAddEvent("btnPdfZoomIn", "click", () => {
      state.pdfScale = Math.min(2.35, Number((state.pdfScale + 0.15).toFixed(2)));
      renderMainPdfPage();
    });

    safeAddEvent("btnQuizClose", "click", closeQuizRunner);
    document.querySelectorAll(".quiz-subtab").forEach((btn) => {
      btn.addEventListener("click", () => setQuizPane(btn.dataset.pane));
    });
    safeAddEvent("btnQuizPdfPrev", "click", () => {
      if (state.quizPdfPage > 1) {
        state.quizPdfPage--;
        renderQuizPdfPage();
      }
    });
    safeAddEvent("btnQuizPdfNext", "click", () => {
      if (state.quizPdfPage < state.quizPdfTotal) {
        state.quizPdfPage++;
        renderQuizPdfPage();
      }
    });
    safeAddEvent("btnQuizPdfZoomOut", "click", () => {
      state.quizPdfScale = Math.max(0.65, Number((state.quizPdfScale - 0.15).toFixed(2)));
      renderQuizPdfPage();
    });
    safeAddEvent("btnQuizPdfZoomIn", "click", () => {
      state.quizPdfScale = Math.min(2.2, Number((state.quizPdfScale + 0.15).toFixed(2)));
      renderQuizPdfPage();
    });
    safeAddEvent("btnQuizSubmit", "click", submitQuizAnswers);
  }

  try {
    wireGlobalEvents();
    authenticate();
  } catch (err) {
    showBootError(err.message || String(err));
  }
})();
