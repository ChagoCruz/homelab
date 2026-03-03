import { createRouter, createWebHistory } from "vue-router";

import JournalEntryPage from "../pages/JournalEntryPage.vue";
import BillsPage from "../pages/BillsPage.vue";
import MileagePage from "../pages/MileagePage.vue";
import HealthPage from "../pages/HealthPage.vue";

const routes = [
  { path: "/", redirect: "/journal" },

  { path: "/journal", component: JournalEntryPage },
  { path: "/bills", component: BillsPage },

  // keep old route working
  { path: "/mileage", component: MileagePage },

  // new "Stats" routes
  { path: "/stats", redirect: "/stats/health" },
  { path: "/stats/health", component: HealthPage },
  { path: "/stats/car", component: MileagePage },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});