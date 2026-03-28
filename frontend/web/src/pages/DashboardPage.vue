<template>
  <main class="page-shell">
    <section class="panel">
      <div class="panel-header">
        <h1>homelab</h1>
        <span class="panel-subtle">main dashboard</span>
      </div>

      <div class="dashboard-grid">
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
              <span class="kv-key">weather summary</span>
              <span class="kv-value">{{ displayWeatherValue(latestWeather?.weather_summary) }}</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">temp max</span>
              <span class="kv-value">{{ displayWeatherValue(latestWeather?.temp_max_f, formatTemp) }}</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">temp min</span>
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

        <AIInsightPanel />

        <section class="panel-block">
          <div class="block-header">
            <h2>quick links</h2>
          </div>

          <div class="quick-links">
            <RouterLink to="/journal" class="terminal-link">journal</RouterLink>
            <RouterLink to="/bills" class="terminal-link">bills</RouterLink>
            <RouterLink to="/mileage" class="terminal-link">mileage</RouterLink>
          </div>
        </section>

        <section class="panel-block wide">
          <div class="block-header">
            <h2>charts</h2>
            <span class="block-meta">
              {{ statsLoading ? "loading daily stats..." : "daily trend view" }}
            </span>
          </div>

          <div class="range-controls">
            <div class="range-group">
              <span class="range-label">daily range</span>
              <label class="range-field">
                from
                <input type="date" v-model="dailyStartDate" />
              </label>
              <label class="range-field">
                to
                <input type="date" v-model="dailyEndDate" />
              </label>
            </div>

            <div class="range-actions">
              <button class="range-btn" type="button" :disabled="statsLoading" @click="fetchStats">
                {{ statsLoading ? "loading..." : "apply ranges" }}
              </button>
              <button class="range-btn ghost" type="button" :disabled="statsLoading" @click="resetRanges">
                reset
              </button>
            </div>
          </div>

          <div class="charts-grid">
            <article class="chart-card">
              <div class="chart-header">
                <h3>daily mood over time</h3>
                <span>{{ dailyRangeLabel }}</span>
              </div>

              <div v-if="dailyError" class="chart-empty">{{ dailyError }}</div>
              <div v-else-if="statsLoading && !dailyFacts.length" class="chart-empty">loading chart...</div>
              <div v-else-if="!dailyMoodChart.points.length" class="chart-empty">no daily mood data yet</div>
              <svg
                v-else
                class="chart-svg"
                :viewBox="chartViewBox"
                preserveAspectRatio="none"
                role="img"
                aria-label="daily mood over time"
              >
                <line
                  v-for="tick in dailyMoodChart.yTicks"
                  :key="`mood-y-${tick.y}`"
                  class="grid-line"
                  :x1="chartFrame.padLeft"
                  :x2="chartFrame.width - chartFrame.padRight"
                  :y1="tick.y"
                  :y2="tick.y"
                />

                <path
                  v-for="(segment, idx) in dailyMoodChart.segments"
                  :key="`mood-segment-${idx}`"
                  class="line-mood"
                  :d="segment"
                />

                <template v-for="point in dailyMoodChart.points" :key="`mood-point-${point.index}`">
                  <circle
                    v-if="point.value !== null"
                    class="point point-mood"
                    :cx="point.x"
                    :cy="point.y"
                    r="2.5"
                  />
                </template>

                <text
                  v-for="tick in dailyMoodChart.yTicks"
                  :key="`mood-y-label-${tick.y}`"
                  class="axis-label"
                  :x="chartFrame.padLeft - 4"
                  :y="tick.y + 4"
                  text-anchor="end"
                >
                  {{ tick.label }}
                </text>

                <text
                  v-for="tick in dailyMoodChart.xTicks"
                  :key="`mood-x-label-${tick.x}`"
                  class="axis-label axis-label-x"
                  :x="tick.x"
                  :y="chartFrame.height - 8"
                  :text-anchor="tick.anchor"
                >
                  {{ tick.label }}
                </text>
              </svg>
            </article>

            <article class="chart-card">
              <div class="chart-header">
                <h3>daily mood with alcohol markers</h3>
                <span>{{ dailyAlcoholMarkers.length }} marker(s)</span>
              </div>

              <div v-if="dailyError" class="chart-empty">{{ dailyError }}</div>
              <div v-else-if="statsLoading && !dailyFacts.length" class="chart-empty">loading chart...</div>
              <div v-else-if="!dailyMoodChart.points.length" class="chart-empty">no daily mood data yet</div>
              <svg
                v-else
                class="chart-svg"
                :viewBox="chartViewBox"
                preserveAspectRatio="none"
                role="img"
                aria-label="daily mood with alcohol markers"
              >
                <line
                  v-for="tick in dailyMoodChart.yTicks"
                  :key="`mood-alcohol-y-${tick.y}`"
                  class="grid-line"
                  :x1="chartFrame.padLeft"
                  :x2="chartFrame.width - chartFrame.padRight"
                  :y1="tick.y"
                  :y2="tick.y"
                />

                <path
                  v-for="(segment, idx) in dailyMoodChart.segments"
                  :key="`mood-alcohol-segment-${idx}`"
                  class="line-mood"
                  :d="segment"
                />

                <template v-for="point in dailyMoodChart.points" :key="`mood-alcohol-point-${point.index}`">
                  <circle
                    v-if="point.value !== null"
                    class="point point-muted"
                    :cx="point.x"
                    :cy="point.y"
                    r="2"
                  />
                </template>

                <g v-for="marker in dailyAlcoholMarkers" :key="marker.id">
                  <circle class="marker marker-alcohol" :cx="marker.x" :cy="marker.y" r="5" />
                  <title>had alcohol</title>
                </g>

                <text
                  v-for="tick in dailyMoodChart.yTicks"
                  :key="`mood-alcohol-y-label-${tick.y}`"
                  class="axis-label"
                  :x="chartFrame.padLeft - 4"
                  :y="tick.y + 4"
                  text-anchor="end"
                >
                  {{ tick.label }}
                </text>

                <text
                  v-for="tick in dailyMoodChart.xTicks"
                  :key="`mood-alcohol-x-label-${tick.x}`"
                  class="axis-label axis-label-x"
                  :x="tick.x"
                  :y="chartFrame.height - 8"
                  :text-anchor="tick.anchor"
                >
                  {{ tick.label }}
                </text>
              </svg>

              <div class="legend-row">
                <span class="legend-pill legend-alcohol">alcohol day</span>
              </div>
            </article>

            <article class="chart-card">
              <div class="chart-header">
                <h3>daily mood with safety meeting markers</h3>
                <span>{{ dailySafetyMarkers.length }} marker(s)</span>
              </div>

              <div v-if="dailyError" class="chart-empty">{{ dailyError }}</div>
              <div v-else-if="statsLoading && !dailyFacts.length" class="chart-empty">loading chart...</div>
              <div v-else-if="!dailyMoodChart.points.length" class="chart-empty">no daily mood data yet</div>
              <svg
                v-else
                class="chart-svg"
                :viewBox="chartViewBox"
                preserveAspectRatio="none"
                role="img"
                aria-label="daily mood with safety meeting markers"
              >
                <line
                  v-for="tick in dailyMoodChart.yTicks"
                  :key="`mood-safety-y-${tick.y}`"
                  class="grid-line"
                  :x1="chartFrame.padLeft"
                  :x2="chartFrame.width - chartFrame.padRight"
                  :y1="tick.y"
                  :y2="tick.y"
                />

                <path
                  v-for="(segment, idx) in dailyMoodChart.segments"
                  :key="`mood-safety-segment-${idx}`"
                  class="line-mood"
                  :d="segment"
                />

                <template v-for="point in dailyMoodChart.points" :key="`mood-safety-point-${point.index}`">
                  <circle
                    v-if="point.value !== null"
                    class="point point-muted"
                    :cx="point.x"
                    :cy="point.y"
                    r="2"
                  />
                </template>

                <g v-for="marker in dailySafetyMarkers" :key="marker.id">
                  <rect class="marker marker-safety" :x="marker.x - 4.5" :y="marker.y - 4.5" width="9" height="9" />
                  <title>safety meeting completed</title>
                </g>

                <text
                  v-for="tick in dailyMoodChart.yTicks"
                  :key="`mood-safety-y-label-${tick.y}`"
                  class="axis-label"
                  :x="chartFrame.padLeft - 4"
                  :y="tick.y + 4"
                  text-anchor="end"
                >
                  {{ tick.label }}
                </text>

                <text
                  v-for="tick in dailyMoodChart.xTicks"
                  :key="`mood-safety-x-label-${tick.x}`"
                  class="axis-label axis-label-x"
                  :x="tick.x"
                  :y="chartFrame.height - 8"
                  :text-anchor="tick.anchor"
                >
                  {{ tick.label }}
                </text>
              </svg>

              <div class="legend-row">
                <span class="legend-pill legend-safety">safety meeting day</span>
              </div>
            </article>

            <article class="chart-card">
              <div class="chart-header">
                <h3>calories vs workout calories</h3>
                <span>{{ dailyRangeLabel }}</span>
              </div>

              <div v-if="dailyError" class="chart-empty">{{ dailyError }}</div>
              <div v-else-if="statsLoading && !dailyFacts.length" class="chart-empty">loading chart...</div>
              <div v-else-if="!caloriesChart.inPoints.length" class="chart-empty">no calorie data yet</div>
              <svg
                v-else
                class="chart-svg"
                :viewBox="chartViewBox"
                preserveAspectRatio="none"
                role="img"
                aria-label="calories versus workout calories"
              >
                <line
                  v-for="tick in caloriesChart.yTicks"
                  :key="`cal-y-${tick.y}`"
                  class="grid-line"
                  :x1="chartFrame.padLeft"
                  :x2="chartFrame.width - chartFrame.padRight"
                  :y1="tick.y"
                  :y2="tick.y"
                />

                <path
                  v-for="(segment, idx) in caloriesChart.inSegments"
                  :key="`cal-in-segment-${idx}`"
                  class="line-calories"
                  :d="segment"
                />
                <path
                  v-for="(segment, idx) in caloriesChart.outSegments"
                  :key="`cal-out-segment-${idx}`"
                  class="line-workout"
                  :d="segment"
                />

                <text
                  v-for="tick in caloriesChart.yTicks"
                  :key="`cal-y-label-${tick.y}`"
                  class="axis-label"
                  :x="chartFrame.padLeft - 4"
                  :y="tick.y + 4"
                  text-anchor="end"
                >
                  {{ tick.label }}
                </text>

                <text
                  v-for="tick in caloriesChart.xTicks"
                  :key="`cal-x-label-${tick.x}`"
                  class="axis-label axis-label-x"
                  :x="tick.x"
                  :y="chartFrame.height - 8"
                  :text-anchor="tick.anchor"
                >
                  {{ tick.label }}
                </text>
              </svg>

              <div class="legend-row">
                <span class="legend-pill legend-calories">calories in</span>
                <span class="legend-pill legend-workout">workout calories</span>
              </div>
            </article>

            <article class="chart-card chart-card-wide">
              <div class="chart-header">
                <h3>daily mood vs weather</h3>
                <span>{{ dailyRangeLabel }}</span>
              </div>

              <div v-if="dailyError" class="chart-empty">{{ dailyError }}</div>
              <div v-else-if="statsLoading && !dailyFacts.length" class="chart-empty">loading chart...</div>
              <div v-else-if="!moodWeatherChart.moodPoints.length" class="chart-empty">no daily weather data yet</div>
              <svg
                v-else
                class="chart-svg"
                :viewBox="wideChartViewBox"
                preserveAspectRatio="none"
                role="img"
                aria-label="daily mood compared with weather"
              >
                <line
                  v-for="tick in moodWeatherChart.moodTicks"
                  :key="`mood-weather-y-${tick.y}`"
                  class="grid-line"
                  :x1="wideChartFrame.padLeft"
                  :x2="wideChartFrame.width - wideChartFrame.padRight"
                  :y1="tick.y"
                  :y2="tick.y"
                />

                <path
                  v-for="(segment, idx) in moodWeatherChart.moodSegments"
                  :key="`mood-weather-mood-segment-${idx}`"
                  class="line-mood"
                  :d="segment"
                />

                <path
                  v-for="(segment, idx) in moodWeatherChart.tempSegments"
                  :key="`mood-weather-temp-segment-${idx}`"
                  class="line-weather"
                  :d="segment"
                />

                <template v-for="point in moodWeatherChart.moodPoints" :key="`mood-weather-mood-point-${point.index}`">
                  <circle
                    v-if="point.value !== null"
                    class="point point-mood"
                    :cx="point.x"
                    :cy="point.y"
                    r="2.4"
                  />
                </template>

                <template v-for="point in moodWeatherChart.tempPoints" :key="`mood-weather-temp-point-${point.index}`">
                  <circle
                    v-if="point.value !== null"
                    class="point point-weather"
                    :cx="point.x"
                    :cy="point.y"
                    r="2.4"
                  />
                </template>

                <g v-for="marker in moodWeatherChart.conditionMarkers" :key="marker.id" :class="['weather-marker', marker.className]">
                  <circle :cx="marker.x" :cy="marker.y" r="8" />
                  <text :x="marker.x" :y="marker.y + 3" text-anchor="middle">{{ marker.short }}</text>
                  <title>{{ marker.label }}</title>
                </g>

                <text
                  v-for="tick in moodWeatherChart.moodTicks"
                  :key="`mood-weather-left-label-${tick.y}`"
                  class="axis-label"
                  :x="wideChartFrame.padLeft - 4"
                  :y="tick.y + 4"
                  text-anchor="end"
                >
                  {{ tick.label }}
                </text>

                <text
                  v-for="tick in moodWeatherChart.tempTicks"
                  :key="`mood-weather-right-label-${tick.y}`"
                  class="axis-label axis-label-right"
                  :x="wideChartFrame.width - wideChartFrame.padRight + 4"
                  :y="tick.y + 4"
                  text-anchor="start"
                >
                  {{ tick.label }}
                </text>

                <text
                  v-for="tick in moodWeatherChart.xTicks"
                  :key="`mood-weather-x-label-${tick.x}`"
                  class="axis-label axis-label-x"
                  :x="tick.x"
                  :y="wideChartFrame.height - 8"
                  :text-anchor="tick.anchor"
                >
                  {{ tick.label }}
                </text>
              </svg>

              <div class="legend-row">
                <span class="legend-pill legend-mood">mood</span>
                <span class="legend-pill legend-weather">max temp</span>
                <span class="legend-pill legend-rain">R rain</span>
                <span class="legend-pill legend-snow">N snow</span>
                <span class="legend-pill legend-sun">S sun</span>
                <span class="legend-pill legend-clouds">C clouds</span>
              </div>
            </article>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AIInsightPanel from "../components/AIInsightPanel.vue";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const latestWeather = ref(null);
