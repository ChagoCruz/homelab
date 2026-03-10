<template>
  <main class="screen">
    <header class="header">
      <div>
        <h1 class="title">JOURNAL INSIGHTS</h1>
        <p class="subtitle">Weekly summaries and recent analysis history</p>
      </div>

      <div class="actions">
        <button class="btn" type="button" :disabled="isGeneratingWeekly" @click="generateWeekly">
          {{ isGeneratingWeekly ? "GENERATING..." : "GENERATE WEEKLY" }}
        </button>
        <button class="btn" type="button" @click="goBack">
          BACK
        </button>
      </div>
    </header>

    <section class="panel">
      <div class="meta-row">
        <span v-if="status" class="status">{{ status }}</span>
        <span v-if="isLoadingHistory">LOADING HISTORY...</span>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>

      <section v-if="weeklyInsight" class="insight-section">
        <div class="section-header">
          <h2 class="section-title">THIS WEEK</h2>
          <span class="section-meta">
            {{ weeklyInsight.period_start }} → {{ weeklyInsight.period_end }}
          </span>
        </div>

        <div class="insight-card featured">
          <div class="card-meta">
            <span>{{ weeklyInsight.insight_type }}</span>
            <span>{{ formatDateTime(weeklyInsight.created_at) }}</span>
            <span v-if="weeklyInsight.entry_count != null">
              {{ weeklyInsight.entry_count }} ENTRIES
            </span>
          </div>
          <pre class="insight-text">{{ weeklyInsight.insight_text }}</pre>
        </div>
      </section>

      <section class="insight-section">
        <div class="section-header">
          <h2 class="section-title">RECENT HISTORY</h2>
          <span class="section-meta">{{ history.length }} ITEMS</span>
        </div>

        <p v-if="!isLoadingHistory && history.length === 0" class="empty-text">
          No journal insights yet.
        </p>

        <div v-else class="insight-list">
          <article
            v-for="item in history"
            :key="item.id"
            class="insight-card"
          >
            <div class="card-meta">
              <span>{{ item.insight_type }}</span>
              <span>{{ formatDateTime(item.created_at) }}</span>
              <span v-if="item.source_id">JOURNAL {{ item.source_id }}</span>
              <span v-if="item.period_start && item.period_end">
                {{ item.period_start }} → {{ item.period_end }}
              </span>
            </div>

            <pre class="insight-text">{{ item.insight_text }}</pre>
          </article>
        </div>
      </section>
    </section>

    <div class="scanlines" aria-hidden="true"></div>
    <div class="vignette" aria-hidden="true"></div>
  </main>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const history = ref([]);
const weeklyInsight = ref(null);
const isLoadingHistory = ref(false);
const isGeneratingWeekly = ref(false);
const status = ref("");
const error = ref("");

function flash(msg) {
  status.value = msg;
  window.clearTimeout(flash._t);
  flash._t = window.setTimeout(() => (status.value = ""), 2200);
}

function goBack() {
  router.push("/journal");
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

async function loadHistory() {
  isLoadingHistory.value = true;
  error.value = "";

  try {
    const res = await fetch(`${baseUrl}/insights/journal/history`);
    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const data = await res.json();
    history.value = Array.isArray(data) ? data : [];
  } catch (e) {
    error.value = `Unable to load journal insights: ${e.message}`;
  } finally {
    isLoadingHistory.value = false;
  }
}

async function generateWeekly() {
  isGeneratingWeekly.value = true;
  error.value = "";

  try {
    const res = await fetch(`${baseUrl}/insights/journal/weekly`, {
      method: "POST"
    });

    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const data = await res.json();
    weeklyInsight.value = data;
    flash("WEEKLY SUMMARY CREATED");
    await loadHistory();
  } catch (e) {
    error.value = `Unable to generate weekly summary: ${e.message}`;
    flash("GENERATION FAILED");
  } finally {
    isGeneratingWeekly.value = false;
  }
}

onMounted(async () => {
  await loadHistory();
});
</script>

<style scoped>
.screen {
  padding: var(--pad);
  position: relative;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 14px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}

.title {
  margin: 0;
  font-size: clamp(26px, 4vw, 46px);
  color: var(--fg);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.subtitle {
  margin: 8px 0 0;
  color: var(--muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 14px;
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.panel {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
  position: relative;
  z-index: 1;
}

.meta-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  color: var(--muted);
  font-size: 14px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.status {
  color: var(--fg);
}

.btn {
  border: 1px solid var(--line);
  background: transparent;
  color: var(--fg);
  padding: 10px 12px;
  border-radius: 8px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 16px;
  cursor: pointer;
}

.btn:hover {
  background: rgba(255, 255, 255, 0.06);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.insight-section + .insight-section {
  margin-top: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.section-title {
  margin: 0;
  color: var(--fg);
  font-size: 18px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.section-meta {
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.insight-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.insight-card {
  border: 1px solid var(--line2);
  border-radius: 10px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
}

.insight-card.featured {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--line);
}

.card-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.insight-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--fg);
  font-size: 15px;
  line-height: 1.45;
  font-family: inherit;
}

.empty-text,
.error-text {
  margin: 0;
  color: var(--muted);
  font-size: 16px;
  letter-spacing: 0.06em;
}

.error-text {
  color: #ffb3b3;
  margin-bottom: 12px;
}

/* CRT overlays */
.scanlines {
  pointer-events: none;
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    to bottom,
    rgba(255, 255, 255, 0.03),
    rgba(255, 255, 255, 0.03) 1px,
    rgba(0, 0, 0, 0) 3px,
    rgba(0, 0, 0, 0) 6px
  );
  mix-blend-mode: overlay;
  opacity: 0.35;
  z-index: 0;
}

.vignette {
  pointer-events: none;
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(0,0,0,0) 35%, rgba(0,0,0,0.6) 100%);
  opacity: 0.9;
  z-index: 0;
}

@media (max-width: 700px) {
  .header {
    flex-direction: column;
  }

  .actions {
    width: 100%;
    justify-content: flex-start;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>