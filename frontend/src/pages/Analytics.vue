<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-5 pt-6 text-white">
			<h1 class="text-xl font-bold">{{ $t("Analytics") }}</h1>
			<p class="text-sm text-navy-200">{{ d.period || "This month" }}</p>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<EmptyState v-if="!session.isSalesManager" :title='$t("Managers only")' />
			<template v-else>
				<Skeleton v-if="loading" :count="4" />
				<template v-else>
					<div class="grid grid-cols-2 gap-3">
						<div class="aa-card"><p class="text-2xl font-bold text-navy-700 dark:text-white">{{ d.conversion_pct }}%</p><p class="text-xs text-gray-400">{{ $t("Order conversion") }}</p></div>
						<div class="aa-card"><p class="text-2xl font-bold text-navy-700 dark:text-white">{{ d.adherence_pct }}%</p><p class="text-xs text-gray-400">{{ $t("Beat adherence") }}</p></div>
						<div class="aa-card"><p class="text-2xl font-bold text-navy-700 dark:text-white">{{ d.attendance_today }}</p><p class="text-xs text-gray-400">{{ $t("Present today") }}</p></div>
						<div class="aa-card"><p class="text-2xl font-bold text-navy-700 dark:text-white">{{ d.visits_completed }}</p><p class="text-xs text-gray-400">{{ $t("Visits completed") }}</p></div>
					</div>

					<div class="aa-card">
						<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Receivables") }}</p>
						<div class="flex justify-between text-sm"><span class="text-gray-500">{{ $t("Outstanding") }}</span><span class="font-semibold text-navy-700 dark:text-white">{{ inrShort(d.ar_total) }}</span></div>
						<div class="flex justify-between text-sm"><span class="text-gray-500">{{ $t("Overdue") }}</span><span class="font-semibold text-red-600">{{ inrShort(d.ar_overdue) }}</span></div>
					</div>

					<div class="aa-card">
						<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Expense claims") }}</p>
						<div class="flex justify-between text-sm"><span class="text-gray-500">{{ $t("Pending approval") }}</span><span class="font-semibold text-navy-700 dark:text-white">{{ d.expense_pending }} · {{ inrShort(d.expense_pending_amount) }}</span></div>
					</div>

					<div v-if="series.length" class="aa-card">
						<p class="mb-3 text-sm font-semibold text-navy-600 dark:text-navy-200">My visits — last 7 days</p>
						<BarChart :data="series" />
					</div>

					<div v-if="products.length" class="aa-card">
						<p class="mb-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Top products (by order value, this month)") }}</p>
						<DonutChart :items="products" :center-top="String(products.length)" center-sub="products" />
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
import DonutChart from "../components/DonutChart.vue"
import BarChart from "../components/BarChart.vue"
import { session } from "../data/session"
import { call } from "../data/api"
import { inrShort } from "../utils/money"

const d = ref({})
const products = ref([])
const series = ref([])
const loading = ref(true)
function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }
onMounted(async () => {
	if (!session.isSalesManager) { loading.value = false; return }
	try {
		d.value = await call("crm_app.dashboards.get_analytics")
		products.value = (await call("crm_app.sfa.get_top_products", { scope: "team" })).items || []
		series.value = (await call("crm_app.sfa.get_productivity_series")).series || []
	} finally { loading.value = false }
})
</script>
