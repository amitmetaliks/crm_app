import { createRouter, createWebHistory } from "vue-router"
import { session, refreshMe } from "./data/session"
import { lock } from "./data/lock"

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
	{ path: "/leads", name: "Leads", component: () => import("./pages/Leads.vue") },
	{ path: "/team", name: "Team", component: () => import("./pages/Team.vue") },
	{ path: "/attendance", name: "Attendance", component: () => import("./pages/Attendance.vue") },
	{ path: "/expense", name: "Expense", component: () => import("./pages/Expense.vue") },
	{ path: "/leave", name: "Leave", component: () => import("./pages/Leave.vue") },
	{ path: "/salary", name: "Salary", component: () => import("./pages/Salary.vue") },
	{ path: "/approvals", name: "Approvals", component: () => import("./pages/Approvals.vue") },
	{ path: "/analytics", name: "Analytics", component: () => import("./pages/Analytics.vue") },
	{ path: "/kra", name: "Kra", component: () => import("./pages/Kra.vue") },
	{ path: "/timeline", name: "Timeline", component: () => import("./pages/Timeline.vue") },
	{ path: "/route", name: "Route", component: () => import("./pages/Route.vue") },
	{ path: "/conveyance", name: "Conveyance", component: () => import("./pages/Conveyance.vue") },
	{ path: "/insights", name: "Insights", component: () => import("./pages/Insights.vue") },
	{ path: "/schemes", name: "Schemes", component: () => import("./pages/Schemes.vue") },
	{ path: "/team-map", name: "TeamMap", component: () => import("./pages/TeamMap.vue") },
	{ path: "/lock", name: "Lock", component: () => import("./pages/Lock.vue"), meta: { public: true } },
	{ path: "/notifications", name: "Notifications", component: () => import("./pages/Notifications.vue") },
	{ path: "/more", name: "More", component: () => import("./pages/More.vue") },
]

const router = createRouter({
	history: createWebHistory("/amit-crm/"),
	routes,
})

router.beforeEach(async (to) => {
	// App lock takes precedence once the user is signed in.
	if (lock.locked && session.isLoggedIn && to.name !== "Lock") return { name: "Lock" }
	if (to.meta.public) {
		if (to.name === "Login" && session.isLoggedIn) return { name: "Dashboard" }
		return true
	}
	if (!session.isLoggedIn) return { name: "Login" }
	if (!session.gateLoaded) await refreshMe()
	return true
})

export default router
