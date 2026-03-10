import { createRouter, createWebHistory } from "vue-router";
import DashboardPage from "../pages/DashboardPage.vue";
import JournalEntryPage from "../pages/JournalEntryPage.vue";
import JournalInsightsPage from "../pages/JournalInsightsPage.vue";
import BillsPage from "../pages/BillsPage.vue";
import MileagePage from "../pages/MileagePage.vue";
import HealthPage from "../pages/HealthPage.vue";
import InsightsPage from "../pages/InsightsPage.vue";

const routes = [
  { path: "/", component: DashboardPage },

  { path: "/journal", component: JournalEntryPage },
  { path: "/journal/insights", component: JournalInsightsPage },
  { path: "/bills", component: BillsPage },

  // AI insights
  { path: "/insights", component: InsightsPage },

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