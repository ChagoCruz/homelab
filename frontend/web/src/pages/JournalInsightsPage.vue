<template>
  <main class="screen">
    <header class="header">
      <div>
        <h1 class="title">JOURNAL INSIGHTS</h1>
        <p class="subtitle">Monthly + weekly pattern profiles and daily entry insights</p>
      </div>

      <div class="actions">
        <button class="btn" type="button" :disabled="isGeneratingMonthly" @click="generateMonthly">
          {{ isGeneratingMonthly ? "GENERATING..." : "GENERATE MONTHLY" }}
        </button>
        <button class="btn" type="button" :disabled="isGeneratingWeekly" @click="generateWeekly">
          {{ isGeneratingWeekly ? "GENERATING..." : "GENERATE WEEKLY" }}
        </button>
        <button class="btn" type="button" @click="goBack">
          BACK
        </button>
      </div>
    </header>

    <section class="panel">
      <div class="meta-row">
        <span v-if="status" class="status">{{ status }}</span>
        <span v-if="isLoadingMonthlyProfiles">LOADING MONTHLY PROFILES...</span>
        <span v-if="isLoadingMonthlySummaries">LOADING MONTHLY SUMMARIES...</span>
        <span v-if="isLoadingWeeklyProfiles">LOADING WEEKLY PROFILES...</span>
        <span v-if="isLoadingWeeklySummaries">LOADING WEEKLY SUMMARIES...</span>
        <span v-if="isLoadingDailyInsights">LOADING DAILY INSIGHTS...</span>
      </div>

      <p v-if="weeklyError" class="error-text">{{ weeklyError }}</p>
      <p v-if="dailyError" class="error-text">{{ dailyError }}</p>

      <button class="accordion-toggle top-level" type="button" @click="toggleMonthlyRoot">
        <span class="summary-arrow" :class="{ open: monthlyRootOpen }">▶</span>
        <span>MONTHLY</span>
        <span class="section-count">{{ monthlyStacks.length }}</span>
      </button>

      <transition name="expand">
        <div v-if="monthlyRootOpen" class="accordion-body">
          <p
            v-if="!isLoadingMonthlyProfiles && !isLoadingMonthlySummaries && monthlyStacks.length === 0"
            class="empty-text"
          >
            No monthly profiles yet.
          </p>

          <div v-else class="accordion-tree">
            <article
              v-for="month in monthlyStacks"
              :key="month.key"
              class="profile-card"
            >
              <button
                class="accordion-toggle profile-toggle"
                type="button"
                @click="toggleMonth(month.key)"
              >
                <span
                  class="summary-arrow"
                  :class="{ open: isMonthOpen(month.key) }"
                >
                  ▶
                </span>
                <span>
                  {{ formatRange(month.period_start, month.period_end) }}
                </span>
                <span class="section-count">
                  {{ monthlyStackBadge(month) }}
                </span>
              </button>

              <transition name="expand">
                <div v-if="isMonthOpen(month.key)" class="profile-body">
                  <section v-if="month.summary" class="profile-section">
                    <h3 class="stack-block-title">[ SUMMARY ]</h3>
                    <p class="profile-paragraph">{{ monthlySummaryText(month) }}</p>
                  </section>

                  <section
                    v-if="monthlySummaryThemes(month).length"
                    class="profile-section"
                  >
                    <h3 class="stack-block-title">[ THEMES ]</h3>
                    <ul class="profile-list">
                      <li v-for="(item, idx) in monthlySummaryThemes(month)" :key="idx">
                        {{ item }}
                      </li>
                    </ul>
                  </section>

                  <div v-if="month.summary && month.profile" class="stack-divider"></div>

                  <section v-if="month.profile" class="profile-section">
                    <h3 class="stack-block-title">[ PATTERN ANALYSIS ]</h3>
                    <p class="stack-kv" v-if="month.profile.dominant_emotions?.length">
                      dominant_emotions: {{ joinList(month.profile.dominant_emotions) }}
                    </p>
                    <p class="stack-kv" v-if="month.profile.recurring_stressors?.length">
                      stressors: {{ joinList(month.profile.recurring_stressors) }}
                    </p>
                    <p class="stack-kv" v-if="month.profile.motivation_drivers?.length">
                      motivation_drivers: {{ joinList(month.profile.motivation_drivers) }}
                    </p>
                    <p class="stack-quote" v-if="month.profile.pattern_summary">
                      > {{ month.profile.pattern_summary }}
                    </p>
                  </section>
                </div>
              </transition>
            </article>
          </div>
        </div>
      </transition>

      <button class="accordion-toggle top-level" type="button" @click="toggleWeeklyRoot">
        <span class="summary-arrow" :class="{ open: weeklyRootOpen }">▶</span>
        <span>WEEKLY</span>
        <span class="section-count">{{ weeklyStacks.length }}</span>
      </button>

      <transition name="expand">
        <div v-if="weeklyRootOpen" class="accordion-body">
          <p
            v-if="!isLoadingWeeklyProfiles && !isLoadingWeeklySummaries && weeklyStacks.length === 0"
            class="empty-text"
          >
            No weekly profiles yet.
          </p>

          <div v-else class="accordion-tree">
            <article
              v-for="week in weeklyStacks"
              :key="week.key"
              class="profile-card"
            >
              <button
                class="accordion-toggle profile-toggle"
                type="button"
                @click="toggleProfile(week.key)"
              >
                <span
                  class="summary-arrow"
                  :class="{ open: isProfileOpen(week.key) }"
                >
                  ▶
                </span>
                <span>
                  {{ formatRange(week.period_start, week.period_end) }}
                </span>
                <span class="section-count">
                  {{ weeklyStackBadge(week) }}
                </span>
              </button>

              <transition name="expand">
                <div v-if="isProfileOpen(week.key)" class="profile-body">
                  <section
                    v-if="week.summary && weeklySystemState(week)"
                    class="profile-section"
                  >
                    <h3 class="stack-block-title">[ SYSTEM_STATE ]</h3>
                    <p class="profile-paragraph">{{ weeklySystemState(week) }}</p>
                  </section>

                  <section
                    v-if="weeklyTopDrivers(week).length"
                    class="profile-section"
                  >
                    <h3 class="stack-block-title">[ TOP_DRIVERS ]</h3>
                    <ul class="profile-list">
                      <li v-for="(item, idx) in weeklyTopDrivers(week)" :key="idx">
                        <p class="stack-kv">driver: {{ item.driver || "—" }}</p>
                        <p class="stack-kv" v-if="item.evidence">evidence: {{ item.evidence }}</p>
                      </li>
                    </ul>
                  </section>

                  <section
                    v-if="weeklyCorrelations(week).length"
                    class="profile-section"
                  >
                    <h3 class="stack-block-title">[ CORRELATIONS ]</h3>
                    <ul class="profile-list">
                      <li v-for="(item, idx) in weeklyCorrelations(week)" :key="idx">
                        <p class="stack-kv">correlation: {{ item.correlation || "—" }}</p>
                        <p class="stack-kv" v-if="item.strength">strength: {{ item.strength }}</p>
                        <p class="stack-kv" v-if="item.interpretation">
                          interpretation: {{ item.interpretation }}
                        </p>
                      </li>
                    </ul>
                  </section>

                  <section
                    v-if="weeklyPatterns(week).length"
                    class="profile-section"
                  >
                    <h3 class="stack-block-title">[ PATTERNS ]</h3>
                    <ul class="profile-list">
                      <li v-for="(item, idx) in weeklyPatterns(week)" :key="idx">
                        {{ item }}
                      </li>
                    </ul>
                  </section>

                  <section
                    v-if="weeklyRiskFlags(week).length"
                    class="profile-section"
                  >
                    <h3 class="stack-block-title">[ RISK_FLAGS ]</h3>
                    <ul class="profile-list">
                      <li v-for="(item, idx) in weeklyRiskFlags(week)" :key="idx">
                        {{ item }}
                      </li>
                    </ul>
                  </section>

                  <section
                    v-if="weeklyRecommendations(week).length"
                    class="profile-section"
                  >
                    <h3 class="stack-block-title">[ RECOMMENDATIONS ]</h3>
                    <ul class="profile-list">
                      <li v-for="(item, idx) in weeklyRecommendations(week)" :key="idx">
                        {{ item }}
                      </li>
                    </ul>
                  </section>

                  <section
                    v-if="!weeklyHasBehavioralSections(week) && week.summary && weeklySummaryText(week)"
                    class="profile-section"
                  >
                    <h3 class="stack-block-title">[ SUMMARY ]</h3>
                    <p class="profile-paragraph">{{ weeklySummaryText(week) }}</p>
                  </section>

                  <section
                    v-if="!weeklyHasBehavioralSections(week) && weeklySummaryThemes(week).length"
                    class="profile-section"
                  >
                    <h3 class="stack-block-title">[ THEMES ]</h3>
                    <ul class="profile-list">
                      <li v-for="(item, idx) in weeklySummaryThemes(week)" :key="idx">
                        {{ item }}
                      </li>
                    </ul>
                  </section>

                  <div v-if="week.summary && week.profile" class="stack-divider"></div>

                  <section v-if="week.profile" class="profile-section">
                    <h3 class="stack-block-title">[ PATTERN ANALYSIS ]</h3>
                    <p class="stack-kv" v-if="week.profile.dominant_emotions?.length">
                      dominant_emotions: {{ joinList(week.profile.dominant_emotions) }}
                    </p>
                    <p class="stack-kv" v-if="week.profile.recurring_stressors?.length">
                      stressors: {{ joinList(week.profile.recurring_stressors) }}
                    </p>
                    <p class="stack-kv" v-if="week.profile.motivation_drivers?.length">
                      motivation_drivers: {{ joinList(week.profile.motivation_drivers) }}
                    </p>
                    <p class="stack-quote" v-if="week.profile.pattern_summary">
                      > {{ week.profile.pattern_summary }}
                    </p>
                  </section>
                </div>
              </transition>
            </article>
          </div>
        </div>
      </transition>

      <button class="accordion-toggle top-level" type="button" @click="toggleDailyRoot">
        <span class="summary-arrow" :class="{ open: dailyRootOpen }">▶</span>
        <span>DAILY INSIGHTS</span>
        <span class="section-count">{{ groupedDailyInsights.length }}</span>
      </button>

      <transition name="expand">
        <div v-if="dailyRootOpen" class="accordion-body">
          <p v-if="!isLoadingDailyInsights && groupedDailyInsights.length === 0" class="empty-text">
            No daily insights yet.
          </p>

          <div v-else class="accordion-tree">
            <section
              v-for="dayGroup in groupedDailyInsights"
              :key="dayGroup.date"
              class="tree-group"
            >
              <button class="accordion-toggle" type="button" @click="toggleDay(dayGroup.date)">
                <span class="summary-arrow" :class="{ open: isDayOpen(dayGroup.date) }">▶</span>
                <span>{{ formatDay(dayGroup.date) }}</span>
                <span class="section-count">{{ dayGroup.count }} ENTRIES</span>
              </button>

              <transition name="expand">
                <div v-if="isDayOpen(dayGroup.date)" class="accordion-body nested">
                  <article
                    v-for="entry in dayGroup.items"
                    :key="entry.id"
                    class="profile-card"
                  >
                    <div class="daily-entry-meta">
                      <span class="profile-stat-label">ENTRY #{{ entry.id }}</span>
                      <span class="daily-entry-time">{{ formatDateTime(entry.created_at) }}</span>
                    </div>

                    <button class="entry-toggle" type="button" @click="toggleEntry(entry.id)">
                      <span class="summary-arrow" :class="{ open: isEntryOpen(entry.id) }">▶</span>
                      <span class="entry-toggle-text">
                        {{ isEntryOpen(entry.id) ? "HIDE ENTRY" : "READ ENTRY" }}
                      </span>
                    </button>

                    <transition name="expand">
                      <section v-if="isEntryOpen(entry.id)" class="profile-section">
                        <h3 class="profile-section-title">ENTRY</h3>
                        <p class="profile-paragraph">{{ entry.content }}</p>
                      </section>
                    </transition>

                    <p v-if="entry.analysisError" class="error-text">{{ entry.analysisError }}</p>
                    <p v-else-if="!entry.analysis" class="empty-text">No insight for this entry yet.</p>

                    <template v-else>
                      <div class="profile-stats">
                        <div class="profile-stat">
                          <span class="profile-stat-label">MOOD</span>
                          <span class="profile-stat-value">
                            {{ formatMood(entry.analysis.mood_score) }}
                          </span>
                        </div>

                        <div class="profile-stat">
                          <span class="profile-stat-label">TONE</span>
                          <span class="profile-stat-value">
                            {{ entry.analysis.emotional_tone || "—" }}
                          </span>
                        </div>
                      </div>

                      <section v-if="entry.analysis.insight" class="profile-section">
                        <h3 class="profile-section-title">INSIGHT</h3>
                        <p class="profile-paragraph">{{ entry.analysis.insight }}</p>
                      </section>

                      <section
                        v-if="entry.analysis.reflection_questions?.length"
                        class="profile-section"
                      >
                        <h3 class="profile-section-title">REFLECTION QUESTIONS</h3>
                        <ul class="profile-list">
                          <li
                            v-for="(question, idx) in entry.analysis.reflection_questions"
                            :key="idx"
                          >
                            {{ question }}
                          </li>
                        </ul>
                      </section>

                      <section v-if="entry.analysis.stressors?.length" class="profile-section">
                        <h3 class="profile-section-title">STRESSORS</h3>
                        <ul class="profile-list">
                          <li v-for="(item, idx) in entry.analysis.stressors" :key="idx">
                            {{ item }}
                          </li>
                        </ul>
                      </section>

                      <section
                        v-if="entry.analysis.positive_signals?.length"
                        class="profile-section"
                      >
                        <h3 class="profile-section-title">POSITIVE SIGNALS</h3>
                        <ul class="profile-list">
                          <li v-for="(item, idx) in entry.analysis.positive_signals" :key="idx">
                            {{ item }}
                          </li>
                        </ul>
                      </section>

                      <section
                        v-if="entry.analysis.thinking_patterns?.length"
                        class="profile-section"
                      >
                        <h3 class="profile-section-title">THINKING PATTERNS</h3>
                        <ul class="profile-list">
                          <li v-for="(item, idx) in entry.analysis.thinking_patterns" :key="idx">
                            {{ item }}
                          </li>
                        </ul>
                      </section>

                      <section v-if="entry.analysis.encouragement" class="profile-section">
                        <h3 class="profile-section-title">ENCOURAGEMENT</h3>
                        <p class="profile-paragraph">{{ entry.analysis.encouragement }}</p>
                      </section>
                    </template>
                  </article>
                </div>
              </transition>
            </section>
          </div>
        </div>
      </transition>
    </section>

    <div class="scanlines" aria-hidden="true"></div>
    <div class="vignette" aria-hidden="true"></div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const configuredApiUrl = import.meta.env.VITE_API_URL;
