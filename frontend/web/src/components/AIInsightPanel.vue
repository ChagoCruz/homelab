<template>
  <section class="panel-block ai-block" :class="{ compact }">
    <div class="block-header ai-header">
      <h2>ai insight</h2>
      <span class="ai-status">{{ loading ? "loading..." : "ready" }}</span>
    </div>

    <div v-if="error" class="terminal-message error">
      {{ error }}
    </div>

    <div v-else-if="loading" class="terminal-message">
      fetching latest insight...
    </div>

    <div v-else-if="insight" class="insight-wrap" :class="{ compact }">
      <div class="meta-row">
        <span>type: {{ insight.insight_type || insight.type || "weekly_report" }}</span>
        <span>
          {{ formatDate(insight.period_start) }} → {{ formatDate(insight.period_end) }}
        </span>
      </div>

      <p v-if="compact" class="compact-text">{{ compactSummary }}</p>
      <pre v-else class="insight-text">{{ insight.insight_text || insight.text }}</pre>
    </div>

    <div v-else class="terminal-message">
      no insight generated yet.
    </div>

    <div class="button-row" :class="{ compact }">
      <RouterLink v-if="compact" to="/insights" class="terminal-link">view details</RouterLink>

      <button
        v-if="showGenerate"
        class="terminal-button"
        :disabled="generating"
        @click="generateWeekly"
      >
        {{ generating ? "generating..." : "generate weekly insight" }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

defineProps({
  compact: {
    type: Boolean,
    default: false,
  },
  showGenerate: {
    type: Boolean,
    default: true,
  },
});

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const insight = ref(null);
const loading = ref(false);
const generating = ref(false);
const error = ref("");

const compactSummary = computed(() => {
  const raw = (insight.value?.insight_text || insight.value?.text || "").replace(/\s+/g, " ").trim();
  if (!raw) return "No summary available yet.";

  const limit = 180;
  return raw.length > limit ? `${raw.slice(0, limit).trimEnd()}...` : raw;
});

async function fetchLatestInsight() {
  loading.value = true;
  error.value = "";

  try {
    const res = await fetch(`${API_BASE}/insights/latest`);
    if (!res.ok) {
      throw new Error("failed to load latest insight");
    }

    const data = await res.json();

    if (data?.message === "No insights yet") {
      insight.value = null;
    } else {
      insight.value = data;
    }
  } catch (err) {
    error.value = err.message || "unable to load insight";
  } finally {
    loading.value = false;
  }
}

async function generateWeekly() {
  generating.value = true;
  error.value = "";

  try {
    const res = await fetch(`${API_BASE}/insights/weekly`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!res.ok) {
      throw new Error("failed to generate weekly insight");
    }

    await res.json();
    await fetchLatestInsight();
  } catch (err) {
    error.value = err.message || "unable to generate insight";
  } finally {
    generating.value = false;
  }
}

function formatDate(value) {
  if (!value) return "--";
  return value;
}

onMounted(fetchLatestInsight);
</script>

<style scoped>
.ai-block {
  min-height: 260px;
}

.ai-block.compact {
  min-height: 0;
}

.ai-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.ai-status {
  color: var(--muted);
  font-size: 1rem;
  text-transform: lowercase;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  color: var(--muted);
  font-size: 1rem;
  border-bottom: 1px dotted var(--line2);
  padding-bottom: 8px;
}

.insight-wrap {
  display: grid;
  gap: 12px;
}

.compact-text {
  margin: 0;
  color: rgba(255, 255, 255, 0.92);
  font-size: 1.05rem;
  line-height: 1.3;
}

.insight-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 1.15rem;
  line-height: 1.35;
}

.terminal-message {
  color: var(--muted);
  min-height: 80px;
}

.error {
  color: #fff;
  opacity: 0.85;
}

.button-row {
  margin-top: 16px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.button-row.compact {
  margin-top: 10px;
}

.terminal-button,
.terminal-link {
  background: transparent;
  color: var(--fg);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 12px;
  font: inherit;
  text-transform: lowercase;
  text-decoration: none;
  cursor: pointer;
}

.terminal-button:hover:not(:disabled),
.terminal-link:hover {
  background: rgba(255, 255, 255, 0.06);
}

.terminal-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 430px) {
  .meta-row {
    font-size: 0.86rem;
  }

  .compact-text {
    font-size: 0.92rem;
  }

  .terminal-button,
  .terminal-link {
    font-size: 0.86rem;
    padding: 7px 10px;
  }
}
</style>
