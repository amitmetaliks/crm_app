<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-5 pt-6 text-white">
			<h1 class="text-xl font-bold">Analytics</h1>
			<p class="text-sm text-navy-200">{{ d.period || "This month" }}</p>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<EmptyState v-if="!session.isSalesManager" title="Managers only" />
			<template v-else>
				<Skeleton v-if="loading" :count="4" />
				<template v-else>
					<div class="grid grid-cols-2 gap-3">
						<div class="aa-card"><p class="text-2xl font-bold text-navy-700 dark:text-white">{{ d.conversion_pct }}%</p><p class="text-xs text-gray-400">Order conversion</p></div>
						<div class="aa-card"><p class="text-2xl font-bold text-navy-700 dark:text-white">{{ d.adherence_pct }}%</p><p class="text-xs text-gray-400">Beat adherence</p></div>
						<div class="aa-card"><p class="text-2xl font-bold text-navy-700 dark:text-white">{{ d.attendance_today }}</p><p class="text-xs text-gray-400">Present today</p></div>
						<div class="aa-card"><p class="text-2xl font-bold text-navy-700 dark:text-white">{{ d.visits_completed }}</p><p class="text-xs text-gray-400">Visits completed</p></div>
					</div>

					<div class="aa-card">
						<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">Receivables</p>
						<div class="flex justify-between text-sm"><span class="text-gray-500">Outstanding</span><span class="font-semibold text-navy-700 dark:text-white">₹{{ fmt(d.ar_total) }}</span></div>
						<div class="flex justify-between text-sm"><span class="text-gray-500">Overdue</span><span class="font-semibold text-red-600">₹{{ fmt(d.ar_overdue) }}</span></div>
					</div>

					<div class="aa-card">
						<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">Expense claims</p>
						<div class="flex justify-between text-sm"><span class="text-gray-500">Pending approval</span><span class="font-semibold text-navy-700 dark:text-white">{{ d.expense_pending }} · ₹{{ fmt(d.expense_pending_amount) }}</span></div>
					</div>

					<router-link :to="{ name: 'Team' }" class="aa-card block text-center text-sm font-medium text-saffron">View team activity →</router-link>
				</template>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { session } from "../data/session"
import { call } from "../data/api"

const d = ref({})
const loading = ref(true)
function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }
onMounted(async () => {
	if (!session.isSalesManager) { loading.value = false; return }
	try { d.value = await call("crm_app.dashboards.get_analytics") } finally { loading.value = false }
})
</script>
