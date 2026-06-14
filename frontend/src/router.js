import { createRouter, createWebHistory } from "vue-router"
import { session, refreshMe } from "./data/session"

const routes = [
	{ path: "/", redirect: "/dashboard" },
	{ path: "/login", name: "Login", component: () => import("./pages/Login.vue"), meta: { public: true } },
	{ path: "/dashboard", name: "Dashboard", component: () => import("./pages/Dashboard.vue") },
	{ path: "/new-visit", name: "NewVisit", component: () => import("./pages/NewVisit.vue") },
	{ path: "/visits", name: "Visits", component: () => import("./pages/Visits.vue") },
	{ path: "/visit/:name", name: "VisitDetail", component: () => import("./pages/VisitDetail.vue"), props: true },
	{ path: "/customers", name: "Customers", component: () => import("./pages/Customers.vue") },
	{ path: "/customer/:name", name: "CustomerDetail", component: () => import("./pages/CustomerDetail.vue"), props: true },
	{ path: "/beat", name: "Beat", component: () => import("./pages/Beat.vue") },
	{ path: "/targets", name: "Targets", component: () => import("./pages/Targets.vue") },
	{ path: "/collections", name: "Collections", component: () => import("./pages/Collections.vue") },
	{ path: "/notifications", name: "Notifications", component: () => import("./pages/Notifications.vue") },
	{ path: "/more", name: "More", component: () => import("./pages/More.vue") },
]

const router = createRouter({
	history: createWebHistory("/amit-crm/"),
	routes,
})

router.beforeEach(async (to) => {
	if (to.meta.public) {
		if (to.name === "Login" && session.isLoggedIn) return { name: "Dashboard" }
		return true
	}
	if (!session.isLoggedIn) return { name: "Login" }
	if (!session.gateLoaded) await refreshMe()
	return true
})

export default router
