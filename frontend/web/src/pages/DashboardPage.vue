<template>
  <main class="page-shell">
    <section class="panel">
      <div class="panel-header">
        <h1>homelab</h1>
        <span class="panel-subtle">main dashboard</span>
      </div>

      <div class="dashboard-grid">
        <section class="panel-block">
          <div class="block-header">
            <h2>system</h2>
          </div>
          <div class="kv-list">
            <div class="kv-row">
              <span class="kv-key">status</span>
              <span class="kv-value">online</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">mode</span>
              <span class="kv-value">life terminal</span>
            </div>
            <div class="kv-row">
              <span class="kv-key">ai</span>
              <span class="kv-value">ollama / gemma3:4b</span>
            </div>
          </div>
        </section>

        <AIInsightPanel />

        <section class="panel-block">
          <div class="block-header">
            <h2>quick links</h2>
          </div>

          <div class="quick-links">
            <RouterLink to="/journal" class="terminal-link">journal</RouterLink>
            <RouterLink to="/bills" class="terminal-link">bills</RouterLink>
            <RouterLink to="/mileage" class="terminal-link">mileage</RouterLink>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import AIInsightPanel from "../components/AIInsightPanel.vue";
</script>

<style scoped>
.page-shell {
  min-height: 100vh;
  padding: clamp(16px, 3vw, 32px);
  box-sizing: border-box;
}

.panel {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: var(--pad);
  background: rgba(255, 255, 255, 0.02);
}

.panel-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 12px;
  margin-bottom: 18px;
}

.panel-header h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 400;
  text-transform: lowercase;
}

.panel-subtle {
  color: var(--muted);
  font-size: 1.1rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.panel-block {
  border: 1px solid var(--line2);
  border-radius: var(--radius);
  padding: 16px;
  background: rgba(255, 255, 255, 0.01);
}

.block-header {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line2);
}

.block-header h2 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 400;
  text-transform: lowercase;
}

.kv-list {
  display: grid;
  gap: 10px;
}

.kv-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px dotted var(--line2);
  padding-bottom: 6px;
}

.kv-key {
  color: var(--muted);
  text-transform: lowercase;
}

.kv-value {
  text-align: right;
  text-transform: lowercase;
}

.quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.terminal-link {
  display: inline-block;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--fg);
  text-decoration: none;
  text-transform: lowercase;
}

.terminal-link:hover {
  background: rgba(255, 255, 255, 0.06);
}

@media (min-width: 900px) {
  .dashboard-grid {
    grid-template-columns: 1fr 1.2fr;
  }

  .dashboard-grid > :last-child {
    grid-column: 1 / -1;
  }
}
</style>