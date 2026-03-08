<template>
  <main class="page">
    <section class="panel">
      <header class="panel-header">
        <h1>INSIGHTS</h1>
        <span class="sub">AI generated life summaries</span>
      </header>

      <AIInsightPanel />
    </section>
  </main>
</template>

<script setup>
import AIInsightPanel from "../components/AIInsightPanel.vue";
</script>

<style scoped>
.page {
  padding: var(--pad);
}

.panel {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 10px;
}

h1 {
  letter-spacing: 0.12em;
}

.sub {
  color: var(--muted);
}
</style>