const browserLocation = typeof window !== "undefined" ? window.location : null;
const browserHost = browserLocation?.hostname;
const browserOrigin = browserLocation?.origin;
const hostBasedCandidates = browserHost
  ? [
      `http://${browserHost}:8001`,
      `http://${browserHost}:8000`,
      `https://${browserHost}:8001`,
      `https://${browserHost}:8000`
    ]
  : [];
const apiBaseCandidates = [...new Set(
  [
    configuredApiUrl,
    browserOrigin,
    ...hostBasedCandidates,
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
  ].filter(Boolean)
)];
const activeApiBaseUrl = ref(apiBaseCandidates[0] ?? "http://localhost:8000");

const weeklyProfiles = ref([]);
const monthlyProfiles = ref([]);
const weeklySummaries = ref([]);
const monthlySummaries = ref([]);
const dailyInsights = ref([]);
const isLoadingWeeklyProfiles = ref(false);
const isLoadingMonthlyProfiles = ref(false);
const isLoadingWeeklySummaries = ref(false);
const isLoadingMonthlySummaries = ref(false);
const isLoadingDailyInsights = ref(false);
const isGeneratingWeekly = ref(false);
const isGeneratingMonthly = ref(false);
const status = ref("");
const weeklyError = ref("");
const dailyError = ref("");

