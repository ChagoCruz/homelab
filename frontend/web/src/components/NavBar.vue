<template>
  <header class="top">
    <RouterLink to="/" class="brand">HOMELAB</RouterLink>

    <nav class="nav">
      <RouterLink to="/journal">JOURNAL</RouterLink>
      <RouterLink to="/bills">BILLS</RouterLink>
      <RouterLink to="/insights">INSIGHTS</RouterLink>

      <div class="dropdown" ref="dropdownEl">
        <button
          class="dropbtn"
          type="button"
          @click="open = !open"
          :aria-expanded="open"
        >
          STATS <span class="caret">▾</span>
        </button>

        <div class="menu" :class="{ open }">
          <RouterLink class="item" to="/stats/health" @click="open = false">
            HEALTH
          </RouterLink>
          <RouterLink class="item" to="/stats/car" @click="open = false">
            CAR
          </RouterLink>
        </div>
      </div>
    </nav>
  </header>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

const open = ref(false);
const dropdownEl = ref(null);

function onDocClick(e) {
  if (!open.value) return;
  const el = dropdownEl.value;
  if (!el) return;

  if (!el.contains(e.target)) {
    open.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", onDocClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", onDocClick);
});
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
  align-items: center;
}

a,
.dropbtn {
  color: var(--fg);
  text-decoration: none;
  border: 1px solid transparent;
  padding: 6px 10px;
  border-radius: 8px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  background: transparent;
  cursor: pointer;
  font: inherit;
  box-sizing: border-box;
}

a.router-link-active {
  border-color: var(--line);
  background: rgba(255, 255, 255, 0.06);
}

.dropdown {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.caret {
  opacity: 0.9;
  margin-left: 6px;
}

.menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 180px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(10, 10, 10, 0.92);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  padding: 8px;
  display: none;
  z-index: 50;
}

.menu.open {
  display: grid;
  gap: 6px;
}

.item {
  display: block;
  padding: 10px 10px;
  border-radius: 8px;
  border: 1px solid transparent;
}

.item:hover {
  border-color: var(--line);
  background: rgba(255, 255, 255, 0.06);
}
</style>