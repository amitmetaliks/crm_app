<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-4 pt-6 text-white">
			<h1 class="text-xl font-bold">Dealers & Customers</h1>
			<input
				v-model="query"
				@input="onSearch"
				class="mt-3 w-full rounded-xl border-0 px-4 py-2.5 text-sm text-navy-700"
				placeholder="Search dealers, leads…"
			/>
		</header>

		<div class="mx-auto max-w-xl space-y-2 p-4">
			<Skeleton v-if="loading" :count="6" />
			<EmptyState v-else-if="!rows.length" title="No matches" subtitle="Try another name." />
			<router-link
				v-for="r in rows"
				v-else
				:key="r.party_type + r.id"
				:to="r.party_type === 'Customer' ? { name: 'CustomerDetail', params: { name: r.id } } : { name: 'NewVisit', query: { ptype: r.party_type, id: r.id, label: r.label } }"
				class="aa-card flex items-center justify-between"
			>
				<div class="min-w-0">
					<p class="truncate font-semibold text-navy-700 dark:text-white">{{ r.label }}</p>
					<p class="text-xs text-gray-400">{{ r.party_type }}{{ r.sub ? " · " + r.sub : "" }}</p>
				</div>
				<ChevronRight class="h-5 w-5 text-gray-300" />
			</router-link>
		</div>

		<BottomNav />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronRight } from "lucide-vue-next"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"

const query = ref("")
const rows = ref([])
const loading = ref(true)
let timer = null

async function load() {
	loading.value = true
	try {
		rows.value = (await call("crm_app.customers.search_parties", { query: query.value, limit: 25 })) || []
	} catch (e) {
		rows.value = []
	} finally {
		loading.value = false
	}
}
function onSearch() {
	clearTimeout(timer)
	timer = setTimeout(load, 300)
}
onMounted(load)
</script>
