<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<!-- Header -->
		<header class="bg-gradient-to-b from-navy-700 to-navy-600 px-5 pb-8 pt-6 text-white">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm text-navy-200">{{ greeting }}</p>
					<h1 class="text-xl font-bold">{{ session.employeeName || "Field Sales" }}</h1>
				</div>
				<router-link :to="{ name: 'Notifications' }" class="rounded-full bg-white/10 p-2.5">
					<Bell class="h-5 w-5" />
				</router-link>
			</div>
		</header>

		<div class="mx-auto -mt-5 max-w-xl space-y-4 px-4">
			<p
				v-if="session.gateLoaded && !session.hasEmployee"
				class="aa-card border border-amber-200 bg-amber-50 text-sm text-amber-800"
			>
				Your login isn't linked to an Employee record yet, so visits can't be saved. Please ask
				your admin to link your account.
			</p>

			<!-- Mark attendance -->
			<router-link :to="{ name: 'Attendance' }" class="aa-card flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="flex h-10 w-10 items-center justify-center rounded-full bg-navy-100 text-navy-700"><CalendarCheck class="h-5 w-5" /></div>
					<div>
						<p class="font-semibold text-navy-700 dark:text-white">Mark attendance</p>
						<p class="text-xs text-gray-400">Selfie + GPS check-in / out</p>
					</div>
				</div>
				<ChevronRight class="h-5 w-5 text-gray-300" />
			</router-link>

			<!-- Resume in-progress visit -->
			<router-link
				v-if="inProgress"
				:to="{ name: 'VisitDetail', params: { name: inProgress.name } }"
				class="aa-card flex items-center justify-between border border-saffron/30 bg-saffron/5"
			>
				<div>
					<p class="text-xs font-semibold uppercase tracking-wide text-saffron">Visit in progress</p>
					<p class="font-semibold text-navy-700 dark:text-white">{{ inProgress.party_display }}</p>
				</div>
				<ChevronRight class="h-5 w-5 text-saffron" />
			</router-link>

			<!-- Quick action -->
			<router-link
				:to="{ name: 'NewVisit' }"
				class="flex items-center justify-center gap-2 rounded-2xl bg-saffron px-4 py-4 font-semibold text-white shadow-lg shadow-saffron/30 active:scale-[0.99]"
			>
				<MapPin class="h-5 w-5" /> Start a Visit
			</router-link>

			<!-- Stats -->
			<div class="grid grid-cols-3 gap-3">
				<div class="aa-card text-center">
					<p class="text-2xl font-bold text-navy-700 dark:text-white">{{ stats.today }}</p>
					<p class="text-xs text-gray-400">Today</p>
				</div>
				<div class="aa-card text-center">
					<p class="text-2xl font-bold text-navy-700 dark:text-white">{{ stats.week }}</p>
					<p class="text-xs text-gray-400">This week</p>
				</div>
				<div class="aa-card text-center">
					<p class="text-2xl font-bold text-navy-700 dark:text-white">{{ stats.completed }}</p>
					<p class="text-xs text-gray-400">Completed</p>
				</div>
			</div>

			<!-- Quick access -->
			<div class="grid grid-cols-3 gap-3">
				<router-link :to="{ name: 'Beat' }" class="aa-card flex flex-col items-center gap-1 py-3 text-center">
					<Route class="h-6 w-6 text-saffron" /><span class="text-xs font-medium text-navy-700 dark:text-white">Beat</span>
				</router-link>
				<router-link :to="{ name: 'Targets' }" class="aa-card flex flex-col items-center gap-1 py-3 text-center">
					<Target class="h-6 w-6 text-saffron" /><span class="text-xs font-medium text-navy-700 dark:text-white">Targets</span>
				</router-link>
				<router-link :to="{ name: 'Collections' }" class="aa-card flex flex-col items-center gap-1 py-3 text-center">
					<IndianRupee class="h-6 w-6 text-saffron" /><span class="text-xs font-medium text-navy-700 dark:text-white">Collect</span>
				</router-link>
			</div>

			<!-- Recent visits -->
			<div>
				<div class="mb-2 flex items-center justify-between px-1">
					<h2 class="text-sm font-semibold text-navy-600 dark:text-navy-200">Recent visits</h2>
					<router-link :to="{ name: 'Visits' }" class="text-xs font-medium text-saffron">See all</router-link>
				</div>

				<Skeleton v-if="loading" :count="3" />
				<EmptyState
					v-else-if="!recent.length"
					title="No visits yet"
					subtitle="Tap “Start a Visit” to log your first dealer visit."
				/>
				<div v-else class="space-y-2">
					<VisitRow v-for="v in recent" :key="v.name" :visit="v" />
				</div>
			</div>
		</div>

		<BottomNav />
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue"
import { Bell, MapPin, ChevronRight, Route, Target, IndianRupee, CalendarCheck } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import VisitRow from "../components/VisitRow.vue"
import { session } from "../data/session"
import { call } from "../data/api"

const loading = ref(true)
const visits = ref([])
const stats = reactive({ today: 0, week: 0, completed: 0 })

const greeting = computed(() => {
	const h = new Date().getHours()
	if (h < 12) return "Good morning"
	if (h < 17) return "Good afternoon"
	return "Good evening"
})

const inProgress = computed(() => visits.value.find((v) => v.visit_status === "In Progress") || null)
const recent = computed(() => visits.value.slice(0, 6))

onMounted(async () => {
	try {
		const rows = await call("crm_app.field_visit.get_my_visits", { scope: "mine", limit: 100 })
		visits.value = rows || []
		const today = dayjs().format("YYYY-MM-DD")
		const weekStart = dayjs().startOf("week")
		stats.today = visits.value.filter((v) => v.visit_date === today).length
		stats.week = visits.value.filter((v) => dayjs(v.visit_date).isAfter(weekStart)).length
		stats.completed = visits.value.filter((v) => v.visit_status === "Completed").length
	} catch (e) {
		/* surfaced via toast elsewhere */
	} finally {
		loading.value = false
	}
})
</script>