const weatherLoading = ref(false);
const weatherError = ref("");

const dailyFacts = ref([]);
const statsLoading = ref(false);
const dailyError = ref("");
const dailyStartDate = ref("");
const dailyEndDate = ref("");

const chartFrame = Object.freeze({
  width: 980,
  height: 290,
  padLeft: 36,
  padRight: 6,
  padTop: 18,
  padBottom: 56,
});
const wideChartFrame = Object.freeze({
  width: 980,
  height: 290,
  padLeft: 36,
  padRight: 36,
  padTop: 18,
  padBottom: 56,
});
const chartViewBox = `0 0 ${chartFrame.width} ${chartFrame.height}`;
const wideChartViewBox = `0 0 ${wideChartFrame.width} ${wideChartFrame.height}`;

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
  const url = new URL(`${API_BASE}/stats/daily-life-facts`);
  if (dailyStartDate.value) {
    url.searchParams.set("start_date", dailyStartDate.value);
  }
  if (dailyEndDate.value) {
    url.searchParams.set("end_date", dailyEndDate.value);
  }
  if (!dailyStartDate.value && !dailyEndDate.value) {
    url.searchParams.set("limit", "90");
  }

  const res = await fetch(url.toString());
  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(msg || `failed to load daily stats (${res.status})`);
  }

  const payload = await res.json();
  return Array.isArray(payload) ? payload : [];
}

