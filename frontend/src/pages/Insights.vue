<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<h1 class="text-lg font-semibold">{{ $t("Smart Insights") }}</h1>
			<div v-if="session.isSalesManager" class="mt-2 flex gap-2">
				<button @click="setScope('mine')" class="rounded-full px-4 py-2 text-xs font-medium" :class="scope === 'mine' ? 'bg-saffron text-navy-700' : 'bg-white/10'">{{ $t("Mine") }}</button>
				<button @click="setScope('team')" class="rounded-full px-4 py-2 text-xs font-medium" :class="scope === 'team' ? 'bg-saffron text-navy-700' : 'bg-white/10'">{{ $t("Team") }}</button>
			</div>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<Skeleton v-if="loading" :count="3" />
			<template v-else>
				<!-- Forecast -->
				<div class="aa-card">
					<div class="mb-2 flex items-center justify-between">
						<p class="text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Sales forecast (next month)") }}</p>
						<span class="text-lg font-bold text-saffron">{{ inrShort(forecast.forecast) }}</span>
					</div>
					<BarChart v-if="histBars.length" :data="histBars" />
					<p v-else class="text-xs text-gray-400">{{ $t("No sales history yet.") }}</p>
					<p class="mt-2 text-xs text-gray-400">{{ $t("Based on the average of recent months' booked orders.") }}</p>
				</div>

				<!-- Churn risk -->
				<div>
					<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">At-risk dealers (no activity 30+ days)</h2>
					<EmptyState v-if="!churn.length" :title='$t("All dealers active")' :subtitle='$t("No dealers are slipping — nice work.")' />
					<div v-else class="space-y-2">
						<router-link v-for="c in churn" :key="c.customer" :to="{ name: 'CustomerDetail', params: { name: c.customer } }" class="aa-card flex items-center justify-between">
							<div class="min-w-0">
								<p class="truncate font-semibold text-navy-700 dark:text-white">{{ c.customer_name }}</p>
								<p class="text-xs text-gray-400">{{ c.last_activity ? "Last activity " + fmtDate(c.last_activity) : "No recorded activity" }}</p>
							</div>
							<span class="shrink-0 rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-600">
								{{ c.days_since != null ? c.days_since + "d" : "never" }}
							</span>
						</router-link>
					</div>
				</div>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import BarChart from "../components/BarChart.vue"
import { session } from "../data/session"
import { call } from "../data/api"
import { inrShort } from "../utils/money"

const scope = ref("mine")
const churn = ref([])
const forecast = ref({ history: [], forecast: 0 })
const loading = ref(true)

const histBars = computed(() => (forecast.value.history || []).map((h) => ({ label: h.label, achieved: Math.round(h.value) })))

function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }
function fmtDate(d) { return d ? dayjs(d).format("DD MMM YYYY") : "" }

async function load() {
	loading.value = true
	try {
		churn.value = (await call("crm_app.insights.churn_risk", { scope: scope.value })) || []
		forecast.value = (await call("crm_app.insights.sales_forecast", { scope: scope.value })) || { history: [], forecast: 0 }
	} finally { loading.value = false }
}
function setScope(s) { scope.value = s; load() }
onMounted(load)
</script>
