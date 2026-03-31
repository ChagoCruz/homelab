<template>
  <main class="page-shell">
    <section class="panel">
      <div class="panel-header">
        <h1>homelab</h1>
        <span class="panel-subtle">main dashboard</span>
      </div>

      <div class="dashboard-grid">
        <section class="panel-block wide">
          <div class="block-header">
            <h2>kpi snapshot</h2>
            <span class="block-meta">mobile first at-a-glance metrics</span>
          </div>

          <div class="kpi-grid">
            <KpiCard
              label="mood"
              :value="moodValue"
              :trend="moodTrend"
            />

            <KpiCard
              label="calories"
              :value="caloriesValue"
              :trend="caloriesTrend"
            />

            <KpiCard
              label="alcohol days this week"
              :value="alcoholDaysValue"
              :trend="alcoholDaysTrend"
            />

            <KpiCard
              label="weight"
              :value="weightValue"
              :trend="weightTrend"
            />
          </div>
        </section>

        <section class="panel-block wide">
          <div class="block-header">
            <h2>health dashboard</h2>
            <span class="block-meta">last 7 days (ending {{ healthDashboardEndDate }})</span>
          </div>

          <div v-if="healthLoading" class="empty-row">loading dashboard...</div>

          <div v-else class="dashboard-stack">
            <div class="dashPanel wideDash">
              <div class="dashTitle">Calories — Last 7 Days</div>
              <div class="dashSub">IN / OUT / NET (IN - OUT)</div>

              <div class="monoLine">
                <span class="tag">TOTAL</span>
                <span>IN {{ totalIn }} | OUT {{ totalOut }} | NET {{ totalNet }}</span>
              </div>

              <div class="dashTable caloriesTable">
                <div class="dashHead calHead">
                  <div>DATE</div>
                  <div>IN</div>
                  <div>OUT</div>
                  <div>NET</div>
                </div>

                <div
                  v-for="entry in caloriesLast7"
                  :key="`cal-${entry.date}`"
                  class="dashRow calRow"
                >
                  <div>{{ formatDashboardDate(entry.date) }}</div>
                  <div>{{ entry.calories_in ?? 0 }}</div>
                  <div>{{ entry.calories_out ?? 0 }}</div>
                  <div :class="{ neg: (entry.calories_net ?? 0) < 0, pos: (entry.calories_net ?? 0) > 0 }">
                    {{ entry.calories_net ?? 0 }}
                  </div>
                </div>
              </div>
            </div>

            <div class="dashPanel wideDash">
              <div class="dashTitle">Blood Pressure — Recent</div>
              <div class="dashSub">LAST 7 ENTRIES</div>

              <div class="dashTable">
                <div class="dashHead bpHead">
                  <div>DATE</div>
                  <div>BP</div>
                </div>

                <div v-if="recentBpEntries.length === 0" class="dashRow bpRow">
                  <div>—</div>
                  <div>No blood pressure entries yet</div>
                </div>

                <div
                  v-for="entry in recentBpEntries"
                  :key="`bp-${entry.date}`"
                  class="dashRow bpRow"
                >
                  <div>{{ formatDashboardDate(entry.date) }}</div>
                  <div>{{ entry.systolic }} / {{ entry.diastolic }}</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <AIInsightPanel compact />

        <section class="panel-block">
          <div class="block-header">
            <h2>system</h2>
          </div>

          <div class="kv-list">
            <div class="kv-row">
              <span class="kv-key">status</span>
              <span class="kv-value">online</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">mode</span>
              <span class="kv-value">life terminal</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">ai</span>
              <span class="kv-value">ollama / gemma3:4b</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">weather</span>
              <span class="kv-value">{{ displayWeatherValue(latestWeather?.weather_summary) }}</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">temp high</span>
              <span class="kv-value">{{ displayWeatherValue(latestWeather?.temp_max_f, formatTemp) }}</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">temp low</span>
              <span class="kv-value">{{ displayWeatherValue(latestWeather?.temp_min_f, formatTemp) }}</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">sunrise</span>
              <span class="kv-value">{{ displayWeatherValue(latestWeather?.sunrise, formatClockTime) }}</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">sunset</span>
              <span class="kv-value">{{ displayWeatherValue(latestWeather?.sunset, formatClockTime) }}</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">moon phase</span>
              <span class="kv-value">{{ displayWeatherValue(latestWeather?.moon_phase_name) }}</span>
            </div>
          </div>
        </section>

        <section class="panel-block">
          <div class="block-header">
            <h2>quick links</h2>
          </div>

          <div class="quick-links">
            <RouterLink to="/journal" class="terminal-link">journal</RouterLink>
            <RouterLink to="/bills" class="terminal-link">bills</RouterLink>
            <RouterLink to="/mileage" class="terminal-link">mileage</RouterLink>
            <RouterLink to="/stats/health" class="terminal-link">health stats</RouterLink>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AIInsightPanel from "../components/AIInsightPanel.vue";
