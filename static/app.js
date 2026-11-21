// Helper to prevent the app from crashing if an ID is missing in HTML
  function safeAddEvent(id, event, callback) {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener(event, callback);
    } else {
      console.warn(`Warning: Element ID #${id} not found in HTML. Skipping listener.`);
    }
  }

  function wireGlobalEvents() {
    // Language switching
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

    // Legal modals
    safeAddEvent("btnOpenTermsReg", "click", () => openLegalModal("terms"));
    safeAddEvent("btnOpenPrivacyReg", "click", () => openLegalModal("privacy"));
    safeAddEvent("btnOpenTermsFooter", "click", () => openLegalModal("terms"));
    safeAddEvent("btnOpenPrivacyFooter", "click", () => openLegalModal("privacy"));
    safeAddEvent("btnLegalClose", "click", () => {
      document.getElementById("modalLegal").classList.add("hidden");
    });
    
    const legalModal = document.getElementById("modalLegal");
    if (legalModal) {
      legalModal.addEventListener("click", (e) => {
        if (e.target.id === "modalLegal") document.getElementById("modalLegal").classList.add("hidden");
      });
    }

    // Library filters & material request
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
      const subject = document.getElementById("reqSubject")?.value.trim() || "";
      const details = document.getElementById("reqDetails")?.value.trim() || "";
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

    // Study plan custom tasks
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

    // PDF Modal controls
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

    // Quiz Modal controls
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