const monthlyRootOpen = ref(false);
const weeklyRootOpen = ref(false);
const dailyRootOpen = ref(false);
const openProfiles = ref({});
const openMonths = ref({});
const openDays = ref({});
const expandedEntries = ref({});

function flash(msg) {
  status.value = msg;
  window.clearTimeout(flash._t);
  flash._t = window.setTimeout(() => (status.value = ""), 2200);
}

function isNetworkFetchError(error) {
  return error instanceof TypeError && /Failed to fetch/i.test(error.message || "");
}

function withApiHint(error) {
  if (isNetworkFetchError(error)) {
    const tried = apiBaseCandidates.join(", ");
    const hostHint = browserHost ? ` Browser host: ${browserHost}.` : "";
    return `Failed to reach API. Tried: ${tried}.${hostHint}`;
  }
  return error?.message || "Unknown error";
}

async function apiFetch(path, init) {
  let lastError = null;

  for (const base of apiBaseCandidates) {
    try {
      const res = await fetch(`${base}${path}`, init);
      activeApiBaseUrl.value = base;
      return res;
    } catch (error) {
      lastError = error;
      if (!isNetworkFetchError(error)) throw error;
    }
  }

  throw lastError || new Error("Failed to fetch");
}

async function readApiError(res) {
  const bodyText = await res.text().catch(() => "");
  if (!bodyText) return `HTTP ${res.status}`;

  try {
    const parsed = JSON.parse(bodyText);
    if (parsed && typeof parsed === "object" && typeof parsed.detail === "string") {
      return parsed.detail;
    }
  } catch (_) {
    // Non-JSON response body; return raw text below.
  }

  return bodyText;
}

