<template>
  <ChartCard
    title="daily mood overlays"
    subtitle="one chart, optional context overlays"
    :meta="`${rows.length} day(s)`"
    :loading="loading"
    :error="error"
    :has-data="hasData"
    empty-text="no daily mood data yet"
  >
    <template #controls>
      <div class="toggle-row">
        <button type="button" class="chip" :class="{ on: showMood }" @click="showMood = !showMood">
          mood
        </button>
        <button type="button" class="chip" :class="{ on: showAlcohol }" @click="showAlcohol = !showAlcohol">
          alcohol
        </button>
        <button type="button" class="chip" :class="{ on: showSafety }" @click="showSafety = !showSafety">
          safety meeting
        </button>
      </div>
    </template>

    <svg
      class="chart-svg"
      :viewBox="chartViewBox"
      preserveAspectRatio="none"
      role="img"
      aria-label="daily mood trend with overlays"
    >
      <line
        v-for="tick in chart.yTicks"
        :key="`mood-overlay-y-${tick.y}`"
        class="grid-line"
        :x1="frame.padLeft"
        :x2="frame.width - frame.padRight"
        :y1="tick.y"
        :y2="tick.y"
      />

      <template v-if="showMood">
        <path
          v-for="(segment, idx) in chart.segments"
          :key="`mood-overlay-segment-${idx}`"
          class="line-mood"
          :d="segment"
        />
      </template>

      <template v-if="showAlcohol">
        <g v-for="marker in alcoholMarkers" :key="marker.id">
          <circle class="marker marker-alcohol" :cx="marker.x" :cy="marker.y" r="4.8" />
          <title>had alcohol</title>
        </g>
      </template>

      <template v-if="showSafety">
        <g v-for="marker in safetyMarkers" :key="marker.id">
          <rect class="marker marker-safety" :x="marker.x - 4" :y="marker.y - 4" width="8" height="8" />
          <title>safety meeting completed</title>
        </g>
      </template>

      <text
        v-for="tick in chart.yTicks"
        :key="`mood-overlay-y-label-${tick.y}`"
        class="axis-label"
        :x="frame.padLeft - 4"
        :y="tick.y + 4"
        text-anchor="end"
      >
        {{ tick.label }}
      </text>

      <text
        v-for="tick in chart.xTicks"
        :key="`mood-overlay-x-label-${tick.x}`"
        class="axis-label axis-label-x"
        :x="tick.x"
        :y="frame.height - 8"
        :text-anchor="tick.anchor"
      >
        {{ tick.label }}
      </text>
    </svg>

    <template #legend>
      <span v-if="showMood" class="legend-pill legend-mood">mood</span>
      <span v-if="showAlcohol" class="legend-pill legend-alcohol">alcohol day</span>
      <span v-if="showSafety" class="legend-pill legend-safety">safety meeting day</span>
      <span v-if="!showMood && !showAlcohol && !showSafety" class="legend-pill muted">toggle a layer</span>
    </template>
  </ChartCard>
</template>

<script setup>
import { computed, ref } from "vue";
import ChartCard from "./ChartCard.vue";
import { buildLineChart } from "../utils/chartUtils";

const props = defineProps({
  rows: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
});

const showMood = ref(true);
const showAlcohol = ref(false);
const showSafety = ref(false);

const frame = Object.freeze({
  width: 980,
  height: 252,
  padLeft: 34,
  padRight: 8,
  padTop: 16,
  padBottom: 46,
});
const chartViewBox = `0 0 ${frame.width} ${frame.height}`;

function formatMoodTick(value) {
  return String(Math.round(value));
}

function resolveMoodFloor(rows) {
  const vals = rows
    .map((row) => Number(row?.avg_mood_score))
    .filter((value) => Number.isFinite(value));

  if (!vals.length) return 0;
  const minValue = Math.min(...vals);
  return minValue >= 0 ? 0 : Math.floor(minValue) - 1;
}

const chart = computed(() =>
  buildLineChart(props.rows, (row) => row?.avg_mood_score, {
    frame,
    fixedMin: resolveMoodFloor(props.rows),
    fixedMax: 10,
    yFormatter: formatMoodTick,
    ySteps: 4,
    xMaxTicks: 8,
  })
);

const hasData = computed(() => chart.value.points.some((point) => point.value !== null));

const alcoholMarkers = computed(() =>
  chart.value.points
    .filter((point) => point.value !== null && Boolean(point.raw?.had_alcohol))
    .map((point) => ({ id: `a-${point.index}`, x: point.x, y: point.y }))
);

const safetyMarkers = computed(() =>
  chart.value.points
    .filter((point) => point.value !== null && Boolean(point.raw?.safety_meeting))
    .map((point) => ({ id: `s-${point.index}`, x: point.x, y: point.y }))
);
</script>

<style scoped>
.toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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

.chip.on {
  border-color: var(--line);
  background: rgba(255, 255, 255, 0.08);
}

.chart-svg {
  width: 100%;
  height: 252px;
  display: block;
}

.grid-line {
  stroke: rgba(255, 255, 255, 0.09);
  stroke-width: 1;
}

.line-mood {
  fill: none;
  stroke: #8af6aa;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
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

.axis-label {
  fill: rgba(255, 255, 255, 0.9);
  font-size: 12.8px;
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.45);
  stroke-width: 0.8px;
}

.axis-label-x {
  font-size: 10.8px;
  stroke: none;
}

.legend-pill {
  border: 1px solid var(--line2);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.85rem;
  text-transform: lowercase;
}

.legend-mood {
  border-color: rgba(138, 246, 170, 0.7);
}

.legend-alcohol {
  border-color: rgba(241, 179, 95, 0.75);
}

.legend-safety {
  border-color: rgba(115, 213, 255, 0.75);
}

.legend-pill.muted {
  color: var(--muted);
}

@media (max-width: 430px) {
  .chart-svg {
    height: 236px;
  }

  .axis-label {
    font-size: 10px;
    stroke-width: 0.6px;
  }

  .axis-label-x {
    font-size: 8.2px;
  }

  .chip {
    padding: 3px 8px;
    font-size: 0.84rem;
  }
}
</style>