async function fetchStats() {
  const rangeError = validateRangeInputs();
  if (rangeError) {
    dailyError.value = rangeError;
    return;
  }

  statsLoading.value = true;
  dailyError.value = "";
  try {
    dailyFacts.value = await fetchDailyLifeFacts();
  } catch (err) {
    dailyFacts.value = [];
    dailyError.value = err?.message || "unable to load daily stats";
  }

  statsLoading.value = false;
}

function displayWeatherValue(value, formatter) {
  if (weatherLoading.value) return "loading...";
  if (weatherError.value) return "unavailable";
  if (value === null || value === undefined || value === "") return "--";

  const formatted = formatter ? formatter(value) : String(value);
  return formatted || "--";
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

function toDateOnly(dateValue) {
  const d = new Date(dateValue);
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}

function initializeRanges() {
  const today = new Date();
  const defaultStart = new Date("2026-03-01T00:00:00");
  const effectiveStart = defaultStart <= today ? defaultStart : today;

  dailyEndDate.value = toDateOnly(today);
  dailyStartDate.value = toDateOnly(effectiveStart);
}

function validateRangeInputs() {
  if (dailyStartDate.value && dailyEndDate.value && dailyStartDate.value > dailyEndDate.value) {
    return "daily range is invalid (start date is after end date)";
  }

  return "";
}

async function resetRanges() {
  initializeRanges();
  await fetchStats();
}

function formatCalendarLabel(value) {
  if (!value) return "--";
  const dt = new Date(`${value}T00:00:00`);
  if (Number.isNaN(dt.getTime())) return String(value);
  return `${dt.getMonth() + 1}/${dt.getDate()}`;
}

function formatCompactCalendarLabel(value, previousValue) {
  if (!value) return "--";

  const current = new Date(`${value}T00:00:00`);
  if (Number.isNaN(current.getTime())) return String(value);

  const month = current.getMonth() + 1;
  const day = current.getDate();
  if (!previousValue) return `${month}/${day}`;

  const previous = new Date(`${previousValue}T00:00:00`);
  if (Number.isNaN(previous.getTime())) return `${month}/${day}`;

  const previousMonth = previous.getMonth() + 1;
  return previousMonth === month ? String(day) : `${month}/${day}`;
}

function formatChartDateTick(row, index, rows) {
  return formatCompactCalendarLabel(row?.day, index > 0 ? rows[index - 1]?.day : null);
}

function toFiniteNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatTickNumber(value) {
  const rounded = Math.round(value);
  if (Math.abs(value - rounded) < 0.05) return String(rounded);
  return value.toFixed(1);
}

function formatMoodTick(value) {
  return String(Math.round(value));
}

function formatCalorieTick(value) {
  return Math.round(value).toLocaleString();
}

function formatTempAxisTick(value) {
  return `${Math.round(value)}°`;
}

function chartX(index, total, frame = chartFrame) {
  const width = frame.width - frame.padLeft - frame.padRight;
  if (total <= 1) return frame.padLeft + width / 2;
  return frame.padLeft + (index * width) / (total - 1);
}

function chartY(value, min, max, frame = chartFrame) {
  const height = frame.height - frame.padTop - frame.padBottom;
  const range = max - min || 1;
  const ratio = (value - min) / range;
  return frame.padTop + (1 - ratio) * height;
}

function buildPathSegments(points) {
  const segments = [];
  let current = [];

  for (const point of points) {
    if (point.value === null || point.y === null) {
      if (current.length) {
        segments.push(current.join(" "));
        current = [];
      }
      continue;
    }

    const prefix = current.length === 0 ? "M" : "L";
    current.push(`${prefix}${point.x.toFixed(2)},${point.y.toFixed(2)}`);
  }

  if (current.length) {
    segments.push(current.join(" "));
  }

  return segments;
}

function buildYTicks(min, max, steps, formatter = formatTickNumber, frame = chartFrame) {
  const ticks = [];
  const safeSteps = Math.max(1, steps);

  for (let i = 0; i <= safeSteps; i += 1) {
    const ratio = i / safeSteps;
    const value = max - (max - min) * ratio;
    ticks.push({
      value,
      y: chartY(value, min, max, frame),
      label: formatter(value),
    });
  }

  return ticks;
}

function buildXTicks(points, labeler) {
  if (!points.length) return [];
  const rows = points.map((point) => point.raw);
  return points.map((point, index) => ({
    x: point.x,
    label: labeler(point.raw, index, rows),
    anchor: index === 0 ? "start" : (index === points.length - 1 ? "end" : "middle"),
  }));
}

function resolveMoodFloor(rows, getter) {
  const vals = rows.map((row) => toFiniteNumber(getter(row))).filter((v) => v !== null);
  if (!vals.length) return 0;

  const minValue = Math.min(...vals);
  if (minValue >= 0) return 0;

  return Math.floor(minValue) - 1;
}

function buildLineChart(rows, getValue, options = {}) {
  const frame = options.frame || chartFrame;
  const values = rows.map((row) => toFiniteNumber(getValue(row)));
  const numeric = values.filter((value) => value !== null);

  const hasFixedMin = typeof options.fixedMin === "number";
  const hasFixedMax = typeof options.fixedMax === "number";

  let min = hasFixedMin ? options.fixedMin : (numeric.length ? Math.min(...numeric) : 0);
  let max = hasFixedMax ? options.fixedMax : (numeric.length ? Math.max(...numeric) : 1);

  if (!hasFixedMin || !hasFixedMax) {
    if (min === max) {
      const bump = min === 0 ? 1 : Math.max(1, Math.abs(min * 0.1));
      if (!hasFixedMin) min -= bump;
      if (!hasFixedMax) max += bump;
    } else {
      const padRatio = options.padRatio ?? 0.08;
      const pad = (max - min) * padRatio;
      if (!hasFixedMin) min -= pad;
      if (!hasFixedMax) max += pad;
    }
  }

  if (min === max) {
    max = min + 1;
  }

  const points = rows.map((row, index) => {
    const value = values[index];
    return {
      raw: row,
      index,
      value,
      x: chartX(index, rows.length, frame),
      y: value === null ? null : chartY(value, min, max, frame),
    };
  });

  const xLabeler = options.xLabel || formatChartDateTick;

  return {
    points,
    segments: buildPathSegments(points),
    yTicks: buildYTicks(min, max, options.ySteps ?? 4, options.yFormatter ?? formatTickNumber, frame),
    xTicks: buildXTicks(points, xLabeler),
    min,
    max,
  };
}

const dailyMoodChart = computed(() =>
  buildLineChart(dailyFacts.value, (row) => row?.avg_mood_score, {
    fixedMin: resolveMoodFloor(dailyFacts.value, (row) => row?.avg_mood_score),
    fixedMax: 10,
    yFormatter: formatMoodTick,
  })
);

const dailyAlcoholMarkers = computed(() =>
  dailyMoodChart.value.points
    .filter((point) => point.value !== null && Boolean(point.raw?.had_alcohol))
    .map((point) => ({ id: `a-${point.index}`, x: point.x, y: point.y }))
);

const dailySafetyMarkers = computed(() =>
  dailyMoodChart.value.points
    .filter((point) => point.value !== null && Boolean(point.raw?.safety_meeting))
    .map((point) => ({ id: `s-${point.index}`, x: point.x, y: point.y }))
);

const caloriesChart = computed(() => {
  const rows = dailyFacts.value;
  const frame = chartFrame;
  const inValues = rows.map((row) => toFiniteNumber(row?.total_calories));
  const outValues = rows.map((row) => toFiniteNumber(row?.total_workout_calories));
  const numeric = [...inValues, ...outValues].filter((value) => value !== null);

  let min = 0;
  let max = numeric.length ? Math.max(...numeric) : 100;

  if (max <= min) {
    max = min + 100;
  } else {
    max *= 1.1;
  }

  const buildPoints = (values) =>
    rows.map((row, index) => {
      const value = values[index];
      return {
        raw: row,
        index,
        value,
        x: chartX(index, rows.length, frame),
        y: value === null ? null : chartY(value, min, max, frame),
      };
    });

  const inPoints = buildPoints(inValues);
  const outPoints = buildPoints(outValues);

  return {
    inPoints,
    outPoints,
    inSegments: buildPathSegments(inPoints),
    outSegments: buildPathSegments(outPoints),
    yTicks: buildYTicks(min, max, 4, formatCalorieTick, frame),
    xTicks: buildXTicks(inPoints, formatChartDateTick),
  };
});

const moodWeatherChart = computed(() => {
  const rows = dailyFacts.value;
  const frame = wideChartFrame;

  const moodValues = rows.map((row) => toFiniteNumber(row?.avg_mood_score));
  const moodMin = resolveMoodFloor(rows, (row) => row?.avg_mood_score);
  const moodMax = 10;

  const tempValues = rows.map((row) => toFiniteNumber(row?.temp_max_f));
  const validTemps = tempValues.filter((value) => value !== null);

  let tempMin = validTemps.length ? Math.min(...validTemps) : 20;
  let tempMax = validTemps.length ? Math.max(...validTemps) : 80;
  if (tempMin === tempMax) {
    tempMin -= 4;
    tempMax += 4;
  } else {
    tempMin -= 3;
    tempMax += 3;
  }

  const moodPoints = rows.map((row, index) => {
    const value = moodValues[index];
    return {
      raw: row,
      index,
      value,
      x: chartX(index, rows.length, frame),
      y: value === null ? null : chartY(value, moodMin, moodMax, frame),
    };
  });

  const tempPoints = rows.map((row, index) => {
    const value = tempValues[index];
    return {
      raw: row,
      index,
      value,
      x: chartX(index, rows.length, frame),
      y: value === null ? null : chartY(value, tempMin, tempMax, frame),
    };
  });

  const conditionMarkers = [];
  for (const point of tempPoints) {
    if (point.value === null) continue;
    const overlays = [
      { flag: point.raw?.had_rain, short: "R", className: "weather-rain", label: "rainy day" },
      { flag: point.raw?.had_snow, short: "N", className: "weather-snow", label: "snow day" },
      { flag: point.raw?.had_sun, short: "S", className: "weather-sun", label: "sunny day" },
      { flag: point.raw?.had_clouds, short: "C", className: "weather-clouds", label: "cloudy day" },
    ];

    let offset = 0;
    for (const overlay of overlays) {
      if (!overlay.flag) continue;
      conditionMarkers.push({
        id: `${overlay.className}-${point.index}-${offset}`,
        x: point.x,
        y: Math.max(frame.padTop + 12, point.y - 13 - offset * 16),
        short: overlay.short,
        className: overlay.className,
        label: `${overlay.label} (${point.raw?.weather_summary || "weather"})`,
      });
      offset += 1;
    }
  }

  return {
    moodPoints,
    tempPoints,
    moodSegments: buildPathSegments(moodPoints),
    tempSegments: buildPathSegments(tempPoints),
    moodTicks: buildYTicks(moodMin, moodMax, 4, formatMoodTick, frame),
    tempTicks: buildYTicks(tempMin, tempMax, 4, formatTempAxisTick, frame),
    xTicks: buildXTicks(moodPoints, formatChartDateTick),
    conditionMarkers,
  };
});

const dailyRangeLabel = computed(() => {
  if (!dailyFacts.value.length) return "--";
  const first = dailyFacts.value[0]?.day;
  const last = dailyFacts.value[dailyFacts.value.length - 1]?.day;
  return `${formatCalendarLabel(first)} - ${formatCalendarLabel(last)}`;
});

onMounted(() => {
  initializeRanges();
  fetchLatestWeather();
  fetchStats();
});
</script>

<style scoped>
.page-shell {
  min-height: 100vh;
  padding: clamp(16px, 3vw, 32px);
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
  padding-bottom: 12px;
  margin-bottom: 18px;
}

.panel-header h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 400;
  text-transform: lowercase;
}

