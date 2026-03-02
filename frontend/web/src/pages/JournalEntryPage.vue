<template>
  <main class="screen">
    <header class="header">
      <h1 class="title">{{ displayDate }}</h1>

      <div class="actions">
        <button class="btn" type="button" @click="saveLocal">SAVE [CTRL+S]</button>
        <button class="btn" type="button" @click="exportTxt">EXPORT</button>
      </div>
    </header>

    <section class="panel">
      <textarea
        v-model="text"
        class="textarea"
        placeholder="input text here....."
        :maxlength="maxLen"
        @keydown.ctrl.s.prevent="saveLocal"
        @keydown.meta.s.prevent="saveLocal"
      />

      <div class="footer">
        <div class="meta">
          <span>{{ text.length }}/{{ maxLen }}</span>
          <span v-if="status" class="status">{{ status }}</span>
        </div>

        <button class="btn primary" :disabled="isSubmitting || !text.trim()" @click="submit">
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

const text = ref("");
const status = ref("");
const isSubmitting = ref(false);
const maxLen = 8000;

const today = new Date();
const displayDate = computed(() =>
  today.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })
);

const storageKey = `homelab:journal:${today.toISOString().slice(0, 10)}`;

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

function exportTxt() {
  const name = `journal_${today.toISOString().slice(0, 10)}.txt`;
  const blob = new Blob([text.value], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
  flash("EXPORTED");
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
    flash("SUBMITTED");
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
}

.title {
  margin: 0;
  font-size: clamp(28px, 4vw, 52px);
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
}

.textarea {
  width: 100%;
  min-height: clamp(360px, 62vh, 760px);
  resize: none;
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

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn.primary {
  padding: 12px 16px;
  border-color: rgba(255, 255, 255, 0.35);
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
}

.vignette {
  pointer-events: none;
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(0,0,0,0) 35%, rgba(0,0,0,0.6) 100%);
  opacity: 0.9;
}
</style>