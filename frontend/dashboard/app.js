/* ═══════════════════════════════════════════════════════════════════════════
   OrchestrAI — Career Intelligence Dashboard
   Main Application JavaScript
   ═══════════════════════════════════════════════════════════════════════════ */

// ── Global State ──────────────────────────────────────────────────────────
let dashboardData = null;
let allJobs = [];

const API_URL = "/api/dashboard";

// ── DOM Ready ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initFilters();
  fetchDashboardData();
});

// ══════════════════════════════════════════════════════════════════════════
// DATA FETCHING
// ══════════════════════════════════════════════════════════════════════════

async function fetchDashboardData() {
  showLoader();
  try {
    const resp = await fetch(API_URL);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    dashboardData = await resp.json();
    renderAll(dashboardData);
  } catch (err) {
    console.error("Failed to fetch dashboard data:", err);
    // Attempt local fallback for static hosting
    try {
      const localResp = await fetch("/database/jobs.yaml");
      if (localResp.ok) {
        console.warn("Using minimal fallback data");
      }
    } catch (_) { /* ignore */ }
    renderEmptyState();
  } finally {
    hideLoader();
  }
}

function showLoader() { document.getElementById("loader").classList.remove("hidden"); }
function hideLoader() { document.getElementById("loader").classList.add("hidden"); }

// ══════════════════════════════════════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════════════════════════════════════