.panel-subtle {
  color: var(--muted);
  font-size: 1.1rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.panel-block {
  border: 1px solid var(--line2);
  border-radius: var(--radius);
  padding: 16px;
  background: rgba(255, 255, 255, 0.01);
}

.panel-block.wide {
  grid-column: 1 / -1;
}

.block-header {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line2);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.block-header h2 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 400;
  text-transform: lowercase;
}

.block-meta {
  color: var(--muted);
  text-transform: lowercase;
}

.range-controls {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin-bottom: 12px;
  border: 1px solid var(--line2);
  border-radius: 10px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.01);
}

.range-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
}

.range-label {
  color: var(--muted);
  text-transform: lowercase;
  min-width: 76px;
}

.range-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-transform: lowercase;
}

.range-field input {
  background: transparent;
  color: var(--fg);
  border: 1px solid var(--line2);
  border-radius: 8px;
  padding: 6px 8px;
  font: inherit;
}

.range-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.range-btn {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--fg);
  font: inherit;
  text-transform: lowercase;
  padding: 6px 10px;
  cursor: pointer;
}

.range-btn.ghost {
  background: transparent;
  border-color: var(--line2);
}

.range-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.kv-list {
  display: grid;
  gap: 10px;
}

.kv-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px dotted var(--line2);
  padding-bottom: 6px;
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
  gap: 10px;
}