import KpiCard from "../components/KpiCard.vue";
import { formatSignedDelta, shiftDate, toDateOnly, toFiniteNumber } from "../utils/chartUtils";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const DAILY_FACT_WINDOW_DAYS = 7;
const HEALTH_DASHBOARD_DAYS = 30;
const CALORIES_WINDOW_DAYS = 7;

const latestWeather = ref(null);
const weatherLoading = ref(false);
const weatherError = ref("");

const dailyFacts = ref([]);
const healthLoading = ref(false);
const healthSeries = ref([]);
const bpLast7 = ref([]);

function todayDate() {
  return toDateOnly(new Date());
}

function currentWeekStartDate() {
  const today = new Date(`${todayDate()}T00:00:00`);
  if (Number.isNaN(today.getTime())) {
    return todayDate();
  }

  // Monday-based week to match backend date_trunc('week') behavior.
  const dayOfWeek = today.getDay(); // 0 = Sunday, 1 = Monday, ...
  const offsetToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  today.setDate(today.getDate() + offsetToMonday);
  return toDateOnly(today);
}

function buildEmptyHealthSeries(endDate, days) {
  const startDate = shiftDate(endDate, -(days - 1));

  return Array.from({ length: days }, (_, index) => {
    const date = shiftDate(startDate, index);
    return {
      date,
      weight: null,
      systolic: null,
      diastolic: null,
      calories_in: 0,
      calories_out: 0,
      calories_net: 0,
    };
  });
}

function normalizeMood(value) {
  const n = toFiniteNumber(value);
  if (n === null) return null;
  return Math.max(0, Math.min(10, n));
}

function formatTemp(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return "--";
  return `${n.toFixed(1)}°f`;
}

function formatClockTime(value) {
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "--";

  return dt.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDashboardDate(value) {
  const raw = String(value ?? "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    return raw.slice(5);
  }

  const dt = new Date(raw);
  if (Number.isNaN(dt.getTime())) return "--";
  const month = String(dt.getMonth() + 1).padStart(2, "0");
  const day = String(dt.getDate()).padStart(2, "0");
  return `${month}-${day}`;
}

function displayWeatherValue(value, formatter) {
  if (weatherLoading.value) return "loading...";
  if (weatherError.value) return "unavailable";
  if (value === null || value === undefined || value === "") return "--";

  const formatted = formatter ? formatter(value) : String(value);
  return formatted || "--";
}

function findLastBy(rows, predicate) {
  for (let i = rows.length - 1; i >= 0; i -= 1) {
    if (predicate(rows[i])) {
      return rows[i];
    }
  }
  return null;
}

function findPrevBy(rows, predicate) {
  let foundLatest = false;
  for (let i = rows.length - 1; i >= 0; i -= 1) {
    if (!predicate(rows[i])) continue;
    if (!foundLatest) {
      foundLatest = true;
      continue;
    }
    return rows[i];
  }
  return null;
}

function getRowDate(row) {
  return String(row?.date ?? row?.entry_date ?? "");
}

function sortRowsByDate(rows) {
  return [...rows].sort((a, b) => getRowDate(a).localeCompare(getRowDate(b)));
}

async function fetchLatestWeather() {
  weatherLoading.value = true;
  weatherError.value = "";

  try {
    const res = await fetch(`${API_BASE}/weather/latest`);
    if (res.status === 404) {
      latestWeather.value = null;
      return;
    }

    if (!res.ok) {
      throw new Error(`failed to load weather (${res.status})`);
    }

    latestWeather.value = await res.json();
  } catch (err) {
    latestWeather.value = null;
    weatherError.value = err?.message || "unable to load weather";
  } finally {
    weatherLoading.value = false;
  }
}

async function fetchDailyLifeFacts() {
  const end = todayDate();
  const start = shiftDate(end, -(DAILY_FACT_WINDOW_DAYS - 1));

  const url = new URL(`${API_BASE}/stats/daily-life-facts`);
  url.searchParams.set("start_date", start);
  url.searchParams.set("end_date", end);

  const res = await fetch(url.toString());
  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(msg || `failed to load daily stats (${res.status})`);
  }

  const payload = await res.json();
  return Array.isArray(payload) ? payload : [];
}

