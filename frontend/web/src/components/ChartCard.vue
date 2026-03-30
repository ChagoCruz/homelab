<template>
  <article class="chart-card">
    <header class="chart-header">
      <div>
        <h3>{{ title }}</h3>
        <p v-if="subtitle" class="chart-subtitle">{{ subtitle }}</p>
      </div>
      <span v-if="meta" class="chart-meta">{{ meta }}</span>
    </header>

    <div v-if="$slots.controls" class="chart-controls">
      <slot name="controls" />
    </div>

    <div v-if="error" class="chart-empty">{{ error }}</div>
    <div v-else-if="loading && !hasData" class="chart-empty">{{ loadingText }}</div>
    <div v-else-if="!hasData" class="chart-empty">{{ emptyText }}</div>
    <div v-else class="chart-body">
      <slot />
    </div>

    <footer v-if="$slots.legend" class="legend-row">
      <slot name="legend" />
    </footer>
  </article>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: "",
  },
  meta: {
    type: String,
    default: "",
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
  hasData: {
    type: Boolean,
    default: false,
  },
  loadingText: {
    type: String,
    default: "loading chart...",
  },
  emptyText: {
    type: String,
    default: "no data yet",
  },
});
</script>

<style scoped>
.chart-card {
  border: 1px solid var(--line2);
  border-radius: var(--radius);
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
}

.chart-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--line2);
  padding-bottom: 8px;
}

.chart-header h3 {
  margin: 0;
  text-transform: lowercase;
  font-size: 1.22rem;
  font-weight: 400;
}

.chart-subtitle {
  margin: 2px 0 0;
  color: var(--muted);
  text-transform: lowercase;
  font-size: 0.92rem;
}

.chart-meta {
  color: var(--muted);
  font-size: 0.88rem;
  text-transform: lowercase;
  white-space: nowrap;
}

.chart-controls {
  margin-bottom: 10px;
}

.chart-empty {
  border: 1px dashed var(--line2);
  border-radius: 8px;
  padding: 14px;
  color: var(--muted);
  text-transform: lowercase;
}

.chart-body {
  min-height: 220px;
}

.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

@media (max-width: 430px) {
  .chart-card {
    padding: 10px 8px;
  }

  .chart-header h3 {
    font-size: 1.08rem;
  }

  .chart-meta {
    font-size: 0.78rem;
  }
}
</style>
