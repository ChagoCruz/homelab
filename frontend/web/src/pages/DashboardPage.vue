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
              :spark-values="moodSparkValues"
            />

            <KpiCard
              label="calories"
              :value="caloriesValue"
              :trend="caloriesTrend"
              :spark-values="caloriesSparkValues"
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
              :spark-values="weightSparkValues"
            />
          </div>
        </section>

        <section class="panel-block wide">
          <div class="block-header">
            <h2>featured chart</h2>

            <div class="range-chips" role="group" aria-label="mood range">
              <button
                v-for="days in [7, 14, 30]"
                :key="`range-${days}`"
                class="chip"
                :class="{ active: selectedRangeDays === days }"
                :disabled="statsLoading"
                @click="setRange(days)"
              >
                {{ days }}d
              </button>
            </div>
          </div>

          <FeaturedMoodTrend
            :rows="dailyFacts"
            :loading="statsLoading"
            :error="dailyError"
            :meta="featuredMeta"
          />

          <div class="primary-cta-row">
            <RouterLink to="/stats/health" class="terminal-link strong-link">view detailed analytics</RouterLink>
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
import FeaturedMoodTrend from "../components/FeaturedMoodTrend.vue";
import KpiCard from "../components/KpiCard.vue";
import { formatSignedDelta, shiftDate, toDateOnly, toFiniteNumber } from "../utils/chartUtils";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const latestWeather = ref(null);
const weatherLoading = ref(false);
const weatherError = ref("");

const selectedRangeDays = ref(7);
const dailyFacts = ref([]);
const statsLoading = ref(false);
const dailyError = ref("");

const healthSeries = ref([]);

function todayDate() {
  return toDateOnly(new Date());
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

function compactConsecutiveValues(values, epsilon = 0.01) {
  const compacted = [];
  let previous = null;

  for (const raw of values) {
    const value = toFiniteNumber(raw);
    if (value === null) continue;
    if (previous === null || Math.abs(value - previous) > epsilon) {
      compacted.push(value);
      previous = value;
    }
  }

  return compacted;
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
  const start = shiftDate(end, -(selectedRangeDays.value - 1));

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
  try {
    const end = todayDate();
    const res = await fetch(`${API_BASE}/health/dashboard?end_date=${encodeURIComponent(end)}&days=30`);
    if (!res.ok) {
      healthSeries.value = [];
      return;
    }

    const payload = await res.json();
    healthSeries.value = sortRowsByDate(Array.isArray(payload?.series) ? payload.series : []);
  } catch {
    healthSeries.value = [];
  }
}

async function fetchStats() {
  statsLoading.value = true;
  dailyError.value = "";

  try {
    dailyFacts.value = await fetchDailyLifeFacts();
  } catch (err) {
    dailyFacts.value = [];
    dailyError.value = err?.message || "unable to load daily stats";
  } finally {
    statsLoading.value = false;
  }
}

function setRange(days) {
  if (selectedRangeDays.value === days || statsLoading.value) return;
  selectedRangeDays.value = days;
  fetchStats();
}

const featuredMeta = computed(() => `${selectedRangeDays.value}-day focus`);

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
const moodSparkValues = computed(() =>
  dailyFacts.value
    .map((row) => normalizeMood(row?.avg_mood_score))
    .filter((value) => value !== null)
);

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
const caloriesSparkValues = computed(() => dailyFacts.value.map((row) => toFiniteNumber(row?.total_calories)));

const alcoholDaysValue = computed(() => {
  const recent = dailyFacts.value.slice(-7);
  const count = recent.filter((row) => Boolean(row?.had_alcohol)).length;
  return `${count} / ${recent.length || 7}`;
});
const alcoholDaysTrend = computed(() => {
  const count = dailyFacts.value.slice(-7).filter((row) => Boolean(row?.had_alcohol)).length;
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
const weightSparkValues = computed(() =>
  compactConsecutiveValues(orderedHealthSeries.value.map((row) => row?.weight))
);

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

.range-chips {
  display: inline-flex;
  gap: 6px;
}

.chip {
  border: 1px solid var(--line2);
  border-radius: 999px;
  padding: 4px 10px;
  background: transparent;
  color: var(--fg);
  font: inherit;
  text-transform: lowercase;
  cursor: pointer;
}

.chip.active {
  border-color: var(--line);
  background: rgba(255, 255, 255, 0.08);
}

.chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.primary-cta-row {
  margin-top: 10px;
  display: flex;
  justify-content: flex-start;
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

.strong-link {
  border-color: rgba(255, 255, 255, 0.44);
  background: rgba(255, 255, 255, 0.04);
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

  .terminal-link,
  .chip {
    font-size: 0.84rem;
    padding: 4px 8px;
  }
}
</style>
