<template>
  <ChartCard
    title="mood x weather heatmap"
    subtitle="mood intensity by day"
    :meta="`${rows.length} day(s)`"
    :loading="loading"
    :error="error"
    :has-data="hasData"
    empty-text="no weather-linked mood data yet"
  >
    <svg
      class="heatmap-svg"
      :viewBox="chartViewBox"
      preserveAspectRatio="none"
      role="img"
      aria-label="daily mood heatmap with weather markers"
    >
      <rect
        class="heatmap-frame"
        :x="frame.padLeft"
        :y="cellY"
        :width="frame.width - frame.padLeft - frame.padRight"
        :height="cellHeight"
      />

      <g v-for="cell in cells" :key="cell.id">
        <rect
          class="heat-cell"
          :x="cell.x"
          :y="cellY"
          :width="cell.width"
          :height="cellHeight"
          :fill="cell.fill"
        />

        <text v-if="cell.weatherCode" class="weather-code" :x="cell.center" :y="cellY - 8" text-anchor="middle">
          {{ cell.weatherCode }}
        </text>
      </g>

      <text class="legend-axis" :x="frame.padLeft" :y="cellY + cellHeight + 18" text-anchor="start">low mood</text>
      <text class="legend-axis" :x="frame.width - frame.padRight" :y="cellY + cellHeight + 18" text-anchor="end">high mood</text>

      <text
        v-for="tick in xTicks"
        :key="`heatmap-x-${tick.x}`"
        class="axis-label"
        :x="tick.x"
        :y="frame.height - 8"
        :text-anchor="tick.anchor"
      >
        {{ tick.label }}
      </text>
    </svg>

    <template #legend>
      <span class="legend-pill">R rain</span>
      <span class="legend-pill">N snow</span>
      <span class="legend-pill">S sun</span>
      <span class="legend-pill">C clouds</span>
    </template>
  </ChartCard>
</template>

<script setup>
import { computed } from "vue";
import ChartCard from "./ChartCard.vue";
import { buildXTicks, formatChartDateTick, toFiniteNumber } from "../utils/chartUtils";

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
  padLeft: 28,
  padRight: 8,
  padTop: 16,
  padBottom: 52,
});
const chartViewBox = `0 0 ${frame.width} ${frame.height}`;

const cellY = frame.padTop + 24;
const cellHeight = frame.height - frame.padTop - frame.padBottom - 34;

function clampMood(value) {
  const n = toFiniteNumber(value);
  if (n === null) return null;
  return Math.max(0, Math.min(10, n));
}

function moodFill(value) {
  const mood = clampMood(value);
  if (mood === null) {
    return "rgba(255,255,255,0.05)";
  }

  const alpha = 0.14 + (mood / 10) * 0.78;
  return `rgba(255,255,255,${alpha.toFixed(3)})`;
}

function weatherCode(row) {
  const codes = [];
  if (row?.had_rain) codes.push("R");
  if (row?.had_snow) codes.push("N");
  if (row?.had_sun) codes.push("S");
  if (row?.had_clouds) codes.push("C");
  return codes.slice(0, 2).join("");
}

const cells = computed(() => {
  const rows = props.rows;
  if (!rows.length) return [];

  const plotWidth = frame.width - frame.padLeft - frame.padRight;
  const gap = 2;
  const width = Math.max(8, (plotWidth - gap * Math.max(rows.length - 1, 0)) / rows.length);

  return rows.map((row, index) => {
    const x = frame.padLeft + index * (width + gap);
    return {
      id: `heat-${index}`,
      x,
      center: x + width / 2,
      width,
      raw: row,
      fill: moodFill(row?.avg_mood_score),
      weatherCode: weatherCode(row),
    };
  });
});

const xTicks = computed(() =>
  buildXTicks(
    cells.value.map((cell, index) => ({ raw: cell.raw, x: cell.center, index })),
    formatChartDateTick,
    8
  )
);

const hasData = computed(() => props.rows.length > 0);
</script>

<style scoped>
.heatmap-svg {
  width: 100%;
  height: 252px;
  display: block;
}

.heatmap-frame {
  fill: rgba(255, 255, 255, 0.02);
  stroke: rgba(255, 255, 255, 0.1);
  stroke-width: 1;
}

.heat-cell {
  stroke: rgba(0, 0, 0, 0.65);
  stroke-width: 0.7;
}

.weather-code {
  fill: rgba(255, 255, 255, 0.94);
  font-size: 10.4px;
  letter-spacing: 0.08em;
}

.axis-label {
  fill: rgba(255, 255, 255, 0.86);
  font-size: 10.2px;
}

.legend-axis {
  fill: var(--muted);
  font-size: 10px;
  text-transform: lowercase;
}

.legend-pill {
  border: 1px solid var(--line2);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.84rem;
  text-transform: lowercase;
}

@media (max-width: 430px) {
  .heatmap-svg {
    height: 228px;
  }

  .weather-code {
    font-size: 9.2px;
  }

  .axis-label {
    font-size: 7.6px;
  }

  .legend-axis {
    font-size: 8px;
  }
}
</style>
