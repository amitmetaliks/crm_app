<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="flex items-center gap-3 bg-navy-700 px-4 py-4 text-white">
			<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="text-lg font-semibold">Active Schemes</h1>
		</header>

		<div class="mx-auto max-w-xl space-y-2 p-4">
			<Skeleton v-if="loading" :count="5" />
			<EmptyState v-else-if="!rows.length" title="No active schemes" subtitle="No current offers/discounts are running." />
			<div v-for="s in rows" v-else :key="s.name" class="aa-card">
				<div class="flex items-center justify-between">
					<p class="font-semibold text-navy-700 dark:text-white">{{ s.title }}</p>
					<span class="shrink-0 rounded-full bg-saffron/15 px-2.5 py-1 text-xs font-semibold text-saffron">{{ s.offer }}</span>
				</div>
				<p class="text-xs text-gray-400">{{ s.apply_on }}<span v-if="s.valid_upto"> · till {{ fmtDate(s.valid_upto) }}</span></p>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronLeft } from "lucide-vue-next"
import dayjs from "dayjs"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"

const rows = ref([])
const loading = ref(true)
function fmtDate(d) { return d ? dayjs(d).format("DD MMM") : "" }
onMounted(async () => {
	try { rows.value = (await call("crm_app.pricing.get_schemes")) || [] } finally { loading.value = false }
})
</script>
