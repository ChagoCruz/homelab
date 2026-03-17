<template>
  <main class="screen">
    <header class="header">
      <div>
        <h1 class="title">JOURNAL INSIGHTS</h1>
        <p class="subtitle">Nested weekly pattern profiles</p>
      </div>

      <div class="actions">
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
        <span v-if="isLoadingProfiles">LOADING PROFILES...</span>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <button class="accordion-toggle top-level" type="button" @click="toggleWeeklyRoot">
        <span class="summary-arrow" :class="{ open: weeklyRootOpen }">▶</span>
        <span>WEEKLY PROFILES</span>
        <span class="section-count">{{ profiles.length }}</span>
      </button>

      <transition name="expand">
        <div v-if="weeklyRootOpen" class="accordion-body">
          <p v-if="!isLoadingProfiles && groupedProfiles.length === 0" class="empty-text">
            No weekly profiles yet.
          </p>

          <div v-else class="accordion-tree">
            <section
              v-for="yearGroup in groupedProfiles"
              :key="yearGroup.year"
              class="tree-group"
            >
              <button class="accordion-toggle" type="button" @click="toggleYear(yearGroup.year)">
                <span class="summary-arrow" :class="{ open: isYearOpen(yearGroup.year) }">▶</span>
                <span>{{ yearGroup.year }}</span>
                <span class="section-count">{{ yearGroup.count }}</span>
              </button>

              <transition name="expand">
                <div v-if="isYearOpen(yearGroup.year)" class="accordion-body nested">
                  <section
                    v-for="monthGroup in yearGroup.months"
                    :key="`${yearGroup.year}-${monthGroup.month}`"
                    class="tree-group"
                  >
                    <button
                      class="accordion-toggle"
                      type="button"
                      @click="toggleMonth(yearGroup.year, monthGroup.month)"
                    >
                      <span
                        class="summary-arrow"
                        :class="{ open: isMonthOpen(yearGroup.year, monthGroup.month) }"
                      >
                        ▶
                      </span>
                      <span>{{ monthGroup.label }}</span>
                      <span class="section-count">{{ monthGroup.count }}</span>
                    </button>

                    <transition name="expand">
                      <div
                        v-if="isMonthOpen(yearGroup.year, monthGroup.month)"
                        class="accordion-body nested"
                      >
                        <article
                          v-for="profile in monthGroup.items"
                          :key="profile.id"
                          class="profile-card"
                        >
                          <button
                            class="accordion-toggle profile-toggle"
                            type="button"
                            @click="toggleProfile(profile.id)"
                          >
                            <span
                              class="summary-arrow"
                              :class="{ open: isProfileOpen(profile.id) }"
                            >
                              ▶
                            </span>
                            <span>
                              {{ formatRange(profile.period_start, profile.period_end) }}
                            </span>
                            <span class="section-count">
                              {{ profile.entry_count ?? 0 }} ENTRIES
                            </span>
                          </button>

                          <transition name="expand">
                            <div v-if="isProfileOpen(profile.id)" class="profile-body">
                              <div class="profile-stats">
                                <div class="profile-stat">
                                  <span class="profile-stat-label">AVG MOOD</span>
                                  <span class="profile-stat-value">
                                    {{ formatMood(profile.average_mood_score) }}
                                  </span>
                                </div>

                                <div class="profile-stat">
                                  <span class="profile-stat-label">PERIOD</span>
                                  <span class="profile-stat-value">
                                    {{ profile.period_start }} → {{ profile.period_end }}
                                  </span>
                                </div>
                              </div>

                              <section v-if="profile.pattern_summary" class="profile-section">
                                <h3 class="profile-section-title">SUMMARY</h3>
                                <p class="profile-paragraph">{{ profile.pattern_summary }}</p>
                              </section>

                              <section
                                v-if="profile.dominant_emotions?.length"
                                class="profile-section"
                              >
                                <h3 class="profile-section-title">DOMINANT EMOTIONS</h3>
                                <ul class="profile-list">
                                  <li v-for="(item, idx) in profile.dominant_emotions" :key="idx">
                                    {{ item }}
                                  </li>
                                </ul>
                              </section>

                              <section
                                v-if="profile.recurring_stressors?.length"
                                class="profile-section"
                              >
                                <h3 class="profile-section-title">RECURRING STRESSORS</h3>
                                <ul class="profile-list">
                                  <li v-for="(item, idx) in profile.recurring_stressors" :key="idx">
                                    {{ item }}
                                  </li>
                                </ul>
                              </section>

                              <section
                                v-if="profile.recurring_positive_signals?.length"
                                class="profile-section"
                              >
                                <h3 class="profile-section-title">POSITIVE SIGNALS</h3>
                                <ul class="profile-list">
                                  <li
                                    v-for="(item, idx) in profile.recurring_positive_signals"
                                    :key="idx"
                                  >
                                    {{ item }}
                                  </li>
                                </ul>
                              </section>

                              <section
                                v-if="profile.recurring_thinking_patterns?.length"
                                class="profile-section"
                              >
                                <h3 class="profile-section-title">THINKING PATTERNS</h3>
                                <ul class="profile-list">
                                  <li
                                    v-for="(item, idx) in profile.recurring_thinking_patterns"
                                    :key="idx"
                                  >
                                    {{ item }}
                                  </li>
                                </ul>
                              </section>

                              <section
                                v-if="profile.recurring_life_direction_signals?.length"
                                class="profile-section"
                              >
                                <h3 class="profile-section-title">LIFE DIRECTION</h3>
                                <ul class="profile-list">
                                  <li
                                    v-for="(item, idx) in profile.recurring_life_direction_signals"
                                    :key="idx"
                                  >
                                    {{ item }}
                                  </li>
                                </ul>
                              </section>

                              <section v-if="profile.core_values?.length" class="profile-section">
                                <h3 class="profile-section-title">CORE VALUES</h3>
                                <ul class="profile-list">
                                  <li v-for="(item, idx) in profile.core_values" :key="idx">
                                    {{ item }}
                                  </li>
                                </ul>
                              </section>
                            </div>
                          </transition>
                        </article>
                      </div>
                    </transition>
                  </section>
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
const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const profiles = ref([]);
const isLoadingProfiles = ref(false);
const isGeneratingWeekly = ref(false);
const status = ref("");
const error = ref("");

