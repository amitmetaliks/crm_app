<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-5 pt-6 text-white">
			<h1 class="text-xl font-bold">{{ $t("Team Activity") }}</h1>
			<p class="text-sm text-navy-200">{{ today }}</p>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<EmptyState v-if="!session.isSalesManager" :title='$t("Managers only")' :subtitle='$t("This view is for sales managers.")' />

			<template v-else>
				<Skeleton v-if="loading" :count="4" />
				<template v-else>
					<div class="aa-card text-center">
						<p class="text-3xl font-bold text-navy-700 dark:text-white">{{ data.today_total }}</p>
						<p class="text-xs text-gray-400">visits across the team today</p>
					</div>

					<div>
						<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Today's coverage") }}</h2>
						<EmptyState v-if="!data.coverage.length" :title='$t("No visits yet today")' />
						<div v-else class="space-y-2">
							<div v-for="(r, i) in data.coverage" :key="i" class="aa-card flex items-center justify-between">
								<span class="text-sm font-medium text-navy-700 dark:text-white">{{ r.sales_person_name }}</span>
								<span class="rounded-full bg-saffron/15 px-2.5 py-1 text-xs font-semibold text-saffron">{{ r.count }} visit(s)</span>
							</div>
						</div>
					</div>

					<div>
						<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">This month — leaderboard</h2>
						<div class="aa-card divide-y divide-gray-100 !p-0 dark:divide-navy-700">
							<div v-for="(r, i) in data.leaderboard" :key="i" class="flex items-center justify-between px-4 py-3">
								<span class="flex items-center gap-2 text-sm text-navy-700 dark:text-white">
									<span class="flex h-6 w-6 items-center justify-center rounded-full bg-navy-100 text-xs font-bold text-navy-700">{{ i + 1 }}</span>
									{{ r.sales_person_name }}
								</span>
								<span class="text-sm text-gray-500">{{ r.completed }} done / {{ r.visits }}</span>
							</div>
						</div>
					</div>

					<div>
						<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Recent team visits") }}</h2>
						<div class="space-y-2">
							<router-link v-for="v in data.recent" :key="v.name" :to="{ name: 'VisitDetail', params: { name: v.name } }" class="aa-card flex items-center justify-between">
								<div class="min-w-0">
									<p class="truncate text-sm font-medium text-navy-700 dark:text-white">{{ v.party_display }}</p>
									<p class="text-xs text-gray-400">{{ v.sales_person_name }} · {{ v.visit_purpose }}</p>
								</div>
								<span class="text-xs text-gray-400">{{ fmtDate(v.visit_date) }}</span>
							</router-link>
						</div>
					</div>
				</template>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { session } from "../data/session"
import { call } from "../data/api"

const data = ref({ today_total: 0, coverage: [], leaderboard: [], recent: [] })
const loading = ref(true)
const today = dayjs().format("ddd, DD MMM YYYY")

function fmtDate(d) { return d ? dayjs(d).format("DD MMM") : "" }

onMounted(async () => {
	if (!session.isSalesManager) { loading.value = false; return }
	try {
		data.value = await call("crm_app.dashboards.get_team_overview", {})
	} finally {
		loading.value = false
	}
})
</script>