function goBack() {
  router.push("/journal");
}

function toggleMonthlyRoot() {
  monthlyRootOpen.value = !monthlyRootOpen.value;
}

function toggleWeeklyRoot() {
  weeklyRootOpen.value = !weeklyRootOpen.value;
}

function toggleDailyRoot() {
  dailyRootOpen.value = !dailyRootOpen.value;
}

function toggleProfile(id) {
  openProfiles.value = {
    ...openProfiles.value,
    [id]: !openProfiles.value[id]
  };
}

function isProfileOpen(id) {
  return !!openProfiles.value[id];
}

function toggleMonth(id) {
  openMonths.value = {
    ...openMonths.value,
    [id]: !openMonths.value[id]
  };
}

function isMonthOpen(id) {
  return !!openMonths.value[id];
}

function toggleDay(day) {
  openDays.value = {
    ...openDays.value,
    [day]: !openDays.value[day]
  };
}

function isDayOpen(day) {
  return !!openDays.value[day];
}

function toggleEntry(id) {
  expandedEntries.value = {
    ...expandedEntries.value,
    [id]: !expandedEntries.value[id]
  };
}

function isEntryOpen(id) {
  return !!expandedEntries.value[id];
}

function parseCalendarDate(value) {
  if (typeof value === "string") {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
    if (match) {
      return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    }
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function entryTimestamp(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function formatDay(value) {
  const date = parseCalendarDate(value);
  if (!date) return value;
  return date
    .toLocaleDateString(undefined, {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric"
    })
    .toUpperCase();
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function formatMood(value) {
  if (value == null || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return num > 0 ? `+${num}` : `${num}`;
}

function formatRange(start, end) {
  const startDate = new Date(`${start}T00:00:00`);
  const endDate = new Date(`${end}T00:00:00`);

  const fmt = (d) =>
    d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric"
    }).toUpperCase();

  return `${fmt(startDate)} – ${fmt(endDate)}`;
}

function parseStructuredOutput(value) {
  if (!value) return {};
  if (typeof value === "object") return value;
  if (typeof value !== "string") return {};

  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (_) {
    return {};
  }
}

function joinList(items) {
  if (!Array.isArray(items)) return "";
  return items.filter(Boolean).join(", ");
}

function toStringList(items) {
  if (!Array.isArray(items)) return [];
  return items
    .map((item) => String(item ?? "").trim())
    .filter(Boolean);
}

function weeklyStructuredOutput(week) {
  if (!week?.summary) return {};
  return parseStructuredOutput(week.summary.structured_output);
}

function weeklyTopDrivers(week) {
  const structured = weeklyStructuredOutput(week);
  const drivers = Array.isArray(structured.top_drivers) ? structured.top_drivers : [];

  return drivers
    .filter((item) => item && typeof item === "object")
    .map((item) => ({
      driver: String(item.driver ?? "").trim(),
      evidence: String(item.evidence ?? "").trim()
    }))
    .filter((item) => item.driver || item.evidence);
}

function weeklyCorrelations(week) {
  const structured = weeklyStructuredOutput(week);
  const correlations = Array.isArray(structured.correlations) ? structured.correlations : [];

  return correlations
    .filter((item) => item && typeof item === "object")
    .map((item) => ({
      correlation: String(item.correlation ?? "").trim(),
      strength: String(item.strength ?? "").trim(),
      interpretation: String(item.interpretation ?? "").trim()
    }))
    .filter((item) => item.correlation || item.interpretation);
}

function weeklyPatterns(week) {
  const structured = weeklyStructuredOutput(week);
  return toStringList(structured.patterns);
}

function weeklyRiskFlags(week) {
  const structured = weeklyStructuredOutput(week);
  return toStringList(structured.risk_flags);
}

function weeklyRecommendations(week) {
  const structured = weeklyStructuredOutput(week);
  return toStringList(structured.recommendations);
}

function weeklyHasBehavioralSections(week) {
  return (
    weeklyTopDrivers(week).length > 0 ||
    weeklyCorrelations(week).length > 0 ||
    weeklyPatterns(week).length > 0 ||
    weeklyRiskFlags(week).length > 0 ||
    weeklyRecommendations(week).length > 0
  );
}

function weeklySystemState(week) {
  if (!week?.summary) return "";
  const structured = weeklyStructuredOutput(week);
  const systemState = typeof structured.system_state === "string" ? structured.system_state.trim() : "";
  if (systemState) return systemState;

  if (weeklyHasBehavioralSections(week)) {
    const summary = typeof structured.summary === "string" ? structured.summary.trim() : "";
    if (summary) return summary;
    return String(week.summary.insight_text ?? "").trim();
  }

  return "";
}

function weeklySummaryText(week) {
  if (!week?.summary) return "";
  const structured = weeklyStructuredOutput(week);
  if (typeof structured.summary === "string" && structured.summary.trim()) {
    return structured.summary.trim();
  }
  return String(week.summary.insight_text ?? "").trim();
}

function monthlySummaryText(month) {
  if (!month?.summary) return "";
  const structured = parseStructuredOutput(month.summary.structured_output);
  return structured.summary || month.summary.insight_text || "";
}

function weeklySummaryThemes(week) {
  if (!week?.summary) return [];
  const structured = weeklyStructuredOutput(week);
  return toStringList(structured.themes);
}

function monthlySummaryThemes(month) {
  if (!month?.summary) return [];
  const structured = parseStructuredOutput(month.summary.structured_output);
  return Array.isArray(structured.themes) ? structured.themes : [];
}

function weeklyStackBadge(week) {
  const hasSummary = !!week?.summary;
  const hasProfile = !!week?.profile;

  if (hasSummary && hasProfile) {
    const count = week.profile?.entry_count ?? 0;
    return `${count} ENTRIES`;
  }

  if (hasProfile) {
    const count = week.profile?.entry_count ?? 0;
    return `${count} ENTRIES`;
  }

  if (hasSummary) return "SUMMARY";
  return "";
}

function monthlyStackBadge(month) {
  const hasSummary = !!month?.summary;
  const hasProfile = !!month?.profile;

  if (hasSummary && hasProfile) {
    const count = month.profile?.entry_count ?? 0;
    return `${count} ENTRIES`;
  }

  if (hasProfile) {
    const count = month.profile?.entry_count ?? 0;
    return `${count} ENTRIES`;
  }

  if (hasSummary) return "SUMMARY";
  return "";
}

const weeklyStacks = computed(() => {
  const byPeriod = new Map();

  const ensureWeek = (periodStart, periodEnd) => {
    const key = `${periodStart}|${periodEnd}`;
    if (!byPeriod.has(key)) {
      byPeriod.set(key, {
        key,
        period_start: periodStart,
        period_end: periodEnd,
        summary: null,
        profile: null
      });
    }
    return byPeriod.get(key);
  };

  for (const profile of weeklyProfiles.value) {
    if (profile?.period_type && profile.period_type !== "weekly") continue;
    const periodStart = String(profile?.period_start ?? "");
    const periodEnd = String(profile?.period_end ?? "");
    if (!periodStart || !periodEnd) continue;

    const week = ensureWeek(periodStart, periodEnd);

    if (
      !week.profile ||
      entryTimestamp(profile?.created_at) > entryTimestamp(week.profile?.created_at)
    ) {
      week.profile = profile;
    }
  }

  for (const summary of weeklySummaries.value) {
    const periodStart = String(summary?.period_start ?? "");
    const periodEnd = String(summary?.period_end ?? "");
    if (!periodStart || !periodEnd) continue;

    const week = ensureWeek(periodStart, periodEnd);

    if (
      !week.summary ||
      entryTimestamp(summary?.created_at) > entryTimestamp(week.summary?.created_at)
    ) {
      week.summary = summary;
    }
  }

  return [...byPeriod.values()].sort((a, b) => {
    const byStart = String(b.period_start).localeCompare(String(a.period_start));
    if (byStart !== 0) return byStart;
    return String(b.period_end).localeCompare(String(a.period_end));
  });
});

const monthlyStacks = computed(() => {
  const byPeriod = new Map();

  const ensureMonth = (periodStart, periodEnd) => {
    const key = `${periodStart}|${periodEnd}`;
    if (!byPeriod.has(key)) {
      byPeriod.set(key, {
        key,
        period_start: periodStart,
        period_end: periodEnd,
        summary: null,
        profile: null
      });
    }
    return byPeriod.get(key);
  };

  for (const profile of monthlyProfiles.value) {
    if (profile?.period_type && profile.period_type !== "monthly") continue;
    const periodStart = String(profile?.period_start ?? "");
    const periodEnd = String(profile?.period_end ?? "");
    if (!periodStart || !periodEnd) continue;

    const month = ensureMonth(periodStart, periodEnd);

    if (
      !month.profile ||
      entryTimestamp(profile?.created_at) > entryTimestamp(month.profile?.created_at)
    ) {
      month.profile = profile;
    }
  }

  for (const summary of monthlySummaries.value) {
    const periodStart = String(summary?.period_start ?? "");
    const periodEnd = String(summary?.period_end ?? "");
    if (!periodStart || !periodEnd) continue;

    const month = ensureMonth(periodStart, periodEnd);

    if (
      !month.summary ||
      entryTimestamp(summary?.created_at) > entryTimestamp(month.summary?.created_at)
    ) {
      month.summary = summary;
    }
  }

  return [...byPeriod.values()].sort((a, b) => {
    const byStart = String(b.period_start).localeCompare(String(a.period_start));
    if (byStart !== 0) return byStart;
    return String(b.period_end).localeCompare(String(a.period_end));
  });
});

const groupedDailyInsights = computed(() => {
  const dayMap = new Map();

  for (const entry of dailyInsights.value) {
    const key = entry?.entry_date ? String(entry.entry_date) : "";
    if (!key) continue;

    if (!dayMap.has(key)) {
      dayMap.set(key, {
        date: key,
        count: 0,
        items: []
      });
    }

    const dayGroup = dayMap.get(key);
    dayGroup.count += 1;
    dayGroup.items.push(entry);
  }

  return [...dayMap.values()]
    .sort((a, b) => b.date.localeCompare(a.date))
    .map((dayGroup) => ({
      ...dayGroup,
      items: dayGroup.items.sort((a, b) => {
        const diff = entryTimestamp(b.created_at) - entryTimestamp(a.created_at);
        if (diff !== 0) return diff;
        return (b.id ?? 0) - (a.id ?? 0);
      })
    }));
});

async function loadWeeklyProfiles() {
  isLoadingWeeklyProfiles.value = true;
  weeklyError.value = "";

  try {
    const res = await apiFetch("/insights/journal/profiles?period_type=weekly");
    if (!res.ok) {
      const msg = await readApiError(res);
      throw new Error(msg);
    }

    const data = await res.json();
    weeklyProfiles.value = Array.isArray(data) ? data : [];
  } catch (e) {
    weeklyError.value = `Unable to load weekly profiles: ${withApiHint(e)}`;
  } finally {
    isLoadingWeeklyProfiles.value = false;
  }
}

async function loadMonthlyProfiles() {
  isLoadingMonthlyProfiles.value = true;

  try {
    const res = await apiFetch("/insights/journal/monthly-profile");
    if (!res.ok) {
      const msg = await readApiError(res);
      throw new Error(msg);
    }

    const data = await res.json();
    monthlyProfiles.value = Array.isArray(data) ? data : [];
  } catch (e) {
    weeklyError.value = `Unable to load monthly profiles: ${withApiHint(e)}`;
  } finally {
    isLoadingMonthlyProfiles.value = false;
  }
}

async function loadWeeklySummaries() {
  isLoadingWeeklySummaries.value = true;

  try {
    const res = await apiFetch("/insights/journal/weekly-summary");

    if (res.status === 404) {
      weeklySummaries.value = [];
      return;
    }

    if (!res.ok) {
      const msg = await readApiError(res);
      throw new Error(msg);
    }

    const data = await res.json();
    weeklySummaries.value = Array.isArray(data) ? data : [];
  } catch (e) {
    weeklyError.value = `Unable to load weekly summaries: ${withApiHint(e)}`;
  } finally {
    isLoadingWeeklySummaries.value = false;
  }
}

async function loadMonthlySummaries() {
  isLoadingMonthlySummaries.value = true;

  try {
    const res = await apiFetch("/insights/journal/monthly-summary");

    if (res.status === 404) {
      monthlySummaries.value = [];
      return;
    }

    if (!res.ok) {
      const msg = await readApiError(res);
      throw new Error(msg);
    }

    const data = await res.json();
    monthlySummaries.value = Array.isArray(data) ? data : [];
  } catch (e) {
    weeklyError.value = `Unable to load monthly summaries: ${withApiHint(e)}`;
  } finally {
    isLoadingMonthlySummaries.value = false;
  }
}

async function loadDailyInsights() {
  isLoadingDailyInsights.value = true;
  dailyError.value = "";
  expandedEntries.value = {};

  try {
    const res = await apiFetch("/journal/");
    if (!res.ok) {
      const msg = await readApiError(res);
      throw new Error(msg);
    }

    const data = await res.json();
    const entries = Array.isArray(data) ? data : [];

    dailyInsights.value = await Promise.all(
      entries.map(async (entry) => {
        let analysis = null;
        let analysisError = "";

        try {
          const analysisRes = await apiFetch(`/journal/${entry.id}/analysis`);
          if (analysisRes.status !== 404) {
            if (!analysisRes.ok) {
              const msg = await readApiError(analysisRes);
              throw new Error(msg);
            }
            analysis = await analysisRes.json();
          }
        } catch (e) {
          analysisError = `Unable to load insight: ${withApiHint(e)}`;
        }

        return {
          ...entry,
          analysis,
          analysisError
        };
      })
    );
  } catch (e) {
    dailyInsights.value = [];
    dailyError.value = `Unable to load daily insights: ${withApiHint(e)}`;
  } finally {
    isLoadingDailyInsights.value = false;
  }
}

async function generateWeekly() {
  isGeneratingWeekly.value = true;
  weeklyError.value = "";

  try {
    const summaryRes = await apiFetch("/insights/journal/weekly-summary", {
      method: "POST"
    });

    if (!summaryRes.ok) {
      const msg = await readApiError(summaryRes);
      throw new Error(msg);
    }

    const profileRes = await apiFetch("/insights/journal/weekly-profile", {
      method: "POST"
    });

    if (!profileRes.ok) {
      const msg = await readApiError(profileRes);
      throw new Error(msg);
    }

    await Promise.all([summaryRes.json(), profileRes.json()]);
    await Promise.all([loadWeeklyProfiles(), loadWeeklySummaries()]);
    flash(
      activeApiBaseUrl.value
        ? `WEEKLY SUMMARY + PROFILE CREATED (${activeApiBaseUrl.value})`
        : "WEEKLY SUMMARY + PROFILE CREATED"
    );
  } catch (e) {
    weeklyError.value = `Unable to generate weekly profile: ${withApiHint(e)}`;
    flash("GENERATION FAILED");
  } finally {
    isGeneratingWeekly.value = false;
  }
}

async function generateMonthly() {
  isGeneratingMonthly.value = true;
  weeklyError.value = "";

  try {
    const summaryRes = await apiFetch("/insights/journal/monthly-summary", {
      method: "POST"
    });

    if (!summaryRes.ok) {
      const msg = await readApiError(summaryRes);
      throw new Error(msg);
    }

    const profileRes = await apiFetch("/insights/journal/monthly-profile", {
      method: "POST"
    });

    if (!profileRes.ok) {
      const msg = await readApiError(profileRes);
      throw new Error(msg);
    }

    await Promise.all([summaryRes.json(), profileRes.json()]);
    await Promise.all([loadMonthlyProfiles(), loadMonthlySummaries()]);
    flash(
      activeApiBaseUrl.value
        ? `MONTHLY SUMMARY + PROFILE CREATED (${activeApiBaseUrl.value})`
        : "MONTHLY SUMMARY + PROFILE CREATED"
    );
  } catch (e) {
    weeklyError.value = `Unable to generate monthly profile: ${withApiHint(e)}`;
    flash("GENERATION FAILED");
  } finally {
    isGeneratingMonthly.value = false;
  }
}

onMounted(async () => {
  await Promise.all([
    loadWeeklyProfiles(),
    loadMonthlyProfiles(),
    loadWeeklySummaries(),
    loadMonthlySummaries(),
    loadDailyInsights()
  ]);
});
</script>

<style scoped>
.screen {
  padding: var(--pad);
  position: relative;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 14px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}

.title {
  margin: 0;
  font-size: clamp(26px, 4vw, 46px);
  color: var(--fg);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.subtitle {
  margin: 8px 0 0;
  color: var(--muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 14px;
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.panel {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
  position: relative;
  z-index: 1;
}

.meta-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  color: var(--muted);
  font-size: 14px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.status {
  color: var(--fg);
}

.btn {
  border: 1px solid var(--line);
  background: transparent;
  color: var(--fg);
  padding: 10px 12px;
  border-radius: 8px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 16px;
  cursor: pointer;
}

.btn:hover {
  background: rgba(255, 255, 255, 0.06);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.accordion-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--line2);
  background: transparent;
  color: var(--fg);
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.accordion-toggle + .accordion-toggle,
.tree-group + .tree-group,
.profile-card + .profile-card {
  margin-top: 10px;
}

.top-level {
  margin-top: 8px;
}

.accordion-body {
  margin-top: 10px;
}

.accordion-body.nested {
  padding-left: 14px;
}

.summary-arrow {
  transition: transform 0.18s ease;
}

.summary-arrow.open {
  transform: rotate(90deg);
}

.section-count {
  margin-left: auto;
  color: var(--muted);
  font-size: 12px;
}

.profile-card {
  border: 1px solid var(--line2);
  border-radius: 10px;
  padding: 10px;
}

.daily-entry-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.daily-entry-time {
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.entry-toggle {
  margin-top: 10px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--muted);
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font: inherit;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.entry-toggle:hover {
  color: var(--fg);
}

.entry-toggle-text {
  font-size: 13px;
}

.profile-body {
  margin-top: 12px;
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.profile-stat {
  border: 1px solid var(--line2);
  border-radius: 8px;
  padding: 10px;
}

.profile-stat-label {
  display: block;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.12em;
  margin-bottom: 6px;
}

.profile-stat-value {
  display: block;
  font-size: 16px;
  line-height: 1.4;
}

.profile-section + .profile-section {
  margin-top: 14px;
}

.profile-section-title {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.stack-block-title {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.profile-paragraph {
  margin: 0;
  line-height: 1.5;
}

.stack-divider {
  border-top: 1px dashed var(--line2);
  margin: 14px 0;
}

.stack-kv {
  margin: 0;
  line-height: 1.5;
  text-transform: none;
}

.stack-kv + .stack-kv {
  margin-top: 6px;
}

.stack-quote {
  margin: 12px 0 0;
  color: var(--muted);
  line-height: 1.5;
}

.profile-list {
  margin: 0;
  padding-left: 18px;
  line-height: 1.5;
}

.empty-text,
.error-text {
  color: var(--muted);
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
