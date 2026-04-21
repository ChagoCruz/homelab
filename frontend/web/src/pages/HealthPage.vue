<template>
  <div class="screen">
    <div class="scanlines"></div>
    <div class="vignette"></div>

    <header class="header">
      <h1 class="title">HEALTH</h1>

      <div class="actions">
        <div class="field inline">
          <label class="label">DATE</label>
          <input class="input" type="date" v-model="selectedDate" @change="loadAll" />
        </div>

        <button v-if="!showDashboard" class="btn" :disabled="isSaving || isSafetySaving" @click="saveAll">
          {{ isSaving ? "SAVING..." : "SAVE ALL" }}
        </button>

        <button
          class="btn ghost"
          :class="{ active: showDashboard }"
          :disabled="dashLoading"
          type="button"
          @click="toggleStatsView"
        >
          {{ dashLoading ? "LOADING..." : (showDashboard ? "ENTRY" : "STATS") }}
        </button>
      </div>
    </header>

    <div v-if="status" class="status" :class="{ ok: statusType === 'ok', err: statusType === 'err' }">
      {{ status }}
    </div>

    <section class="grid">
      <template v-if="!showDashboard">
      <!-- WEIGHT -->
      <div class="panel">
        <div class="panelHeader">
          <div class="panelTitle">WEIGHT</div>
          <div class="panelMeta">ONE ENTRY / DAY</div>
        </div>

        <div class="row rowWeight">
          <div class="field">
            <label class="label">WEIGHT (LB)</label>
            <input class="input" type="number" step="0.1" v-model="weightValue" placeholder="e.g. 252.4" />
          </div>

          <button class="btn small" :disabled="isSaving || isSafetySaving" @click="saveAll">SAVE</button>
        </div>
      </div>

      <!-- BLOOD PRESSURE -->
      <div class="panel">
        <div class="panelHeader">
          <div class="panelTitle">BLOOD PRESSURE</div>
          <div class="panelMeta">ONE ENTRY / DAY</div>
        </div>

        <div class="row rowBP">
          <div class="field">
            <label class="label">SYSTOLIC</label>
            <input class="input" type="number" v-model="bpSystolic" placeholder="e.g. 124" />
          </div>

          <div class="field">
            <label class="label">DIASTOLIC</label>
            <input class="input" type="number" v-model="bpDiastolic" placeholder="e.g. 78" />
          </div>

          <button class="btn small" :disabled="isSaving || isSafetySaving" @click="saveAll">SAVE</button>
        </div>
      </div>

      <!-- SAFETY MEETING -->
      <div class="panel wide">
        <div class="panelHeader">
          <div class="panelTitle">SAFETY MEETING</div>
          <div class="panelMeta">ONE TOGGLE / DAY</div>
        </div>

        <div class="row rowSafety">
          <label class="toggleRowLabel">
            <input class="toggleInput" type="checkbox" v-model="safetyMeetingCompleted" />
            <span class="toggleText">SAFE TODAY</span>
          </label>

          <button class="btn small" :disabled="isSaving || isSafetySaving" @click="saveSafetyMeeting()">
            {{ isSafetySaving ? "SAVING..." : "SAVE" }}
          </button>
        </div>
      </div>

      <!-- DIET -->
      <div class="panel wide">
        <div class="panelHeader">
          <div class="panelTitle">DIET LOG</div>
          <div class="panelMeta">{{ dietCaloriesMeta }}</div>
        </div>

        <div class="table dietTable">
          <div class="thead dietHead">
            <div>MEAL</div>
            <div>FOOD</div>
            <div>CAL</div>
            <div>CONF</div>
            <div></div>
          </div>

          <div v-if="dietRows.length === 0" class="empty">
            NO MEALS LOGGED FOR THIS DATE.
          </div>

          <div v-for="(r, idx) in dietRows" :key="r._key" class="trow dietRow">
            <select class="input" v-model="r.meal">
              <option value="">—</option>
              <option>breakfast</option>
              <option>lunch</option>
              <option>dinner</option>
              <option>snack</option>
              <option>drink</option>
              <option>other</option>
            </select>

            <input class="input" v-model="r.food" placeholder="e.g. rice + chicken" />

            <input class="input" type="number" v-model="r.calories" placeholder="e.g. 650" />

            <select class="input" v-model="r.confidence">
              <option value="">—</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>

            <button class="btn tiny danger" :disabled="isSaving" @click="removeDiet(idx)">
              DEL
            </button>
          </div>
        </div>

        <div class="panelFooter">
          <button class="btn ghost" @click="addDiet">+ ADD MEAL</button>
        </div>
      </div>

      <!-- WORKOUT -->
      <div class="panel wide">
        <div class="panelHeader">
          <div class="panelTitle">WORKOUTS</div>
          <div class="panelMeta">{{ workoutCaloriesMeta }}</div>
        </div>

        <div class="table">
          <div class="thead workoutHead">
            <div>WORKOUT</div>
            <div>CAL BURNT</div>
            <div></div>
          </div>

          <div v-if="workoutRows.length === 0" class="empty">
            NO WORKOUTS LOGGED FOR THIS DATE.
          </div>

          <div v-for="(r, idx) in workoutRows" :key="r._key" class="trow workoutRow">
            <input class="input" v-model="r.workout" placeholder="e.g. YMCA treadmill 35m" />
            <input class="input" type="number" v-model="r.calories_burnt" placeholder="e.g. 320" />
            <button class="btn tiny danger" :disabled="isSaving" @click="removeWorkout(idx)">
              DEL
            </button>
          </div>
        </div>

        <div class="panelFooter">
          <button class="btn ghost" @click="addWorkout">+ ADD WORKOUT</button>
        </div>
      </div>
      </template>

      <template v-else>
      <div class="panel wide">
        <div class="panelHeader">
          <div class="panelTitle">HEALTH DASHBOARD</div>
          <div class="panelMeta">LAST 7 DAYS (ENDING {{ healthDashboardEndDate }})</div>
        </div>

        <div v-if="dashLoading" class="empty">LOADING DASHBOARD...</div>

        <div v-else class="dashboard-stack">
          <div class="dashPanel wideDash">
            <div class="dashTitle">Weekly KPI Snapshot</div>
            <div class="dashSub">WEEK ENDING {{ selectedWeekEndLabel }} (VS PREVIOUS WEEK)</div>

            <div class="weeklyKpiGrid">
              <article
                v-for="card in weeklyKpiCards"
                :key="card.key"
                class="weeklyKpiCard"
                :class="card.tone"
              >
                <div class="weeklyKpiTitle">{{ card.title }}</div>
                <div class="weeklyKpiCurrent">{{ card.currentText }}</div>
                <div class="weeklyKpiMeta">PREVIOUS: {{ card.previousText }}</div>
                <div class="weeklyKpiMeta">DELTA: {{ card.deltaText }}</div>
              </article>
            </div>
          </div>

          <div class="dashPanel wideDash">
            <div class="dashTitle">Weekly Comparison</div>
            <div class="dashSub">LAST {{ weeklyHistoryRows.length || WEEKLY_HISTORY_WEEKS }} WEEKS</div>

            <div v-if="weeklyHistoryRows.length === 0" class="empty">NO WEEKLY HISTORY AVAILABLE.</div>

            <div v-else class="weeklyHistoryWrap">
              <table class="weeklyHistoryTable">
                <thead>
                  <tr>
                    <th>WEEK END</th>
                    <th>FOOD</th>
                    <th>DRINKS</th>
                    <th>BEER</th>
                    <th>EXERCISE</th>
                    <th>NET</th>
                    <th>AVG/DAY (IN/OUT)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in weeklyHistoryRows"
                    :key="`history-${row.week_start}`"
                  >
                    <td data-label="Week End">{{ formatDashboardDate(row.week_end) }}</td>
                    <td data-label="Food">{{ formatMetricValue(row.total_food_calories) }}</td>
                    <td data-label="Drinks">{{ formatMetricValue(row.total_drink_calories) }}</td>
                    <td data-label="Beer">{{ formatMetricValue(row.total_beer_calories) }}</td>
                    <td data-label="Exercise">{{ formatMetricValue(row.total_exercise_calories) }}</td>
                    <td data-label="Net">{{ formatMetricValue(row.net_calories) }}</td>
                    <td data-label="Avg/Day In/Out">{{ formatHistoryAvg(row.avg_daily_calories_in, row.avg_daily_calories_out) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

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
            <div class="dashTitle">Weight — Last 7 Days</div>
            <div class="dashSub">DAILY WEIGHT ENTRIES</div>

            <div class="dashTable weightTable">
              <div class="dashHead">
                <div>DATE</div>
                <div>WEIGHT</div>
              </div>

              <div
                v-for="entry in weightLast7"
                :key="`weight-${entry.date}`"
                class="dashRow"
              >
                <div>{{ formatDashboardDate(entry.date) }}</div>
                <div>{{ formatWeight(entry.weight) }}</div>
              </div>
            </div>
          </div>

          <div class="dashPanel wideDash">
            <div class="dashTitle">Blood Pressure — Recent</div>
            <div class="dashSub">LAST 7 ENTRIES</div>

            <div class="dashTable bpTable">
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
      </div>
      </template>

    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { shiftDate, toDateOnly } from "../utils/chartUtils";

const isLoading = ref(false);
const isSaving = ref(false);
const isSafetySaving = ref(false);

const status = ref("");
const statusType = ref("ok"); // ok | err

const selectedDate = ref(getLocalDateString());

// single/day values
const weightId = ref(null);
const weightValue = ref("");

const bpId = ref(null);
const bpSystolic = ref("");
const bpDiastolic = ref("");
const safetyMeetingCompleted = ref(false);

// multi/day values
const dietRows = ref([]);
const workoutRows = ref([]);
const HEALTH_DASHBOARD_DAYS = 30;
const CALORIES_WINDOW_DAYS = 7;
const WEEKLY_HISTORY_WEEKS = 8;
const showDashboard = ref(false);
const dashLoading = ref(false);
const dashboardSeries = ref([]);
const bpLast7 = ref([]);
const weeklySummary = ref(buildEmptyWeeklySummary());

function flash(msg, type = "ok") {
  status.value = msg;
  statusType.value = type;
  window.clearTimeout(flash._t);
  flash._t = window.setTimeout(() => (status.value = ""), 2200);
}

function getBaseUrl() {
  return import.meta.env.VITE_API_URL ?? "http://localhost:8000";
}

function getLocalDateString() {
  const d = new Date();
  return (
    d.getFullYear() +
    "-" +
    String(d.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(d.getDate()).padStart(2, "0")
  );
}

function todayDate() {
  return toDateOnly(new Date());
}

function weekStartFromDate(dateValue) {
  const dt = new Date(`${dateValue}T00:00:00`);
  if (Number.isNaN(dt.getTime())) {
    return dateValue;
  }

  const dayOfWeek = dt.getDay();
  const offsetToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  dt.setDate(dt.getDate() + offsetToMonday);
  return toDateOnly(dt);
}

function toNumberOrNull(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "string" && value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function buildEmptyWeeklyMetric() {
  return {
    current: null,
    previous_week_value: null,
    delta_from_previous_week: null,
  };
}

function buildEmptyWeeklySummary(weekStart = null) {
  return {
    week_start: weekStart,
    week_end: null,
    total_food_calories: buildEmptyWeeklyMetric(),
    total_drink_calories: buildEmptyWeeklyMetric(),
    total_beer_calories: buildEmptyWeeklyMetric(),
    total_exercise_calories: buildEmptyWeeklyMetric(),
    net_calories: buildEmptyWeeklyMetric(),
    avg_daily_calories_in: buildEmptyWeeklyMetric(),
    avg_daily_calories_out: buildEmptyWeeklyMetric(),
    days_since_last_safety_meeting: null,
    weekly_history: [],
  };
}

function normalizeWeeklyMetric(metric) {
  return {
    current: toNumberOrNull(metric?.current),
    previous_week_value: toNumberOrNull(metric?.previous_week_value),
    delta_from_previous_week: toNumberOrNull(metric?.delta_from_previous_week),
  };
}

function normalizeWeeklyHistoryRow(row) {
  return {
    week_start: row?.week_start ?? "",
    week_end: row?.week_end ?? "",
    total_food_calories: toNumberOrNull(row?.total_food_calories),
    total_drink_calories: toNumberOrNull(row?.total_drink_calories),
    total_beer_calories: toNumberOrNull(row?.total_beer_calories),
    total_exercise_calories: toNumberOrNull(row?.total_exercise_calories),
    net_calories: toNumberOrNull(row?.net_calories),
    avg_daily_calories_in: toNumberOrNull(row?.avg_daily_calories_in),
    avg_daily_calories_out: toNumberOrNull(row?.avg_daily_calories_out),
  };
}

function normalizeWeeklySummary(payload, fallbackWeekStart = null) {
  const base = buildEmptyWeeklySummary(fallbackWeekStart);
  if (!payload || typeof payload !== "object") return base;

  return {
    week_start: payload?.week_start ?? fallbackWeekStart,
    week_end: payload?.week_end ?? null,
    total_food_calories: normalizeWeeklyMetric(payload?.total_food_calories),
    total_drink_calories: normalizeWeeklyMetric(payload?.total_drink_calories),
    total_beer_calories: normalizeWeeklyMetric(payload?.total_beer_calories),
    total_exercise_calories: normalizeWeeklyMetric(payload?.total_exercise_calories),
    net_calories: normalizeWeeklyMetric(payload?.net_calories),
    avg_daily_calories_in: normalizeWeeklyMetric(payload?.avg_daily_calories_in),
    avg_daily_calories_out: normalizeWeeklyMetric(payload?.avg_daily_calories_out),
    days_since_last_safety_meeting: toNumberOrNull(payload?.days_since_last_safety_meeting),
    weekly_history: Array.isArray(payload?.weekly_history)
      ? payload.weekly_history.map(normalizeWeeklyHistoryRow)
      : [],
  };
}

function formatMetricValue(value, fallback = "N/A") {
  const n = toNumberOrNull(value);
  if (n === null) return fallback;
  return Math.round(n).toLocaleString();
}

function formatDeltaValue(value) {
  const n = toNumberOrNull(value);
  if (n === null) return "N/A";
  const rounded = Math.round(n);
  const sign = rounded > 0 ? "+" : "";
  return `${sign}${rounded.toLocaleString()}`;
}

function formatHistoryAvg(avgIn, avgOut) {
  return `${formatMetricValue(avgIn)} / ${formatMetricValue(avgOut)}`;
}

function safetyMeetingTone(daysSince) {
  const n = toNumberOrNull(daysSince);
  if (n === null) return "";
  if (n < 3) return "warn";
  if (n > 14) return "good";
  return "";
}

function getRowDate(row) {
  return String(row?.date ?? row?.entry_date ?? "");
}

function sortRowsByDate(rows) {
  return [...rows].sort((a, b) => getRowDate(a).localeCompare(getRowDate(b)));
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

function formatWeight(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${n.toFixed(1)} lb`;
}

function mkKey() {
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function normalizeDietRow(r) {
  return {
    id: r?.id ?? null,
    _key: mkKey(),
    meal: r?.meal ?? "",
    food: r?.food ?? "",
    calories: r?.calories ?? "",
    confidence: r?.confidence ?? "",
  };
}

function normalizeWorkoutRow(r) {
  return {
    id: r?.id ?? null,
    _key: mkKey(),
    workout: r?.workout ?? "",
    calories_burnt: r?.calories_burnt ?? "",
  };
}

async function loadDay() {
  if (isLoading.value) return;
  isLoading.value = true;
  status.value = "";

  try {
    const baseUrl = getBaseUrl();
    const date = selectedDate.value;

    const res = await fetch(`${baseUrl}/health/day?date=${encodeURIComponent(date)}`);
    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const data = await res.json();

    weightId.value = data?.weight?.id ?? null;
    weightValue.value = data?.weight?.weight ?? "";

    bpId.value = data?.blood_pressure?.id ?? null;
    bpSystolic.value = data?.blood_pressure?.systolic ?? "";
    bpDiastolic.value = data?.blood_pressure?.diastolic ?? "";

    dietRows.value = Array.isArray(data?.diet) ? data.diet.map(normalizeDietRow) : [];
    workoutRows.value = Array.isArray(data?.workouts) ? data.workouts.map(normalizeWorkoutRow) : [];
  } catch (e) {
    flash(`LOAD ERROR: ${e.message}`, "err");
  } finally {
    isLoading.value = false;
  }
}

async function loadSafetyMeeting() {
  try {
    const baseUrl = getBaseUrl();
    const date = selectedDate.value;

    const res = await fetch(`${baseUrl}/health/safety-meeting?date=${encodeURIComponent(date)}`);
    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const data = await res.json();
    safetyMeetingCompleted.value = Boolean(data?.completed);
  } catch (e) {
    flash(`SAFETY LOAD ERROR: ${e.message}`, "err");
  }
}

async function loadDashboard() {
  if (dashLoading.value) return;
  dashLoading.value = true;

  try {
    const baseUrl = getBaseUrl();
    const end = selectedDate.value || todayDate();
    const selectedWeekStart = weekStartFromDate(end);
    const [healthResult, weeklyResult] = await Promise.allSettled([
      fetch(`${baseUrl}/health/dashboard?end_date=${encodeURIComponent(end)}&days=${HEALTH_DASHBOARD_DAYS}`),
      fetch(
        `${baseUrl}/stats/weekly-life-summary?view=dashboard&week_start=${encodeURIComponent(selectedWeekStart)}&history_weeks=${WEEKLY_HISTORY_WEEKS}`
      ),
    ]);

    if (healthResult.status === "fulfilled" && healthResult.value.ok) {
      const payload = await healthResult.value.json();
      const series = Array.isArray(payload?.series) ? payload.series : [];
      dashboardSeries.value = sortRowsByDate(series.length ? series : buildEmptyHealthSeries(end, HEALTH_DASHBOARD_DAYS));
      bpLast7.value = Array.isArray(payload?.bp_last_7) ? payload.bp_last_7 : [];
    } else {
      dashboardSeries.value = buildEmptyHealthSeries(end, HEALTH_DASHBOARD_DAYS);
      bpLast7.value = [];
    }

    if (weeklyResult.status === "fulfilled" && weeklyResult.value.ok) {
      const payload = await weeklyResult.value.json();
      weeklySummary.value = normalizeWeeklySummary(payload, selectedWeekStart);
    } else {
      weeklySummary.value = buildEmptyWeeklySummary(selectedWeekStart);
    }
  } catch (e) {
    const end = selectedDate.value || todayDate();
    dashboardSeries.value = buildEmptyHealthSeries(end, HEALTH_DASHBOARD_DAYS);
    bpLast7.value = [];
    weeklySummary.value = buildEmptyWeeklySummary(weekStartFromDate(end));
    flash(`DASHBOARD LOAD ERROR: ${e.message}`, "err");
  } finally {
    dashLoading.value = false;
  }
}

async function toggleStatsView() {
  if (showDashboard.value) {
    showDashboard.value = false;
    return;
  }

  showDashboard.value = true;
  await loadDashboard();
}

async function loadAll() {
  await loadDay();
  await loadSafetyMeeting();
  if (showDashboard.value) {
    await loadDashboard();
  }
}

function addDiet() {
  dietRows.value.push(normalizeDietRow({}));
}

function addWorkout() {
  workoutRows.value.push(normalizeWorkoutRow({}));
}

async function removeDiet(idx) {
  const row = dietRows.value[idx];
  if (row?.id) {
    try {
      const baseUrl = getBaseUrl();
      const res = await fetch(`${baseUrl}/health/diet/${row.id}`, { method: "DELETE" });
      if (!res.ok) {
        const msg = await res.text().catch(() => "");
        throw new Error(msg || `HTTP ${res.status}`);
      }
      dietRows.value.splice(idx, 1);
      flash("DIET ENTRY DELETED");
      if (showDashboard.value) {
        await loadDashboard();
      }
      return;
    } catch (e) {
      flash(`DELETE ERROR: ${e.message}`, "err");
      return;
    }
  }
  dietRows.value.splice(idx, 1);
}

async function removeWorkout(idx) {
  const row = workoutRows.value[idx];
  if (row?.id) {
    try {
      const baseUrl = getBaseUrl();
      const res = await fetch(`${baseUrl}/health/workout/${row.id}`, { method: "DELETE" });
      if (!res.ok) {
        const msg = await res.text().catch(() => "");
        throw new Error(msg || `HTTP ${res.status}`);
      }
      workoutRows.value.splice(idx, 1);
      flash("WORKOUT DELETED");
      if (showDashboard.value) {
        await loadDashboard();
      }
      return;
    } catch (e) {
      flash(`DELETE ERROR: ${e.message}`, "err");
      return;
    }
  }
  workoutRows.value.splice(idx, 1);
}

function cleanedDietPayload() {
  return dietRows.value
    .map((r) => ({
      id: r.id ?? null,
      meal: (r.meal ?? "").trim() || null,
      food: (r.food ?? "").trim() || null,
      calories: r.calories === "" || r.calories === null ? null : Number(r.calories),
      confidence: (r.confidence ?? "").trim() || null,
    }))
    .filter((r) => r.meal || r.food || r.calories !== null || r.confidence);
}

function cleanedWorkoutPayload() {
  return workoutRows.value
    .map((r) => ({
      id: r.id ?? null,
      workout: (r.workout ?? "").trim() || null,
      calories_burnt: r.calories_burnt === "" || r.calories_burnt === null ? null : Number(r.calories_burnt),
    }))
    .filter((r) => r.workout || r.calories_burnt !== null);
}

const dietTotalCalories = computed(() =>
  dietRows.value.reduce((sum, row) => {
    const value = Number(row?.calories);
    return sum + (Number.isFinite(value) ? value : 0);
  }, 0)
);

const workoutTotalCalories = computed(() =>
  workoutRows.value.reduce((sum, row) => {
    const value = Number(row?.calories_burnt);
    return sum + (Number.isFinite(value) ? value : 0);
  }, 0)
);

const dietCaloriesMeta = computed(() => `TOTAL CALORIES: ${Math.round(dietTotalCalories.value).toLocaleString()}`);
const workoutCaloriesMeta = computed(() => `TOTAL CAL BURNT: ${Math.round(workoutTotalCalories.value).toLocaleString()}`);
const orderedDashboardSeries = computed(() => sortRowsByDate(dashboardSeries.value));
const caloriesLast7 = computed(() => {
  const lastSeven = orderedDashboardSeries.value.slice(-CALORIES_WINDOW_DAYS);
  return [...lastSeven].sort((a, b) => String(b.date ?? "").localeCompare(String(a.date ?? "")));
});
const weightLast7 = computed(() => {
  const lastSeven = orderedDashboardSeries.value.slice(-CALORIES_WINDOW_DAYS);
  return [...lastSeven].sort((a, b) => String(b.date ?? "").localeCompare(String(a.date ?? "")));
});
const totalIn = computed(() => caloriesLast7.value.reduce((sum, row) => sum + Number(row?.calories_in ?? 0), 0));
const totalOut = computed(() => caloriesLast7.value.reduce((sum, row) => sum + Number(row?.calories_out ?? 0), 0));
const totalNet = computed(() => caloriesLast7.value.reduce((sum, row) => sum + Number(row?.calories_net ?? 0), 0));
const healthDashboardEndDate = computed(() => {
  const latest = orderedDashboardSeries.value[orderedDashboardSeries.value.length - 1];
  if (!latest) return formatDashboardDate(selectedDate.value || todayDate());
  return formatDashboardDate(latest.date);
});
const selectedWeekEndLabel = computed(() => {
  const explicitWeekEnd = weeklySummary.value?.week_end;
  if (explicitWeekEnd) return formatDashboardDate(explicitWeekEnd);

  const weekStart = weekStartFromDate(selectedDate.value || todayDate());
  return formatDashboardDate(shiftDate(weekStart, 6));
});
const weeklyHistoryRows = computed(() =>
  Array.isArray(weeklySummary.value?.weekly_history)
    ? weeklySummary.value.weekly_history.slice(0, WEEKLY_HISTORY_WEEKS)
    : []
);
const weeklyKpiCards = computed(() => {
  const summary = weeklySummary.value || buildEmptyWeeklySummary();
  return [
    {
      key: "food",
      title: "Food Calories",
      currentText: formatMetricValue(summary.total_food_calories?.current),
      previousText: formatMetricValue(summary.total_food_calories?.previous_week_value),
      deltaText: formatDeltaValue(summary.total_food_calories?.delta_from_previous_week),
      tone: "",
    },
    {
      key: "drinks",
      title: "Drink Calories",
      currentText: formatMetricValue(summary.total_drink_calories?.current),
      previousText: formatMetricValue(summary.total_drink_calories?.previous_week_value),
      deltaText: formatDeltaValue(summary.total_drink_calories?.delta_from_previous_week),
      tone: "",
    },
    {
      key: "beer",
      title: "Beer Calories",
      currentText: formatMetricValue(summary.total_beer_calories?.current),
      previousText: formatMetricValue(summary.total_beer_calories?.previous_week_value),
      deltaText: formatDeltaValue(summary.total_beer_calories?.delta_from_previous_week),
      tone: "",
    },
    {
      key: "exercise",
      title: "Exercise Calories",
      currentText: formatMetricValue(summary.total_exercise_calories?.current),
      previousText: formatMetricValue(summary.total_exercise_calories?.previous_week_value),
      deltaText: formatDeltaValue(summary.total_exercise_calories?.delta_from_previous_week),
      tone: "",
    },
    {
      key: "net",
      title: "Net Calories",
      currentText: formatMetricValue(summary.net_calories?.current),
      previousText: formatMetricValue(summary.net_calories?.previous_week_value),
      deltaText: formatDeltaValue(summary.net_calories?.delta_from_previous_week),
      tone: "",
    },
    {
      key: "avg-in",
      title: "Avg Daily Calories In",
      currentText: formatMetricValue(summary.avg_daily_calories_in?.current),
      previousText: formatMetricValue(summary.avg_daily_calories_in?.previous_week_value),
      deltaText: formatDeltaValue(summary.avg_daily_calories_in?.delta_from_previous_week),
      tone: "",
    },
    {
      key: "avg-out",
      title: "Avg Daily Calories Out",
      currentText: formatMetricValue(summary.avg_daily_calories_out?.current),
      previousText: formatMetricValue(summary.avg_daily_calories_out?.previous_week_value),
      deltaText: formatDeltaValue(summary.avg_daily_calories_out?.delta_from_previous_week),
      tone: "",
    },
    {
      key: "safety",
      title: "Days Since Last Safety Meeting",
      currentText: formatMetricValue(summary.days_since_last_safety_meeting),
      previousText: "N/A",
      deltaText: "N/A",
      tone: safetyMeetingTone(summary.days_since_last_safety_meeting),
    },
  ];
});
const recentBpEntries = computed(() => bpLast7.value.slice(0, 7));

async function saveSafetyMeeting(options = {}) {
  const { silentSuccess = false, throwOnError = false } = options;
  if (isSafetySaving.value) return;
  isSafetySaving.value = true;

  try {
    const baseUrl = getBaseUrl();
    const date = selectedDate.value;

    const res = await fetch(`${baseUrl}/health/safety-meeting?date=${encodeURIComponent(date)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ completed: Boolean(safetyMeetingCompleted.value) }),
    });

    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    if (!silentSuccess) {
      flash("SAFETY MEETING SAVED");
    }
  } catch (e) {
    if (throwOnError) {
      throw e;
    }
    flash(`SAFETY SAVE ERROR: ${e.message}`, "err");
  } finally {
    isSafetySaving.value = false;
  }
}

async function saveAll() {
  if (isSaving.value || isSafetySaving.value) return;
  isSaving.value = true;
  status.value = "";

  try {
    const baseUrl = getBaseUrl();
    const date = selectedDate.value;

    const payload = {
      weight: {
        id: weightId.value,
        entry_date: date,
        weight: weightValue.value === "" ? null : Number(weightValue.value),
      },
      blood_pressure: {
        id: bpId.value,
        entry_date: date,
        systolic: bpSystolic.value === "" ? null : Number(bpSystolic.value),
        diastolic: bpDiastolic.value === "" ? null : Number(bpDiastolic.value),
      },
      diet: cleanedDietPayload().map((d) => ({ ...d, log_date: date })),
      workouts: cleanedWorkoutPayload().map((w) => ({ ...w, workout_date: date })),
    };

    const res = await fetch(`${baseUrl}/health/day?date=${encodeURIComponent(date)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const updated = await res.json();

    weightId.value = updated?.weight?.id ?? weightId.value;
    bpId.value = updated?.blood_pressure?.id ?? bpId.value;

    dietRows.value = Array.isArray(updated?.diet) ? updated.diet.map(normalizeDietRow) : [];
    workoutRows.value = Array.isArray(updated?.workouts) ? updated.workouts.map(normalizeWorkoutRow) : [];

    await saveSafetyMeeting({ silentSuccess: true, throwOnError: true });

    flash("SAVED");
    if (showDashboard.value) {
      await loadDashboard();
    }
  } catch (e) {
    flash(`SAVE ERROR: ${e.message}`, "err");
  } finally {
    isSaving.value = false;
  }
}

onMounted(() => {
  loadAll();
});
</script>

<style scoped>
/* base terminal styles */

.screen { padding: var(--pad); position: relative; overflow: hidden; }
.scanlines { pointer-events: none; position: absolute; inset: 0; background: repeating-linear-gradient(to bottom, rgba(255,255,255,0.02), rgba(255,255,255,0.02) 1px, transparent 1px, transparent 3px); mix-blend-mode: overlay; opacity: 0.35; }
.vignette { pointer-events: none; position: absolute; inset: -40px; background: radial-gradient(circle at center, transparent 0%, rgba(0,0,0,0.55) 70%); opacity: 0.55; }

.header { position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); padding-bottom: 14px; margin-bottom: 16px; }
.title { margin: 0; font-size: clamp(28px, 4vw, 52px); letter-spacing: 0.12em; text-transform: uppercase; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; align-items: flex-end; }

.status { position: relative; border: 1px solid var(--line); border-radius: var(--radius); padding: 10px 12px; margin-bottom: 14px; letter-spacing: 0.08em; text-transform: uppercase; background: rgba(255,255,255,0.03); }
.status.err { border-color: rgba(255, 80, 80, 0.55); }

.grid { position: relative; display: grid; gap: 14px; grid-template-columns: repeat(12, 1fr); }
.panel { grid-column: span 6; border: 1px solid var(--line); border-radius: var(--radius); padding: 14px; background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); box-sizing: border-box; min-width: 0; }
.panel.wide { grid-column: span 12; }

.panelHeader { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 12px; }
.panelTitle { letter-spacing: 0.12em; text-transform: uppercase; }
.panelMeta { opacity: 0.75; letter-spacing: 0.08em; font-size: 12px; text-transform: uppercase; }

.row { display: grid; gap: 12px; align-items: end; }
.rowWeight { grid-template-columns: minmax(0, 1fr) auto; }
.rowBP { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto; }
.rowSafety { grid-template-columns: minmax(0, 1fr) auto; align-items: center; }

.toggleRowLabel { display: inline-flex; align-items: center; gap: 10px; cursor: pointer; }
.toggleInput { width: 18px; height: 18px; accent-color: rgba(255, 255, 255, 0.9); cursor: pointer; }
.toggleText { letter-spacing: 0.1em; text-transform: uppercase; font-size: 13px; }

.field { display: grid; gap: 6px; min-width: 0; }
.field.inline { min-width: 220px; }
.label { font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; opacity: 0.85; }

.input { width: 100%; background: transparent; color: var(--fg); border: 1px solid var(--line2); border-radius: calc(var(--radius) - 4px); padding: 10px 12px; outline: none; box-sizing: border-box; min-width: 0; text-transform: none;}
.input:focus { border-color: var(--line); box-shadow: 0 0 0 2px rgba(255,255,255,0.06); }

.btn { border: 1px solid var(--line); background: rgba(255,255,255,0.06); color: var(--fg); border-radius: 10px; padding: 10px 12px; letter-spacing: 0.12em; text-transform: uppercase; cursor: pointer; box-sizing: border-box; white-space: nowrap; }
.btn.ghost { background: transparent; border-color: var(--line2); }
.btn.active { background: rgba(255,255,255,0.12); border-color: var(--line); }
.btn.small { padding: 10px 12px; }
.btn.tiny { padding: 8px 10px; border-radius: 10px; }
.btn.danger { border-color: rgba(255,80,80,0.55); background: rgba(255,80,80,0.08); }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }

.table { display: grid; gap: 10px; }
.thead { display: grid; grid-template-columns: minmax(0,160px) minmax(0,1fr) minmax(0,110px) minmax(0,110px) 70px; gap: 12px; padding: 10px 10px; border: 1px solid var(--line2); border-radius: 10px; opacity: 0.85; letter-spacing: 0.12em; text-transform: uppercase; font-size: 12px; box-sizing: border-box; }
.trow { display: grid; grid-template-columns: minmax(0,160px) minmax(0,1fr) minmax(0,110px) minmax(0,110px) 70px; gap: 12px; align-items: center; min-width: 0; }
.workoutHead { grid-template-columns: minmax(0,1fr) minmax(0,150px) 70px; }
.workoutRow { grid-template-columns: minmax(0,1fr) minmax(0,150px) 70px; }
.empty { padding: 12px; border: 1px dashed var(--line2); border-radius: 10px; opacity: 0.8; letter-spacing: 0.1em; text-transform: uppercase; font-size: 12px; }
.panelFooter { margin-top: 12px; display: flex; justify-content: flex-start; }

.dashboard-stack {
  display: grid;
  gap: 14px;
}

.dashPanel {
  border: 1px solid var(--line2);
  border-radius: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  min-width: 0;
}

.weeklyKpiGrid {
  margin-top: 10px;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.weeklyKpiCard {
  border: 1px solid var(--line2);
  border-radius: 10px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.02);
  display: grid;
  gap: 4px;
}

.weeklyKpiCard.warn {
  border-color: rgba(255, 110, 110, 0.55);
  background: rgba(255, 110, 110, 0.09);
}

.weeklyKpiCard.good {
  border-color: rgba(120, 220, 140, 0.55);
  background: rgba(120, 220, 140, 0.08);
}

.weeklyKpiTitle {
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  opacity: 0.85;
}

.weeklyKpiCurrent {
  font-size: clamp(20px, 3vw, 32px);
  line-height: 1.1;
}

.weeklyKpiMeta {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.76;
}

.weeklyHistoryWrap {
  margin-top: 10px;
  width: 100%;
  overflow-x: auto;
  min-width: 0;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
}

.weeklyHistoryTable {
  width: 100%;
  border-collapse: collapse;
  min-width: 700px;
}

.weeklyHistoryTable th,
.weeklyHistoryTable td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid var(--line2);
  white-space: nowrap;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.weeklyHistoryTable th {
  opacity: 0.82;
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
  min-width: 0;
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

@media (max-width: 980px) {
  .panel { grid-column: span 12; }
}

@media (max-width: 760px) {
  .dashHead {
    display: none;
  }

  .dashRow {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    padding: 8px 10px;
    align-items: center;
  }

  .calRow {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-template-areas:
      "date date date"
      "in out net";
    gap: 6px;
    align-items: start;
  }

  .calRow > :nth-child(1) { grid-area: date; }
  .calRow > :nth-child(2) { grid-area: in; }
  .calRow > :nth-child(3) { grid-area: out; }
  .calRow > :nth-child(4) { grid-area: net; }

  .calRow > :nth-child(2)::before {
    content: "IN";
    display: block;
    font-size: 10px;
    opacity: 0.72;
    letter-spacing: 0.08em;
  }

  .calRow > :nth-child(3)::before {
    content: "OUT";
    display: block;
    font-size: 10px;
    opacity: 0.72;
    letter-spacing: 0.08em;
  }

  .calRow > :nth-child(4)::before {
    content: "NET";
    display: block;
    font-size: 10px;
    opacity: 0.72;
    letter-spacing: 0.08em;
  }

  .weightTable .dashRow > :nth-child(2)::before {
    content: "WEIGHT";
    display: block;
    font-size: 10px;
    opacity: 0.72;
    letter-spacing: 0.08em;
  }

  .bpTable .dashRow > :nth-child(2)::before {
    content: "BP";
    display: block;
    font-size: 10px;
    opacity: 0.72;
    letter-spacing: 0.08em;
  }

  .weeklyHistoryWrap {
    touch-action: pan-x;
  }

  .weeklyHistoryTable {
    min-width: 620px;
  }

  .weeklyHistoryTable th,
  .weeklyHistoryTable td {
    padding: 7px 8px;
    font-size: 11px;
    letter-spacing: 0.05em;
  }

  .weeklyHistoryTable th:nth-child(1),
  .weeklyHistoryTable td:nth-child(1) {
    min-width: 72px;
  }

  .weeklyHistoryTable th:nth-child(2),
  .weeklyHistoryTable td:nth-child(2),
  .weeklyHistoryTable th:nth-child(3),
  .weeklyHistoryTable td:nth-child(3),
  .weeklyHistoryTable th:nth-child(4),
  .weeklyHistoryTable td:nth-child(4),
  .weeklyHistoryTable th:nth-child(5),
  .weeklyHistoryTable td:nth-child(5),
  .weeklyHistoryTable th:nth-child(6),
  .weeklyHistoryTable td:nth-child(6) {
    min-width: 64px;
  }

  .weeklyHistoryTable th:nth-child(7),
  .weeklyHistoryTable td:nth-child(7) {
    min-width: 120px;
  }

  .dietHead {
    display: none;
  }

  .dietRow {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-areas:
      "meal meal"
      "food food"
      "cal conf"
      "del del";
    gap: 10px;
    border: 1px solid var(--line2);
    border-radius: 10px;
    padding: 10px;
  }

  .dietRow > :nth-child(1) { grid-area: meal; }
  .dietRow > :nth-child(2) { grid-area: food; }
  .dietRow > :nth-child(3) { grid-area: cal; }
  .dietRow > :nth-child(4) { grid-area: conf; }
  .dietRow > :nth-child(5) {
    grid-area: del;
    justify-self: end;
  }
}

@media (max-width: 430px) {
  .weeklyKpiGrid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .weeklyKpiCard {
    padding: 7px;
  }

  .weeklyKpiTitle,
  .weeklyKpiMeta {
    font-size: 10px;
  }

  .weeklyKpiCurrent {
    font-size: 16px;
  }

  .weeklyHistoryTable {
    min-width: 590px;
  }

  .weeklyHistoryTable th,
  .weeklyHistoryTable td {
    padding: 6px 7px;
    font-size: 10px;
  }

  .calRow {
    font-size: 12px;
  }

  .calRow > div,
  .dashRow > div {
    min-width: 0;
  }
}

</style>
