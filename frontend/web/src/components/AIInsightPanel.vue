<template>
  <section class="panel-block ai-block">
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

    <div v-else-if="insight" class="insight-wrap">
      <div class="meta-row">
        <span>type: {{ insight.insight_type || insight.type || "weekly_report" }}</span>
        <span>
          {{ formatDate(insight.period_start) }} → {{ formatDate(insight.period_end) }}
        </span>
      </div>

      <pre class="insight-text">{{ insight.insight_text || insight.text }}</pre>
    </div>

    <div v-else class="terminal-message">
      no insight generated yet.
    </div>

    <div class="button-row">
      <button class="terminal-button" :disabled="generating" @click="generateWeekly">
        {{ generating ? "generating..." : "generate weekly insight" }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

const insight = ref(null);
const loading = ref(false);
const generating = ref(false);
const error = ref("");

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
}

.terminal-button {
  background: transparent;
  color: var(--fg);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 14px;
  font: inherit;
  text-transform: lowercase;
  cursor: pointer;
}

.terminal-button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.06);
}

.terminal-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>