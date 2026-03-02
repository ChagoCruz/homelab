<template>
  <header class="top">
    <div class="brand">HOMELAB</div>
    <nav class="nav">
      <RouterLink to="/journal">JOURNAL</RouterLink>
      <RouterLink to="/bills">BILLS</RouterLink>
      <RouterLink to="/mileage">MILEAGE</RouterLink>
    </nav>
  </header>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style scoped>
.top {
  padding: var(--pad);
  border-bottom: 1px solid var(--line);
  display: flex;
  gap: 18px;
  align-items: center;
  justify-content: space-between;
}

.brand {
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.nav {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

a {
  color: var(--fg);
  text-decoration: none;
  border: 1px solid transparent;
  padding: 6px 10px;
  border-radius: 8px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

a.router-link-active {
  border-color: var(--line);
  background: rgba(255,255,255,0.06);
}
</style>