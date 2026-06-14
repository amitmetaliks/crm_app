<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-4 pb-4 pt-5 text-white">
			<h1 class="text-lg font-semibold">Activity Timeline</h1>
			<div class="mt-3 flex items-center justify-between">
				<button @click="shift(-1)" class="rounded-lg bg-white/10 px-3 py-1"><ChevronLeft class="h-5 w-5" /></button>
				<span class="text-sm font-medium">{{ fmtDay(date) }}</span>
				<button @click="shift(1)" class="rounded-lg bg-white/10 px-3 py-1"><ChevronRight class="h-5 w-5" /></button>
			</div>
		</header>

		<div class="mx-auto max-w-xl p-4">
			<Skeleton v-if="loading" :count="4" />
			<EmptyState v-else-if="!items.length" title="No activity" subtitle="No activity recorded for this date." />
			<div v-else class="space-y-0">
				<div v-for="(it, i) in items" :key="i" class="flex gap-3">
					<div class="flex flex-col items-center">
						<div class="flex h-9 w-9 items-center justify-center rounded-full" :class="it.type === 'attendance' ? 'bg-green-100 text-green-600' : 'bg-saffron/15 text-saffron'">
							<CalendarCheck v-if="it.type === 'attendance'" class="h-4 w-4" /><MapPin v-else class="h-4 w-4" />
						</div>
						<div v-if="i < items.length - 1" class="my-1 w-px flex-1 bg-gray-200 dark:bg-navy-700"></div>
					</div>
					<div class="flex-1 pb-4">
						<div class="aa-card !py-2.5">
							<div class="flex items-center justify-between">
								<p class="truncate text-sm font-semibold text-navy-700 dark:text-white">{{ it.title }}</p>
								<span class="shrink-0 text-xs text-gray-400">{{ fmtTime(it.time) }}</span>
							</div>
							<p v-if="it.subtitle" class="text-xs text-gray-400">{{ it.subtitle }}</p>
						</div>
					</div>
				</div>
			</div>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronLeft, ChevronRight, CalendarCheck, MapPin } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"

const date = ref(dayjs().format("YYYY-MM-DD"))
const items = ref([])
const loading = ref(true)

function fmtDay(d) { return dayjs(d).format("ddd, DD MMM YYYY") }
function fmtTime(t) { return t ? dayjs(t).format("h:mm A") : "" }
function shift(n) { date.value = dayjs(date.value).add(n, "day").format("YYYY-MM-DD"); load() }

async function load() {
	loading.value = true
	try { items.value = (await call("crm_app.sfa.get_activity_timeline", { date: date.value })).items || [] }
	finally { loading.value = false }
}
onMounted(load)
</script>
