<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="flex items-center gap-3 bg-navy-700 px-4 py-4 text-white">
			<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="text-lg font-semibold">KRA — This Month</h1>
		</header>

		<div class="mx-auto max-w-xl space-y-3 p-4">
			<Skeleton v-if="loading" :count="5" />
			<div v-for="(k, i) in rows" v-else :key="i" class="aa-card">
				<div class="mb-1 flex items-center justify-between">
					<span class="text-sm font-semibold text-navy-700 dark:text-white">{{ k.label }}</span>
					<span class="text-sm text-gray-500">
						{{ k.unit === '₹' ? '₹' : '' }}{{ fmt(k.achieved) }}{{ k.unit === '%' ? '%' : '' }}
						<span v-if="k.has_target" class="text-gray-400"> / {{ k.unit === '₹' ? '₹' : '' }}{{ fmt(k.target) }}{{ k.unit === '%' ? '%' : '' }}</span>
						<span v-else class="text-xs text-gray-300"> (no target)</span>
					</span>
				</div>
				<div class="h-2.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-navy-700">
					<div class="h-full rounded-full" :class="k.pct >= 100 ? 'bg-green-500' : 'bg-saffron'" :style="{ width: Math.min(100, k.pct) + '%' }"></div>
				</div>
				<p class="mt-1 text-right text-xs font-medium" :class="k.pct >= 100 ? 'text-green-600' : 'text-gray-400'">{{ k.pct }}%</p>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronLeft } from "lucide-vue-next"
import Skeleton from "../components/Skeleton.vue"
import { call } from "../data/api"

const rows = ref([])
const loading = ref(true)
function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }
onMounted(async () => {
	try { rows.value = (await call("crm_app.sfa.get_kra")) || [] } finally { loading.value = false }
})
</script>
