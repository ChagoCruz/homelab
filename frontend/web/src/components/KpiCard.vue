<template>
  <article class="kpi-card">
    <div class="kpi-label">{{ label }}</div>
    <div class="kpi-value">{{ value }}</div>
    <div class="kpi-meta">{{ trend }}</div>
    <svg
      v-if="hasSparkline"
      class="kpi-spark-svg"
      viewBox="0 0 100 24"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <line class="spark-grid" x1="0" y1="22" x2="100" y2="22" />
      <path v-for="(segment, idx) in sparkSegments" :key="`spark-${idx}`" class="spark-line" :d="segment" />
      <circle v-if="lastPoint" class="spark-point" :cx="lastPoint.x" :cy="lastPoint.y" r="1.7" />
    </svg>
  </article>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: String,
    default: "--",
  },
  trend: {
    type: String,
    default: "no recent change",
  },
  sparkValues: {
    type: Array,
    default: () => [],
  },
});

function toFiniteNumber(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "string" && value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function sampleSeries(values, maxPoints = 16) {
  if (values.length <= maxPoints) return values;
  if (maxPoints <= 1) return [values[values.length - 1]];

  const step = (values.length - 1) / (maxPoints - 1);
  const sampled = [];
  for (let i = 0; i < maxPoints; i += 1) {
    sampled.push(values[Math.round(i * step)]);
  }
  return sampled;
}

const sampled = computed(() => sampleSeries(props.sparkValues.map(toFiniteNumber), 16));

const hasSparkline = computed(() => sampled.value.filter((value) => value !== null).length >= 2);

const points = computed(() => {
  if (!hasSparkline.value) return [];

  const values = sampled.value;
  const numeric = values.filter((value) => value !== null);
  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  const range = max - min || 1;

  return values.map((value, index) => {
    const x = values.length <= 1 ? 50 : (index * 100) / (values.length - 1);
    if (value === null) {
      return { index, value, x, y: null };
    }
    const y = 2 + (1 - (value - min) / range) * 18;
    return { index, value, x, y };
  });
});

const sparkSegments = computed(() => {
  const segments = [];
  let current = [];

  for (const point of points.value) {
    if (point.value === null || point.y === null) {
      if (current.length) {
        segments.push(current.join(" "));
        current = [];
      }
      continue;
    }

    const cmd = current.length === 0 ? "M" : "L";
    current.push(`${cmd}${point.x.toFixed(2)},${point.y.toFixed(2)}`);
  }

  if (current.length) {
    segments.push(current.join(" "));
  }

  return segments;
});

const lastPoint = computed(() => {
  for (let i = points.value.length - 1; i >= 0; i -= 1) {
    const point = points.value[i];
    if (point.value !== null && point.y !== null) return point;
  }
  return null;
});
</script>

<style scoped>
.kpi-card {
  border: 1px solid var(--line2);
  border-radius: 10px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.015);
  display: grid;
  gap: 6px;
}

.kpi-label {
  text-transform: lowercase;
  color: var(--muted);
  font-size: 0.95rem;
}

.kpi-value {
  font-size: clamp(1.4rem, 5vw, 2rem);
  line-height: 1;
  text-transform: lowercase;
}

.kpi-meta {
  font-size: 0.9rem;
  text-transform: lowercase;
  color: var(--muted);
}

.kpi-spark-svg {
  margin-top: 2px;
  width: 100%;
  height: 24px;
  display: block;
}

.spark-grid {
  stroke: rgba(255, 255, 255, 0.14);
  stroke-width: 1;
}

.spark-line {
  fill: none;
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.spark-point {
  fill: #fff;
  stroke: #000;
  stroke-width: 0.7;
}

@media (max-width: 430px) {
  .kpi-card {
    padding: 9px;
    gap: 5px;
  }

  .kpi-value {
    font-size: 1.32rem;
  }

  .kpi-meta,
  .kpi-label {
    font-size: 0.82rem;
  }
}
</style>
