import { createRouter, createWebHistory } from "vue-router";
import JournalEntryPage from "../pages/JournalEntryPage.vue";
import BillsPage from "../pages/BillsPage.vue";
import MileagePage from "../pages/MileagePage.vue";

const routes = [
  { path: "/", redirect: "/journal" },
  { path: "/journal", component: JournalEntryPage },
  { path: "/bills", component: BillsPage },
  { path: "/mileage", component: MileagePage }
];

export default createRouter({
  history: createWebHistory(),
  routes
});