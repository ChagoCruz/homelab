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

        <button class="btn" :disabled="isSaving || isSafetySaving" @click="saveAll">
          {{ isSaving ? "SAVING..." : "SAVE ALL" }}
        </button>

        <button class="btn ghost" :disabled="isLoading" @click="loadAll">
          {{ isLoading ? "LOADING..." : "REFRESH" }}
        </button>
      </div>
    </header>

    <div v-if="status" class="status" :class="{ ok: statusType === 'ok', err: statusType === 'err' }">
      {{ status }}
    </div>

    <section class="grid">
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

      <!-- DETAILED ANALYTICS -->
      <div class="panel wide">
        <div class="panelHeader">
          <div class="panelTitle">DETAILED ANALYTICS</div>
          <div class="panelMeta">{{ analyticsRangeLabel }}</div>
        </div>

        <div class="analyticsControls">
          <span class="analyticsLabel">RANGE</span>
          <button
            v-for="days in [14, 21, 30]"
            :key="`analytics-${days}`"
            type="button"
            class="btn ghost tiny"
            :class="{ active: analyticsDays === days }"
            :disabled="analyticsLoading"
            @click="setAnalyticsDays(days)"
          >
            {{ days }}D
          </button>
        </div>

        <div class="analyticsStack">
          <MoodOverlayChart :rows="analyticsFacts" :loading="analyticsLoading" :error="analyticsError" />
          <CaloriesWorkoutChart :rows="analyticsFacts" :loading="analyticsLoading" :error="analyticsError" />
          <MoodWeatherHeatmap :rows="analyticsFacts" :loading="analyticsLoading" :error="analyticsError" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import CaloriesWorkoutChart from "../components/CaloriesWorkoutChart.vue";
import MoodOverlayChart from "../components/MoodOverlayChart.vue";
import MoodWeatherHeatmap from "../components/MoodWeatherHeatmap.vue";
import { shiftDate } from "../utils/chartUtils";

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

// analytics
const analyticsLoading = ref(false);
const analyticsError = ref("");
const analyticsDays = ref(21);
const analyticsFacts = ref([]);

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

const analyticsStartDate = computed(() =>
  shiftDate(selectedDate.value, -(analyticsDays.value - 1))
);

const analyticsRangeLabel = computed(
  () => `LAST ${analyticsDays.value} DAYS (${analyticsStartDate.value} → ${selectedDate.value})`
);

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

async function loadAnalytics() {
  if (analyticsLoading.value) return;
  analyticsLoading.value = true;
  analyticsError.value = "";

  try {
    const baseUrl = getBaseUrl();
    const url = new URL(`${baseUrl}/stats/daily-life-facts`);
    url.searchParams.set("start_date", analyticsStartDate.value);
    url.searchParams.set("end_date", selectedDate.value);

    const res = await fetch(url.toString());
    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const payload = await res.json();
    analyticsFacts.value = Array.isArray(payload) ? payload : [];
  } catch (e) {
    analyticsFacts.value = [];
    analyticsError.value = `ANALYTICS ERROR: ${e.message}`;
  } finally {
    analyticsLoading.value = false;
  }
}

function setAnalyticsDays(days) {
  if (analyticsLoading.value || analyticsDays.value === days) return;
  analyticsDays.value = days;
  loadAnalytics();
}

async function loadAll() {
  await loadDay();
  await loadSafetyMeeting();
  await loadAnalytics();
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
      await loadAnalytics();
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
      await loadAnalytics();
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
    await loadAnalytics();
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
/* base terminal styles + analytics layout */

.screen { padding: var(--pad); position: relative; overflow: hidden; }
.scanlines { pointer-events: none; position: absolute; inset: 0; background: repeating-linear-gradient(to bottom, rgba(255,255,255,0.02), rgba(255,255,255,0.02) 1px, transparent 1px, transparent 3px); mix-blend-mode: overlay; opacity: 0.35; }
.vignette { pointer-events: none; position: absolute; inset: -40px; background: radial-gradient(circle at center, transparent 0%, rgba(0,0,0,0.55) 70%); opacity: 0.55; }

.header { position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); padding-bottom: 14px; margin-bottom: 16px; }
.title { margin: 0; font-size: clamp(28px, 4vw, 52px); letter-spacing: 0.12em; text-transform: uppercase; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; align-items: flex-end; }

.status { position: relative; border: 1px solid var(--line); border-radius: var(--radius); padding: 10px 12px; margin-bottom: 14px; letter-spacing: 0.08em; text-transform: uppercase; background: rgba(255,255,255,0.03); }
.status.err { border-color: rgba(255, 80, 80, 0.55); }

.grid { position: relative; display: grid; gap: 14px; grid-template-columns: repeat(12, 1fr); }
.panel { grid-column: span 6; border: 1px solid var(--line); border-radius: var(--radius); padding: 14px; background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); box-sizing: border-box; }
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

/* ANALYTICS styles */
.analyticsControls {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.analyticsLabel {
  opacity: 0.75;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-size: 12px;
}

.btn.active {
  border-color: var(--line);
  background: rgba(255, 255, 255, 0.08);
}

.analyticsStack {
  display: grid;
  gap: 12px;
}

@media (max-width: 980px) {
  .panel { grid-column: span 12; }
}

@media (max-width: 760px) {
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

</style>