async function fetchHealthSnapshot() {
  healthLoading.value = true;

  try {
    const end = todayDate();
    const res = await fetch(`${API_BASE}/health/dashboard?end_date=${encodeURIComponent(end)}&days=${HEALTH_DASHBOARD_DAYS}`);

    if (!res.ok) {
      healthSeries.value = buildEmptyHealthSeries(end, HEALTH_DASHBOARD_DAYS);
      bpLast7.value = [];
      return;
    }

    const payload = await res.json();
    const series = Array.isArray(payload?.series) ? payload.series : [];
    healthSeries.value = sortRowsByDate(series.length ? series : buildEmptyHealthSeries(end, HEALTH_DASHBOARD_DAYS));
    bpLast7.value = Array.isArray(payload?.bp_last_7) ? payload.bp_last_7 : [];
  } catch {
    const end = todayDate();
    healthSeries.value = buildEmptyHealthSeries(end, HEALTH_DASHBOARD_DAYS);
    bpLast7.value = [];
  } finally {
    healthLoading.value = false;
  }
}

async function fetchStats() {
  try {
    dailyFacts.value = await fetchDailyLifeFacts();
  } catch {
    dailyFacts.value = [];
  }
}

const latestMood = computed(() => findLastBy(dailyFacts.value, (row) => normalizeMood(row?.avg_mood_score) !== null));
const previousMood = computed(() => findPrevBy(dailyFacts.value, (row) => normalizeMood(row?.avg_mood_score) !== null));
const moodValue = computed(() => {
  const val = normalizeMood(latestMood.value?.avg_mood_score);
  return val === null ? "--" : `${val.toFixed(1)} / 10`;
});
const moodTrend = computed(() => {
  const latest = normalizeMood(latestMood.value?.avg_mood_score);
  const prev = normalizeMood(previousMood.value?.avg_mood_score);
  if (latest === null || prev === null) return "not enough entries";
  return `${formatSignedDelta(latest - prev)} vs previous day`;
});

const latestCalories = computed(() => findLastBy(dailyFacts.value, (row) => toFiniteNumber(row?.total_calories) !== null));
const previousCalories = computed(() => findPrevBy(dailyFacts.value, (row) => toFiniteNumber(row?.total_calories) !== null));
const caloriesValue = computed(() => {
  const val = toFiniteNumber(latestCalories.value?.total_calories);
  return val === null ? "--" : `${Math.round(val).toLocaleString()} kcal`;
});
const caloriesTrend = computed(() => {
  const latest = toFiniteNumber(latestCalories.value?.total_calories);
  const prev = toFiniteNumber(previousCalories.value?.total_calories);
  if (latest === null || prev === null) return "not enough entries";
  return `${formatSignedDelta(latest - prev, 0)} kcal vs previous`;
});

const alcoholDaysValue = computed(() => {
  const weekStart = currentWeekStartDate();
  const today = todayDate();

  const count = dailyFacts.value.filter((row) => {
    const day = String(row?.day ?? row?.date ?? "");
    return day >= weekStart && day <= today && Boolean(row?.had_alcohol);
  }).length;

  return `${count} / 7`;
});
const alcoholDaysTrend = computed(() => {
  const weekStart = currentWeekStartDate();
  const today = todayDate();

  const count = dailyFacts.value.filter((row) => {
    const day = String(row?.day ?? row?.date ?? "");
    return day >= weekStart && day <= today && Boolean(row?.had_alcohol);
  }).length;

  if (count === 0) return "clean week";
  if (count <= 2) return "low frequency";
  return "watch this trend";
});

const orderedHealthSeries = computed(() => sortRowsByDate(healthSeries.value));

const latestWeight = computed(() => findLastBy(orderedHealthSeries.value, (row) => toFiniteNumber(row?.weight) !== null));
const previousWeight = computed(() => findPrevBy(orderedHealthSeries.value, (row) => toFiniteNumber(row?.weight) !== null));
const weightValue = computed(() => {
  const val = toFiniteNumber(latestWeight.value?.weight);
  return val === null ? "--" : `${val.toFixed(1)} lb`;
});
const weightTrend = computed(() => {
  const latest = toFiniteNumber(latestWeight.value?.weight);
  const prev = toFiniteNumber(previousWeight.value?.weight);
  if (latest === null || prev === null) return "not enough entries";
  return `${formatSignedDelta(latest - prev)} lb vs previous`;
});

