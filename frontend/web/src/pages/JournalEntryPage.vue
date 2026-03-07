<template>
  <main class="screen">
    <header class="header">
      <h1 class="title">{{ displayDate }}</h1>

      <div class="actions">
        <button class="btn" :class="{ active: mode === 'reflect' }" type="button" @click="openReflect">
          REFLECT
        </button>
        <button class="btn" :class="{ active: mode === 'entry' }" type="button" @click="openEntry">
          ENTRY
        </button>
      </div>
    </header>

    <section class="panel">
      <textarea
        v-if="mode === 'entry'"
        v-model="text"
        class="textarea"
        placeholder="input text here....."
        :maxlength="maxLen"
        @keydown.ctrl.s.prevent="saveLocal"
        @keydown.meta.s.prevent="saveLocal"
      />

      <div v-else class="history">
        <p v-if="isLoadingEntries" class="history-empty">Loading entries...</p>
        <p v-else-if="historyError" class="history-empty">{{ historyError }}</p>
        <p v-else-if="sortedEntries.length === 0" class="history-empty">No submitted entries yet.</p>

        <template v-else>
          <article
            v-for="(entry, idx) in sortedEntries"
            :key="`${entry.entry_date}-${idx}`"
            class="history-entry"
          >
            <h2 class="history-date">{{ formatDate(entry.entry_date) }}</h2>
            <p class="history-content">{{ entry.content }}</p>
          </article>
        </template>
      </div>

      <div class="footer" :class="{ reflect: mode === 'reflect' }">
        <div class="meta">
          <span v-if="mode === 'entry'">{{ text.length }}/{{ maxLen }}</span>
          <span v-else>{{ sortedEntries.length }} ENTRIES</span>
          <span v-if="status" class="status">{{ status }}</span>
        </div>

        <button
          v-if="mode === 'entry'"
          class="btn primary"
          :disabled="isSubmitting || !text.trim()"
          @click="submit"
        >
          {{ isSubmitting ? "SUBMITTING..." : "SUBMIT" }}
        </button>
      </div>
    </section>

    <div class="scanlines" aria-hidden="true"></div>
    <div class="vignette" aria-hidden="true"></div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";

const mode = ref("entry");
const text = ref("");
const entries = ref([]);
const status = ref("");
const isSubmitting = ref(false);
const isLoadingEntries = ref(false);
const historyError = ref("");
const hasLoadedEntries = ref(false);
const maxLen = 8000;

const today = new Date();
const displayDate = computed(() =>
  today.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })
);
const sortedEntries = computed(() =>
  [...entries.value].sort((a, b) => entryTimestamp(b.entry_date) - entryTimestamp(a.entry_date))
);

const storageKey = `homelab:journal:${getLocalDateString()}`;

onMounted(() => {
  const saved = localStorage.getItem(storageKey);
  if (saved) text.value = saved;
});

function flash(msg) {
  status.value = msg;
  window.clearTimeout(flash._t);
  flash._t = window.setTimeout(() => (status.value = ""), 2000);
}

function saveLocal() {
  localStorage.setItem(storageKey, text.value);
  flash("SAVED");
}

function openEntry() {
  mode.value = "entry";
}

async function openReflect() {
  mode.value = "reflect";
  await loadEntries();
}

function parseEntryDate(value) {
  if (typeof value === "string") {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
    if (match) {
      return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    }
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function entryTimestamp(value) {
  const date = parseEntryDate(value);
  return date ? date.getTime() : 0;
}

function formatDate(value) {
  const date = parseEntryDate(value);
  if (!date) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

async function loadEntries(force = false) {
  if (isLoadingEntries.value) return;
  if (hasLoadedEntries.value && !force) return;

  isLoadingEntries.value = true;
  historyError.value = "";

  const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

  try {
    const res = await fetch(`${baseUrl}/journal/`);
    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    const data = await res.json();
    entries.value = Array.isArray(data) ? data : [];
    hasLoadedEntries.value = true;
  } catch (e) {
    historyError.value = `Unable to load entries: ${e.message}`;
  } finally {
    isLoadingEntries.value = false;
  }
}

function getLocalDateString() {
  const d = new Date();
  return (
    d.getFullYear() +
    "-" +
    String(d.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(d.getDate()).padStart(2, "0")
  );
}

async function submit() {
  isSubmitting.value = true;
  status.value = "";

  // IMPORTANT:
  // - local dev (running backend on host): http://localhost:8000
  // - docker compose (frontend container talking to api container): http://api:8000
  const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

  try {
    // Match your schema fields if needed; this is a safe starting payload.
    // Your JournalCreate likely has: date/content (or similar). Adjust once you confirm.
    const payload = {
      entry_date: getLocalDateString(),
      content: text.value
    };

    const res = await fetch(`${baseUrl}/journal/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const msg = await res.text().catch(() => "");
      throw new Error(msg || `HTTP ${res.status}`);
    }

    localStorage.removeItem(storageKey);
    hasLoadedEntries.value = false;
    text.value = "";
    flash("SUBMITTED");
    window.setTimeout(() => window.location.reload(), 120);
  } catch (e) {
    flash(`ERROR: ${e.message}`);
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.screen {
  padding: var(--pad);
  position: relative;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
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
  font-size: clamp(28px, 4vw, 52px);
  color: var(--fg);
  letter-spacing: 0.12em;
  text-transform: uppercase;
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

.textarea {
  width: 100%;
  min-height: clamp(220px, 46vh, 520px);
  resize: none;
  box-sizing: border-box;
  background: transparent;
  color: var(--fg);
  border: 1px solid var(--line2);
  border-radius: calc(var(--radius) - 4px);
  padding: 14px;
  outline: none;
  font-size: clamp(18px, 2.6vw, 26px);
  line-height: 1.35;
  letter-spacing: 0.06em;
}

.textarea::placeholder {
  color: rgba(255, 255, 255, 0.35);
}

.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  border-top: 1px solid var(--line2);
  padding-top: 12px;
}

.meta {
  display: flex;
  gap: 16px;
  color: var(--muted);
  font-size: 16px;
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

.btn.active {
  background: rgba(255, 255, 255, 0.12);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn.primary {
  padding: 12px 16px;
  border-color: rgba(255, 255, 255, 0.35);
}

.history {
  min-height: clamp(360px, 62vh, 760px);
  border: 1px solid var(--line2);
  border-radius: calc(var(--radius) - 4px);
  overflow-y: auto;
  padding: 14px;
}

.history-empty {
  margin: 0;
  color: var(--muted);
  font-size: 18px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.history-entry {
  border-bottom: 1px solid var(--line2);
  padding-bottom: 14px;
  margin-bottom: 14px;
}

.history-entry:last-of-type {
  border-bottom: 0;
  margin-bottom: 0;
  padding-bottom: 0;
}

.history-date {
  margin: 0 0 8px;
  font-size: 16px;
  color: var(--fg);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.history-content {
  margin: 0;
  white-space: pre-wrap;
  color: var(--fg);
  font-size: clamp(18px, 2.2vw, 24px);
  line-height: 1.35;
  letter-spacing: 0.04em;
}

.footer.reflect {
  justify-content: flex-start;
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
</style>