function initNavigation() {
  const navLinks = document.querySelectorAll(".nav-link");
  const sections = document.querySelectorAll(".section");

  navLinks.forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = link.dataset.section;

      // Update active nav link
      navLinks.forEach(l => l.classList.remove("active"));
      link.classList.add("active");

      // Show target section
      sections.forEach(s => s.classList.remove("active"));
      const target = document.getElementById(targetId);
      if (target) {
        target.classList.add("active");
        // Re-trigger animations
        target.style.animation = "none";
        target.offsetHeight; // force reflow
        target.style.animation = "";
      }

      // Close mobile menu
      document.querySelector(".nav-links").classList.remove("open");
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });

  // Mobile menu toggle
  const mobileMenuBtn = document.getElementById("mobileMenuBtn");
  mobileMenuBtn?.addEventListener("click", () => {
    document.querySelector(".nav-links").classList.toggle("open");
  });

  // Refresh button
  document.getElementById("refreshBtn")?.addEventListener("click", () => {
    const btn = document.getElementById("refreshBtn");
    btn.classList.add("spinning");
    fetchDashboardData().finally(() => {
      setTimeout(() => btn.classList.remove("spinning"), 600);
    });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// RENDER ALL
// ══════════════════════════════════════════════════════════════════════════

function renderAll(data) {
  renderReadinessScore(data.readiness);
  renderQuickStats(data);
  renderInternships(data);
  renderStrategy(data.strategy);
  renderSecurity(data.security_reports);
  renderInterviews(data.interviews, data.jobs);
}

function renderEmptyState() {
  const grid = document.getElementById("internshipGrid");
  if (grid) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon">📡</div>
        <p class="empty-state-text">Unable to connect to the OrchestrAI backend.<br/>Please ensure the server is running and refresh.</p>
      </div>`;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 1 — CAREER READINESS
// ══════════════════════════════════════════════════════════════════════════

function renderReadinessScore(readiness) {
  if (!readiness) return;

  const score = readiness.readiness_score || 0;
  const label = readiness.label || "";
  const components = readiness.components || {};

  // Animate main score ring
  const circumference = 2 * Math.PI * 85; // r=85
  const offset = circumference - (score / 100) * circumference;
  const ring = document.getElementById("scoreRingFill");
  if (ring) {
    ring.style.strokeDasharray = circumference;
    ring.style.strokeDashoffset = circumference;
    setTimeout(() => { ring.style.strokeDashoffset = offset; }, 300);
  }

  // Animate score number
  animateCounter("scoreNumber", score, 2000);

  // Set label
  const labelEl = document.getElementById("scoreLabel");
  if (labelEl) {
    labelEl.textContent = label;
    const cls = score >= 85 ? "strong" : score >= 70 ? "good" : score >= 50 ? "developing" : "needs-work";
    labelEl.className = "score-label " + cls;
  }

  // Sub-scores
  const subScores = {
    skill: components.skill_coverage?.score || 0,
    portfolio: components.portfolio_strength?.score || 0,
    practice: components.interview_practice?.score || 0,
    security: components.security_health?.score || 0,
  };

  const subCircumference = 2 * Math.PI * 50; // r=50
  Object.entries(subScores).forEach(([key, val]) => {
    const card = document.querySelector(`.sub-score-card[data-score="${key}"]`);
    if (!card) return;
    const fill = card.querySelector(".sub-ring-fill");
    if (fill) {
      fill.style.strokeDasharray = subCircumference;
      fill.style.strokeDashoffset = subCircumference;
      const subOffset = subCircumference - (val / 100) * subCircumference;
      setTimeout(() => { fill.style.strokeDashoffset = subOffset; }, 500);
    }

    const ids = { skill: "skillScore", portfolio: "portfolioScore", practice: "practiceScore", security: "securityScore" };
    animateCounter(ids[key], Math.round(val), 1800);
  });
}

function animateCounter(elementId, target, duration) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const start = performance.now();
  const startVal = 0;

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const ease = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(startVal + (target - startVal) * ease);
    el.textContent = Number.isInteger(target) ? current : current.toFixed(1);
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

function renderQuickStats(data) {
  const jobs = data.jobs || [];
  const secReports = data.security_reports || [];
  const scores = data.scores || [];

  document.getElementById("totalJobs").textContent = jobs.length;
  document.getElementById("totalRepos").textContent = secReports.length;

  const highMatch = scores.filter(s => (s.match_score || 0) >= 70).length;
  document.getElementById("highMatchCount").textContent = highMatch;

  const safe = secReports.filter(r => (r.risk_level || "").toLowerCase() === "safe").length;
  document.getElementById("safeRepos").textContent = safe;
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 2 — INTERNSHIPS
// ══════════════════════════════════════════════════════════════════════════

function renderInternships(data) {
  const jobs = data.jobs || [];
  const skillAnalysis = data.skill_analysis || [];
  const coverLetters = data.cover_letters || [];
  const optimizations = data.optimizations || [];
  const scores = data.scores || [];
  const practice = data.practice || [];
  const interviews = data.interviews || [];
  const perInternship = data.per_internship_portfolios || [];

  // Build lookup maps
  const skillLookup = buildLookup(skillAnalysis);
  const clLookup = buildLookup(coverLetters, "link");
  const optLookup = buildLookup(optimizations, "optimized_resume_link");
  const scoreLookup = buildLookup(scores);
  const practiceLookup = buildLookup(practice, "practice_link");
  const interviewLookup = buildLookup(interviews, "interview_link");
  const pipLookup = buildLookup(perInternship, "link");

  // Enrich jobs with additional data
  allJobs = jobs.map(job => {
    const key = `${job.company || ""}|${job.role || ""}`;
    const analysis = skillLookup[key] || {};
    const scoreData = scoreLookup[key] || {};

    return {
      ...job,
      missing_skills: analysis.missing_skills || [],
      roadmap: analysis.roadmap || [],
      match_score: scoreData.match_score || 0,
      selection_probability: scoreData.selection_probability || "Unknown",
      priority: scoreData.priority || "Unknown",
      cover_letter_link: clLookup[key] || "",
      resume_link: optLookup[key] || "",
      practice_link: practiceLookup[key] || "",
      interview_link: interviewLookup[key] || "",
      portfolio_link: pipLookup[key] || "",
    };
  });

  renderInternshipCards(allJobs);
}

function buildLookup(list, valueKey) {
  const map = {};
  for (const item of list) {
    if (!item || typeof item !== "object") continue;
    const key = `${item.company || ""}|${item.role || ""}`;
    map[key] = valueKey ? (item[valueKey] || "") : item;
  }
  return map;
}

function renderInternshipCards(jobs) {
  const grid = document.getElementById("internshipGrid");
  if (!grid) return;

  if (jobs.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon">🔍</div>
        <p class="empty-state-text">No internships match your current filters.<br/>Try adjusting the filters above.</p>
      </div>`;
    document.getElementById("resultsCount").textContent = "0 opportunities";
    return;
  }

  document.getElementById("resultsCount").textContent = `${jobs.length} opportunities`;

  grid.innerHTML = jobs.map((job, i) => {
    const scoreClass = job.match_score >= 70 ? "high" : job.match_score >= 40 ? "medium" : "low";
    const probClass = (job.selection_probability || "").toLowerCase().includes("high") ? "prob-high" :
      (job.selection_probability || "").toLowerCase().includes("medium") ? "prob-medium" : "prob-low";

    const skillTags = (job.technical_skills || []).slice(0, 6).map(s =>
      `<span class="skill-tag">${escapeHtml(s)}</span>`
    ).join("");

    const gapHtml = job.missing_skills.length > 0
      ? `<div class="intern-gap">⚠️ Gap: ${job.missing_skills.slice(0, 4).map(s => escapeHtml(s)).join(", ")}${job.missing_skills.length > 4 ? ` +${job.missing_skills.length - 4} more` : ""}</div>`
      : `<div class="intern-gap no-gap">✓ All skills covered — you're well-equipped!</div>`;

    // Roadmap section (expandable)
    let roadmapHtml = "";
    if (job.roadmap && job.roadmap.length > 0) {
      const steps = job.roadmap.slice(0, 5).map(s => `<li>${escapeHtml(String(s))}</li>`).join("");
      roadmapHtml = `
        <details class="intern-roadmap">
          <summary>📚 Learning Roadmap (${job.roadmap.length} steps)</summary>
          <ul>${steps}</ul>
        </details>`;
    }

    // Strip tracking parameters which often cause ERR_CONNECTION_RESET
    let cleanApplyLink = job.apply_link;
    if (cleanApplyLink && cleanApplyLink.includes("linkedin.com/jobs/view/")) {
      cleanApplyLink = cleanApplyLink.split("?")[0];
    }

    // Always show all action buttons — disabled state for missing links
    const applyBtn = cleanApplyLink
      ? `<a href="${cleanApplyLink}" target="_blank" class="btn-action btn-apply">Apply →</a>`
      : `<span class="btn-action btn-disabled">Apply →</span>`;

    const clBtn = job.cover_letter_link
      ? `<a href="${job.cover_letter_link}" target="_blank" class="btn-action btn-secondary">📄 Cover Letter</a>`
      : `<span class="btn-action btn-disabled">📄 Cover Letter</span>`;

    const resumeBtn = job.resume_link
      ? `<a href="${job.resume_link}" target="_blank" class="btn-action btn-secondary">📋 Resume</a>`
      : `<span class="btn-action btn-disabled">📋 Resume</span>`;

    const portfolioBtn = job.portfolio_link
      ? `<a href="${job.portfolio_link}" target="_blank" class="btn-action btn-secondary">🎯 Portfolio</a>`
      : `<span class="btn-action btn-disabled">🎯 Portfolio</span>`;

    const interviewBtn = job.interview_link
      ? `<a href="${job.interview_link}" target="_blank" class="btn-action btn-secondary">🎤 Interview</a>`
      : `<span class="btn-action btn-disabled">🎤 Interview</span>`;

    return `
      <div class="intern-card" style="animation-delay:${i * 0.06}s">
        <div class="intern-card-header">
          <div>
            <div class="intern-company">${escapeHtml(job.company || "Unknown")}</div>
            <div class="intern-role">${escapeHtml(job.role || "")}</div>
          </div>
          <div class="intern-score-badge ${scoreClass}">${job.match_score}</div>
        </div>
        <div class="intern-meta">
          <span class="intern-meta-item">📍 ${escapeHtml(job.location || "Remote")}</span>
          <span class="intern-meta-item">🏷️ ${escapeHtml(job.source || "")}</span>
        </div>
        <div class="intern-skills">${skillTags}</div>
        <div class="intern-probability ${probClass}">
          ${job.selection_probability} Probability · ${job.priority}
        </div>
        ${gapHtml}
        ${roadmapHtml}
        <div class="intern-actions">
          ${applyBtn}
          ${clBtn}
          ${resumeBtn}
          ${portfolioBtn}
          ${interviewBtn}
        </div>
      </div>`;
  }).join("");
}

// ══════════════════════════════════════════════════════════════════════════
// FILTERS
// ══════════════════════════════════════════════════════════════════════════

function initFilters() {
  const filterPlatform = document.getElementById("filterPlatform");
  const filterRole = document.getElementById("filterRole");
  const filterScore = document.getElementById("filterScore");
  const filterLocation = document.getElementById("filterLocation");
  const clearBtn = document.getElementById("clearFilters");
  const scoreLabel = document.getElementById("scoreSliderVal");

  const applyFilters = () => {
    const platform = filterPlatform.value;
    const role = filterRole.value;
    const minScore = parseInt(filterScore.value, 10);
    const location = filterLocation.value;

    scoreLabel.textContent = minScore;

    let filtered = allJobs.filter(job => {
      if (platform !== "all" && !(job.source || "").toLowerCase().includes(platform.toLowerCase())) return false;
      if (role !== "all" && !(job.role || "").toLowerCase().includes(role.toLowerCase())) return false;
      if (job.match_score < minScore) return false;
      if (location !== "all") {
        const loc = (job.location || "").toLowerCase();
        if (location === "Remote" && !loc.includes("remote")) return false;
        if (location === "On-site" && loc.includes("remote")) return false;
      }
      return true;
    });

    renderInternshipCards(filtered);
  };

  filterPlatform?.addEventListener("change", applyFilters);
  filterRole?.addEventListener("change", applyFilters);
  filterScore?.addEventListener("input", applyFilters);
  filterLocation?.addEventListener("change", applyFilters);

  clearBtn?.addEventListener("click", () => {
    filterPlatform.value = "all";
    filterRole.value = "all";
    filterScore.value = 0;
    filterLocation.value = "all";
    scoreLabel.textContent = "0";
    renderInternshipCards(allJobs);
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 3 — CAREER STRATEGY
// ══════════════════════════════════════════════════════════════════════════

function renderStrategy(strategy) {
  if (!strategy || typeof strategy !== "object") return;

  // Goal
  const goalText = document.getElementById("goalText");
  if (goalText) goalText.textContent = strategy.goal || "Building your career path...";

  const analysis = strategy.analysis || {};

  // Skill gap badges
  const skillGapBadges = document.getElementById("skillGapBadges");
  const topSkills = analysis.top_missing_skills || [];
  if (skillGapBadges) {
    skillGapBadges.innerHTML = topSkills.length > 0
      ? topSkills.map(s => `<span class="gap-badge">${escapeHtml(s)}</span>`).join("")
      : `<span style="color:var(--success)">✓ No critical skill gaps identified</span>`;
  }

  // Portfolio & Practice status
  const portfolioStatus = document.getElementById("portfolioStatus");
  if (portfolioStatus) portfolioStatus.textContent = analysis.portfolio_strength || "Not assessed";

  const practiceStatus = document.getElementById("practiceStatus");
  if (practiceStatus) practiceStatus.textContent = analysis.practice_status || "Not assessed";

  // Top opportunities
  const topOpps = document.getElementById("topOpportunities");
  const opps = analysis.top_opportunities || [];
  if (topOpps) {
    topOpps.innerHTML = opps.length > 0
      ? opps.map(o => `<li class="opp-item">${escapeHtml(o)}</li>`).join("")
      : `<li class="opp-item">Run the pipeline to identify top matches</li>`;
  }

  // Action plan
  const actionPlan = document.getElementById("actionPlan");
  const actions = strategy.actions || [];
  if (actionPlan) {
    actionPlan.innerHTML = actions.length > 0
      ? actions.map((a, i) => `
          <div class="action-step">
            <span class="step-number">${i + 1}</span>
            <span class="step-text">${escapeHtml(a)}</span>
          </div>`).join("")
      : `<div class="action-step"><span class="step-number">1</span><span class="step-text">Keep building projects and practicing interviews!</span></div>`;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 4 — SECURITY
// ══════════════════════════════════════════════════════════════════════════

function renderSecurity(reports) {
  if (!Array.isArray(reports)) reports = [];

  // Overview stats
  const total = reports.length;
  const high = reports.filter(r => (r.risk_level || "").toLowerCase() === "high").length;
  const med = reports.filter(r => (r.risk_level || "").toLowerCase() === "medium").length;
  const safe = reports.filter(r => ["safe", "low"].includes((r.risk_level || "").toLowerCase())).length;

  document.getElementById("secTotalRepos").textContent = total;
  document.getElementById("secHighCount").textContent = high;
  document.getElementById("secMedCount").textContent = med;
  document.getElementById("secSafeCount").textContent = safe;

  // Sort: High first, then Medium, then Low, then Safe
  const riskOrder = { high: 0, medium: 1, low: 2, safe: 3 };
  const sorted = [...reports].sort((a, b) => {
    const aLevel = (a.risk_level || "safe").toLowerCase();
    const bLevel = (b.risk_level || "safe").toLowerCase();
    return (riskOrder[aLevel] ?? 4) - (riskOrder[bLevel] ?? 4);
  });

  const grid = document.getElementById("securityGrid");
  if (!grid) return;

  if (sorted.length === 0) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-state-icon">🔒</div><p class="empty-state-text">No security scans performed yet.</p></div>`;
    return;
  }

  grid.innerHTML = sorted.map(report => {
    const risk = (report.risk_level || "Safe").toLowerCase();
    const riskLabel = risk.charAt(0).toUpperCase() + risk.slice(1);
    const issues = report.issues || [];
    const topIssue = issues.length > 0 ? String(issues[0]).slice(0, 120) : "No issues found.";
    const prUrl = report.auto_fix_pr || "";
    const repoUrl = report.repo_url || `https://github.com/${report.repo || ""}`;
    const vulns = report.total_vulnerabilities || 0;
    const files = report.scanned_files || 0;

    return `
      <div class="sec-card">
        <div class="sec-card-header">
          <a href="${repoUrl}" target="_blank" class="sec-repo-name">${escapeHtml(report.repo || "Unknown")}</a>
          <span class="sec-risk-badge ${risk}">${riskLabel}</span>
        </div>
        <div class="sec-stats-row">
          <span>🐛 ${vulns} vulnerabilities</span>
          <span>📂 ${files} files scanned</span>
        </div>
        <div class="sec-issue">${escapeHtml(topIssue)}</div>
        <div class="sec-card-actions">
          <a href="${repoUrl}" target="_blank" class="btn-action btn-secondary">View Repo</a>
          ${(risk === "high" || risk === "medium") ? `<a href="${prUrl || (repoUrl + '/pulls')}" target="_blank" class="btn-action btn-apply">${prUrl ? 'View Fix PR →' : 'View Fixes →'}</a>` : ""}
        </div>
      </div>`;
  }).join("");
}

// ══════════════════════════════════════════════════════════════════════════
// SECTION 5 — MOCK INTERVIEWS
// ══════════════════════════════════════════════════════════════════════════

function renderInterviews(interviews, jobs) {
  const grid = document.getElementById("interviewGrid");
  if (!grid) return;

  // Combine interview data with job info
  let interviewCards = [];

  if (Array.isArray(interviews) && interviews.length > 0) {
    interviewCards = interviews;
  } else if (Array.isArray(jobs)) {
    // Fallback: create cards from jobs that have interview links
    interviewCards = allJobs.filter(j => j.interview_link).map(j => ({
      company: j.company,
      role: j.role,
      interview_link: j.interview_link,
    }));
  }

  if (interviewCards.length === 0) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-state-icon">🎤</div><p class="empty-state-text">No mock interviews available yet.<br/>They'll be generated in the next pipeline run.</p></div>`;
    return;
  }

  grid.innerHTML = interviewCards.map(item => {
    const link = item.interview_link || item.practice_link || "#";
    return `
      <div class="interview-card">
        <span class="interview-emoji">🎤</span>
        <div class="interview-company">${escapeHtml(item.company || "Company")}</div>
        <div class="interview-role">${escapeHtml(item.role || "Role")}</div>
        <a href="${link}" target="_blank" class="btn-interview">
          Start Mock Interview →
        </a>
      </div>`;
  }).join("");
}

// ══════════════════════════════════════════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════════════════════════════════════════

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