const caloriesLast7 = computed(() => {
  const lastSeven = orderedHealthSeries.value.slice(-CALORIES_WINDOW_DAYS);
  return [...lastSeven].sort((a, b) => String(b.date ?? "").localeCompare(String(a.date ?? "")));
});

const totalIn = computed(() => caloriesLast7.value.reduce((sum, row) => sum + Number(row?.calories_in ?? 0), 0));
const totalOut = computed(() => caloriesLast7.value.reduce((sum, row) => sum + Number(row?.calories_out ?? 0), 0));
const totalNet = computed(() => caloriesLast7.value.reduce((sum, row) => sum + Number(row?.calories_net ?? 0), 0));

const healthDashboardEndDate = computed(() => {
  const latest = orderedHealthSeries.value[orderedHealthSeries.value.length - 1];
  if (!latest) return formatDashboardDate(todayDate());
  return formatDashboardDate(latest.date);
});

const recentBpEntries = computed(() => bpLast7.value.slice(0, 7));

onMounted(async () => {
  await Promise.all([fetchLatestWeather(), fetchStats(), fetchHealthSnapshot()]);
});
</script>

<style scoped>
.page-shell {
  min-height: 100vh;
  padding: clamp(14px, 3vw, 30px);
  box-sizing: border-box;
}

.panel {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: var(--pad);
  background: rgba(255, 255, 255, 0.02);
}

.panel-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 10px;
  margin-bottom: 14px;
}

.panel-header h1 {
  margin: 0;
  font-size: clamp(1.8rem, 4vw, 3rem);
  font-weight: 400;
  text-transform: lowercase;
}

.panel-subtle {
  color: var(--muted);
  font-size: 1rem;
  text-transform: lowercase;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.panel-block {
  border: 1px solid var(--line2);
  border-radius: var(--radius);
  padding: 12px;
  background: rgba(255, 255, 255, 0.01);
}

.panel-block.wide {
  grid-column: 1 / -1;
}

.block-header {
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line2);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.block-header h2 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 400;
  text-transform: lowercase;
}

.block-meta {
  color: var(--muted);
  text-transform: lowercase;
  font-size: 0.86rem;
}

.kpi-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.empty-row {
  padding: 12px;
  border: 1px dashed var(--line2);
  border-radius: 10px;
  opacity: 0.8;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-size: 12px;
}

.dashboard-stack {
  display: grid;
  gap: 14px;
}

.dashPanel {
  border: 1px solid var(--line2);
  border-radius: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
}

.wideDash {
  grid-column: span 12;
}

.dashTitle {
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.dashSub {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.75;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.monoLine {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--line2);
  border-radius: 10px;
  display: flex;
  gap: 10px;
  align-items: center;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 12px;
  flex-wrap: wrap;
}

.tag {
  border: 1px solid var(--line2);
  border-radius: 8px;
  padding: 4px 8px;
  opacity: 0.9;
}

.dashTable {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}

.dashHead {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--line2);
  border-radius: 10px;
  opacity: 0.85;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 12px;
}

.dashRow {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
}

.bpHead,
.bpRow {
  grid-template-columns: 1fr 1fr;
}

.calHead {
  grid-template-columns: 1fr 90px 90px 90px;
}

.calRow {
  grid-template-columns: 1fr 90px 90px 90px;
}

.neg {
  opacity: 0.85;
}

.pos {
  opacity: 1;
}

.kv-list {
  display: grid;
  gap: 8px;
}

.kv-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px dotted var(--line2);
  padding-bottom: 5px;
}

.kv-key {
  color: var(--muted);
  text-transform: lowercase;
}

.kv-value {
  text-align: right;
  text-transform: lowercase;
}

.quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.terminal-link {
  display: inline-block;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 11px;
  color: var(--fg);
  text-decoration: none;
  text-transform: lowercase;
}

.terminal-link:hover {
  background: rgba(255, 255, 255, 0.06);
}

@media (min-width: 920px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .kpi-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 430px) {
  .panel {
    padding: 12px;
  }

  .panel-subtle {
    font-size: 0.86rem;
  }

  .block-header h2 {
    font-size: 1.02rem;
  }

  .block-meta {
    font-size: 0.74rem;
  }

  .terminal-link {
    font-size: 0.84rem;
    padding: 4px 8px;
  }

  .calHead,
  .calRow {
    grid-template-columns: minmax(0, 1fr) minmax(44px, 52px) minmax(44px, 52px) minmax(44px, 52px);
    gap: 6px;
    padding: 8px;
    font-size: 12px;
  }

  .calHead > div,
  .calRow > div,
  .dashRow > div,
  .dashHead > div {
    min-width: 0;
  }
}
</style>
