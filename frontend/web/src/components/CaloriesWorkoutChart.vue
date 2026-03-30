<template>
  <ChartCard
    title="calories vs workout"
    subtitle="calories in line + workout bars"
    :meta="`${rows.length} day(s)`"
    :loading="loading"
    :error="error"
    :has-data="hasData"
    empty-text="no calorie data yet"
  >
    <svg
      class="chart-svg"
      :viewBox="chartViewBox"
      preserveAspectRatio="none"
      role="img"
      aria-label="calories in and workout calories"
    >
      <line
        v-for="tick in chart.yTicks"
        :key="`cal-grid-${tick.y}`"
        class="grid-line"
        :x1="frame.padLeft"
        :x2="frame.width - frame.padRight"
        :y1="tick.y"
        :y2="tick.y"
      />

      <rect
        v-for="bar in chart.workoutBars"
        :key="bar.id"
        class="bar-workout"
        :x="bar.x"
        :y="bar.y"
        :width="bar.width"
        :height="bar.height"
      />

      <path
        v-for="(segment, idx) in chart.inSegments"
        :key="`cal-in-segment-${idx}`"
        class="line-calories"
        :d="segment"
      />

      <text
        v-for="tick in chart.yTicks"
        :key="`cal-y-label-${tick.y}`"
        class="axis-label"
        :x="frame.padLeft - 4"
        :y="tick.y + 4"
        text-anchor="end"
      >
        {{ tick.label }}
      </text>

      <text
        v-for="tick in chart.xTicks"
        :key="`cal-x-label-${tick.x}`"
        class="axis-label axis-label-x"
        :x="tick.x"
        :y="frame.height - 8"
        :text-anchor="tick.anchor"
      >
        {{ tick.label }}
      </text>
    </svg>

    <template #legend>
      <span class="legend-pill legend-calories">calories in</span>
      <span class="legend-pill legend-workout">workout calories</span>
    </template>
  </ChartCard>
</template>

<script setup>
import { computed } from "vue";
import ChartCard from "./ChartCard.vue";
import {
  buildPathSegments,
  buildXTicks,
  buildYTicks,
  chartX,
  chartY,
  formatChartDateTick,
  toFiniteNumber,
} from "../utils/chartUtils";

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

const frame = Object.freeze({
  width: 980,
  height: 252,
  padLeft: 42,
  padRight: 8,
  padTop: 16,
  padBottom: 46,
});
const chartViewBox = `0 0 ${frame.width} ${frame.height}`;

function formatCalorieTick(value) {
  return Math.round(value).toLocaleString();
}

const chart = computed(() => {
  const rows = props.rows;

  const inValues = rows.map((row) => toFiniteNumber(row?.total_calories));
  const workoutValues = rows.map((row) => toFiniteNumber(row?.total_workout_calories));

  const numeric = [...inValues, ...workoutValues].filter((value) => value !== null);
  let min = 0;
  let max = numeric.length ? Math.max(...numeric) : 100;

  if (max <= min) {
    max = min + 100;
  } else {
    max *= 1.1;
  }

  const inPoints = rows.map((row, index) => {
    const value = inValues[index];
    return {
      raw: row,
      index,
      value,
      x: chartX(index, rows.length, frame),
      y: value === null ? null : chartY(value, min, max, frame),
    };
  });

  const workoutPoints = rows.map((row, index) => {
    const value = workoutValues[index];
    return {
      raw: row,
      index,
      value,
      x: chartX(index, rows.length, frame),
      y: value === null ? null : chartY(value, min, max, frame),
    };
  });

  const plotWidth = frame.width - frame.padLeft - frame.padRight;
  const step = rows.length <= 1 ? plotWidth : plotWidth / (rows.length - 1);
  const barWidth = Math.max(5, Math.min(16, step * 0.48));
  const yZero = chartY(0, min, max, frame);

  const workoutBars = workoutPoints
    .filter((point) => point.value !== null)
    .map((point) => ({
      id: `workout-bar-${point.index}`,
      x: point.x - barWidth / 2,
      y: point.y,
      width: barWidth,
      height: Math.max(1, yZero - point.y),
    }));

  return {
    inPoints,
    inSegments: buildPathSegments(inPoints),
    workoutBars,
    yTicks: buildYTicks(min, max, 4, formatCalorieTick, frame),
    xTicks: buildXTicks(inPoints, formatChartDateTick, 8),
  };
});

const hasData = computed(() => chart.value.inPoints.some((point) => point.value !== null));
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

.line-calories {
  fill: none;
  stroke: #f7cd5e;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.bar-workout {
  fill: rgba(255, 143, 122, 0.72);
  stroke: rgba(255, 143, 122, 0.95);
  stroke-width: 0.8;
  rx: 1.8;
}

.axis-label {
  fill: rgba(255, 255, 255, 0.9);
  font-size: 12.4px;
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.45);
  stroke-width: 0.7px;
}

.axis-label-x {
  font-size: 10.6px;
  stroke: none;
}

.legend-pill {
  border: 1px solid var(--line2);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.85rem;
  text-transform: lowercase;
}

.legend-calories {
  border-color: rgba(247, 205, 94, 0.75);
}

.legend-workout {
  border-color: rgba(255, 143, 122, 0.78);
}

@media (max-width: 430px) {
  .chart-svg {
    height: 236px;
  }

  .axis-label {
    font-size: 9.8px;
    stroke-width: 0.55px;
  }

  .axis-label-x {
    font-size: 8px;
  }
}
</style>
