<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<div class="flex items-center gap-3">
				<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
				<h1 class="text-xl font-bold">{{ $t("Journey plan") }}</h1>
			</div>
			<p v-if="pjp.exists" class="mt-1 text-sm text-navy-200">
				{{ pjp.title }} · {{ cycleLabel }} · {{ pjp.total_stops }} {{ $t("stops") }}
			</p>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<Skeleton v-if="loading" :count="3" />

			<EmptyState
				v-else-if="!pjp.exists"
				:title='$t("No journey plan yet")'
				:subtitle='$t("Your manager sets which dealers you cover, and how often.")'
			/>

			<template v-else>
				<!-- Coverage: the whole point of a PJP -->
				<div class="aa-card">
					<div class="flex items-end justify-between">
						<div>
							<p class="text-xs text-gray-400">{{ $t("Coverage (last 4 weeks)") }}</p>
							<p class="text-3xl font-bold" :class="cov.pct >= 80 ? 'text-green-600' : cov.pct >= 60 ? 'text-amber-500' : 'text-red-600'">
								{{ cov.pct }}%
							</p>
						</div>
						<p class="text-sm text-gray-500">{{ cov.covered }} / {{ cov.planned }} {{ $t("stops visited") }}</p>
					</div>
					<div class="mt-2 h-2 overflow-hidden rounded-full bg-gray-100 dark:bg-navy-700">
						<div class="h-full rounded-full" :class="cov.pct >= 80 ? 'bg-green-500' : cov.pct >= 60 ? 'bg-amber-400' : 'bg-red-500'" :style="{ width: Math.min(cov.pct, 100) + '%' }" />
					</div>
				</div>

				<!-- Today -->
				<div>
					<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">
						{{ $t("Due today") }} ({{ pjp.today.length }})
					</h2>
					<EmptyState v-if="!pjp.today.length" :title='$t("Nothing due today")' />
					<div v-else class="space-y-2">
						<router-link
							v-for="s in pjp.today"
							:key="s.customer"
							:to="{ name: 'CustomerDetail', params: { name: s.customer } }"
							class="aa-card flex items-center justify-between"
						>
							<span class="min-w-0 truncate text-sm font-medium text-navy-700 dark:text-white">{{ s.customer_name }}</span>
							<span class="shrink-0 text-xs text-gray-400">{{ $t(s.beat_type) }}</span>
						</router-link>
					</div>
					<button v-if="pjp.today.length" class="aa-btn-primary mt-2 w-full" :disabled="busy" @click="genBeat">
						{{ busy ? $t("Adding…") : $t("Add today's stops to my beat") }}
					</button>
				</div>

				<!-- Missed stops — the part a rep needs to see, not hide -->
				<div v-if="cov.missed?.length">
					<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">
						{{ $t("Missed stops") }} ({{ cov.missed_count }})
					</h2>
					<div class="aa-card space-y-2">
						<router-link
							v-for="(m, i) in cov.missed.slice(0, 10)"
							:key="i"
							:to="{ name: 'CustomerDetail', params: { name: m.customer } }"
							class="flex items-center justify-between text-sm"
						>
							<span class="min-w-0 truncate text-navy-700 dark:text-white">{{ m.customer_name }}</span>
							<span class="shrink-0 text-xs text-red-500">{{ fmtDate(m.date) }}</span>
						</router-link>
					</div>
				</div>

				<!-- Skipped WITH a reason: uncovered, but explained. Kept separate from
				     'missed' so coverage can never be dressed up by skipping. -->
				<div v-if="cov.excused?.length">
					<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">
						{{ $t("Skipped with reason") }} ({{ cov.excused_count }})
					</h2>
					<div class="aa-card space-y-2">
						<router-link
							v-for="(m, i) in cov.excused.slice(0, 10)"
							:key="i"
							:to="{ name: 'CustomerDetail', params: { name: m.customer } }"
							class="flex items-center justify-between text-sm"
						>
							<span class="min-w-0 truncate text-navy-700 dark:text-white">{{ m.customer_name }}</span>
							<span class="shrink-0 text-xs text-amber-600">{{ $t(m.skip_reason) }} · {{ fmtDate(m.date) }}</span>
						</router-link>
					</div>
				</div>

				<!-- The plan itself -->
				<div>
					<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Full plan") }}</h2>
					<div v-for="d in days" :key="d" class="mb-2">
						<div v-if="byDay[d]?.length" class="aa-card">
							<p class="mb-1 text-xs font-semibold uppercase tracking-wide text-saffron">{{ $t(d) }}</p>
							<div v-for="(e, i) in byDay[d]" :key="i" class="flex items-center justify-between py-0.5 text-sm">
								<span class="min-w-0 truncate text-navy-700 dark:text-white">{{ e.customer_name }}</span>
								<span class="shrink-0 text-xs text-gray-400">
									<template v-if="pjp.cycle_weeks > 1">{{ $t("Week") }} {{ e.week_no }} · </template>{{ $t(e.beat_type) }}
								</span>
							</div>
						</div>
					</div>
				</div>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { ChevronLeft } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { toast } from "../utils/toast"
import { t } from "../data/i18n"

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
const pjp = ref({ exists: false, entries: [], today: [] })
const cov = ref({ pct: 0, covered: 0, planned: 0, missed: [] })
const loading = ref(true)
const busy = ref(false)

const cycleLabel = computed(() => {
	const w = pjp.value.cycle_weeks
	if (w === 1) return t("Weekly")
	if (w === 2) return t("Fortnightly")
	return t("Monthly")
})
const byDay = computed(() => {
	const g = {}
	for (const e of pjp.value.entries || []) (g[e.weekday] = g[e.weekday] || []).push(e)
	for (const d in g) g[d].sort((a, b) => (a.week_no || 1) - (b.week_no || 1))
	return g
})

function fmtDate(d) { return d ? dayjs(d).format("DD MMM") : "" }

async function genBeat() {
	busy.value = true
	try {
		const res = await call("crm_app.pjp.generate_beat")
		toast.success(res.created ? `${res.created} stop(s) added to today's beat` : "Beat already has today's stops")
	} catch (e) {
		toast.error(e?.messages?.[0] || "Could not build the beat")
	} finally {
		busy.value = false
	}
}

onMounted(async () => {
	try {
		pjp.value = await call("crm_app.pjp.get_my_pjp")
		if (pjp.value.exists) cov.value = await call("crm_app.pjp.get_coverage")
	} catch (e) {
		/* leave the empty state */
	} finally {
		loading.value = false
	}
})
</script>