const weeklyRootOpen = ref(true);
const openYears = ref({});
const openMonths = ref({});
const openProfiles = ref({});

function flash(msg) {
  status.value = msg;
  window.clearTimeout(flash._t);
  flash._t = window.setTimeout(() => (status.value = ""), 2200);
}

function goBack() {
  router.push("/journal");
}

function toggleWeeklyRoot() {
  weeklyRootOpen.value = !weeklyRootOpen.value;
}

function toggleYear(year) {
  openYears.value = {
    ...openYears.value,
    [year]: !openYears.value[year]
  };
}

function isYearOpen(year) {
  return !!openYears.value[year];
}

function monthKey(year, month) {
  return `${year}-${month}`;
}

function toggleMonth(year, month) {
  const key = monthKey(year, month);
  openMonths.value = {
    ...openMonths.value,
    [key]: !openMonths.value[key]
  };
}

function isMonthOpen(year, month) {
  return !!openMonths.value[monthKey(year, month)];
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

const groupedProfiles = computed(() => {
  const yearMap = new Map();

  for (const profile of profiles.value) {
    const start = new Date(`${profile.period_start}T00:00:00`);
    const year = start.getFullYear();
    const month = start.getMonth();
    const monthLabel = start.toLocaleDateString(undefined, {
      month: "long"
    }).toUpperCase();

    if (!yearMap.has(year)) {
      yearMap.set(year, {
        year,
        count: 0,
        months: new Map()
      });
    }

    const yearGroup = yearMap.get(year);
    yearGroup.count += 1;

    if (!yearGroup.months.has(month)) {
      yearGroup.months.set(month, {
        month,
        label: monthLabel,
        count: 0,
        items: []
      });
    }

    const monthGroup = yearGroup.months.get(month);
    monthGroup.count += 1;
    monthGroup.items.push(profile);
  }

  return [...yearMap.values()]
    .sort((a, b) => b.year - a.year)
    .map((yearGroup) => ({
      year: yearGroup.year,
      count: yearGroup.count,
      months: [...yearGroup.months.values()]
        .sort((a, b) => b.month - a.month)
        .map((monthGroup) => ({
          ...monthGroup,
          items: monthGroup.items.sort((a, b) =>
            b.period_start.localeCompare(a.period_start)
          )
        }))
    }));
});

async function loadProfiles() {
  isLoadingProfiles.value = true;
  error.value = "";

  try {
    const res = await fetch(`${baseUrl}/insights/journal/profiles`);
    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const data = await res.json();
    profiles.value = Array.isArray(data) ? data : [];
  } catch (e) {
    error.value = `Unable to load journal profiles: ${e.message}`;
  } finally {
    isLoadingProfiles.value = false;
  }
}

async function generateWeekly() {
  isGeneratingWeekly.value = true;
  error.value = "";

  try {
    const res = await fetch(`${baseUrl}/insights/journal/weekly`, {
      method: "POST"
    });

    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    await res.json();
    flash("WEEKLY PROFILE CREATED");
    await loadProfiles();
  } catch (e) {
    error.value = `Unable to generate weekly profile: ${e.message}`;
    flash("GENERATION FAILED");
  } finally {
    isGeneratingWeekly.value = false;
  }
}

onMounted(async () => {
  await loadProfiles();
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

.profile-paragraph {
  margin: 0;
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