.terminal-link {
  display: inline-block;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--fg);
  text-decoration: none;
  text-transform: lowercase;
}

.terminal-link:hover {
  background: rgba(255, 255, 255, 0.06);
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.chart-card {
  border: 1px solid var(--line2);
  border-radius: 10px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
}

.chart-card-wide {
  grid-column: 1 / -1;
}

.chart-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.chart-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 400;
  text-transform: lowercase;
}

.chart-header span {
  color: var(--muted);
  text-transform: lowercase;
  font-size: 0.95rem;
}

.chart-empty {
  border: 1px dashed var(--line2);
  border-radius: 8px;
  padding: 16px;
  text-transform: lowercase;
  color: var(--muted);
}

.chart-svg {
  width: 100%;
  overflow: hidden;
  height: 290px;
  display: block;
}

.grid-line {
  stroke: rgba(255, 255, 255, 0.09);
  stroke-width: 1;
}

.axis-label {
  fill: rgba(255, 255, 255, 0.92);
  font-size: 14px;
  font-weight: 600;
  text-transform: lowercase;
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.45);
  stroke-width: 0.8px;
  stroke-linejoin: round;
}

.axis-label-x {
  font-size: 11.5px;
  font-weight: 500;
  fill: rgba(255, 255, 255, 0.86);
  stroke: none;
  paint-order: normal;
}

