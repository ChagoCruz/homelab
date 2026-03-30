<template>
  <ChartCard
    title="mood trend"
    subtitle="featured 7-day view"
    :meta="meta"
    :loading="loading"
    :error="error"
    :has-data="hasData"
    empty-text="no daily mood data yet"
  >
    <svg
      class="chart-svg"
      :viewBox="chartViewBox"
      preserveAspectRatio="none"
      role="img"
      aria-label="daily mood trend"
    >
      <line
        v-for="tick in chart.yTicks"
        :key="`mood-grid-${tick.y}`"
        class="grid-line"
        :x1="frame.padLeft"
        :x2="frame.width - frame.padRight"
        :y1="tick.y"
        :y2="tick.y"
      />

      <path
        v-for="(segment, idx) in chart.segments"
        :key="`mood-segment-${idx}`"
        class="line-mood"
        :d="segment"
      />

      <circle
        v-if="lastPoint"
        class="point-last"
        :cx="lastPoint.x"
        :cy="lastPoint.y"
        r="3.2"
      />

      <text
        v-for="tick in chart.yTicks"
        :key="`mood-y-label-${tick.y}`"
        class="axis-label"
        :x="frame.padLeft - 4"
        :y="tick.y + 4"
        text-anchor="end"
      >
        {{ tick.label }}
      </text>

      <text
        v-for="tick in chart.xTicks"
        :key="`mood-x-label-${tick.x}`"
        class="axis-label axis-label-x"
        :x="tick.x"
        :y="frame.height - 8"
        :text-anchor="tick.anchor"
      >
        {{ tick.label }}
      </text>
    </svg>

    <template #legend>
      <span class="legend-pill">mood</span>
      <span class="legend-pill muted">latest point highlighted</span>
    </template>
  </ChartCard>
</template>

<script setup>
import { computed } from "vue";
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
  meta: {
    type: String,
    default: "last 7 days",
  },
});

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
    ySteps: 4,
    yFormatter: formatMoodTick,
    xMaxTicks: 7,
  })
);

const hasData = computed(() => chart.value.points.some((point) => point.value !== null));

const lastPoint = computed(() => {
  for (let index = chart.value.points.length - 1; index >= 0; index -= 1) {
    const point = chart.value.points[index];
    if (point.value !== null) {
      return point;
    }
  }
  return null;
});
</script>

<style scoped>
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
  stroke-width: 2.3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.point-last {
  fill: #8af6aa;
  stroke: #000;
  stroke-width: 0.9;
}

.axis-label {
  fill: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.45);
  stroke-width: 0.8px;
}

.axis-label-x {
  font-size: 11px;
  stroke: none;
}

.legend-pill {
  border: 1px solid rgba(138, 246, 170, 0.7);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.86rem;
  text-transform: lowercase;
}

.legend-pill.muted {
  border-color: var(--line2);
  color: var(--muted);
}

@media (max-width: 430px) {
  .chart-svg {
    height: 236px;
  }

  .axis-label {
    font-size: 10.4px;
    stroke-width: 0.6px;
  }

  .axis-label-x {
    font-size: 8.2px;
  }
}
</style>