.line-mood,
.line-weather,
.line-calories,
.line-workout {
  fill: none;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.line-mood {
  stroke: #89f5a8;
}

.line-weather {
  stroke: #7cc6ff;
  stroke-dasharray: 6 4;
}

.line-calories {
  stroke: #f7cd5e;
}

.line-workout {
  stroke: #ff8f7a;
}

.point {
  stroke: #000;
  stroke-width: 0.5;
}

.point-mood {
  fill: #89f5a8;
}

.point-muted {
  fill: rgba(255, 255, 255, 0.45);
}

.point-weather {
  fill: #7cc6ff;
}

.marker {
  stroke: #000;
  stroke-width: 0.9;
}

.marker-alcohol {
  fill: #f1b35f;
}

.marker-safety {
  fill: #73d5ff;
}

.weather-marker circle {
  stroke: #000;
  stroke-width: 0.8;
}

.weather-marker text {
  fill: #000;
  font-size: 10px;
  font-weight: 700;
}

.weather-rain circle {
  fill: #7cc6ff;
}

.weather-snow circle {
  fill: #d7ecff;
}

.weather-sun circle {
  fill: #f7cd5e;
}

.weather-clouds circle {
  fill: #a8b8cc;
}

.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.legend-pill {
  border: 1px solid var(--line2);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.9rem;
  text-transform: lowercase;
}

.legend-calories {
  border-color: rgba(247, 205, 94, 0.7);
}

.legend-workout {
  border-color: rgba(255, 143, 122, 0.7);
}

.legend-mood {
  border-color: rgba(137, 245, 168, 0.8);
}

.legend-weather {
  border-color: rgba(124, 198, 255, 0.8);
}

.legend-alcohol {
  border-color: rgba(241, 179, 95, 0.8);
}

.legend-safety {
  border-color: rgba(115, 213, 255, 0.8);
}

.legend-rain {
  border-color: rgba(124, 198, 255, 0.8);
}

.legend-snow {
  border-color: rgba(215, 236, 255, 0.9);
}

.legend-sun {
  border-color: rgba(247, 205, 94, 0.9);
}

.legend-clouds {
  border-color: rgba(168, 184, 204, 0.9);
}

.axis-label-right {
  font-size: 12px;
}

@media (min-width: 900px) {
  .dashboard-grid {
    grid-template-columns: 1fr 1.2fr;
  }

  .range-controls {
    grid-template-columns: 1fr auto;
    align-items: end;
  }

  .range-actions {
    justify-content: flex-end;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
