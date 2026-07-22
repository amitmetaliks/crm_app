<template>
	<div class="aa-workspace">
		<header class="aa-topbar !items-end">
			<div><p class="aa-kicker">Your territory</p><h1 class="aa-display mt-1">Dealers</h1><p class="aa-subtitle">Find the account before you arrive.</p></div>
			<router-link :to="{ name: 'NewVisit' }" class="aa-back" aria-label="New prospect"><UserRoundPlus class="h-5 w-5" /></router-link>
		</header>

		<main class="aa-content pt-3">
			<div class="relative">
				<Search class="pointer-events-none absolute left-4 top-3.5 h-5 w-5 text-gray-400" />
				<input v-model="query" @input="onSearch" class="aa-search" :placeholder='$t("Search name, area or account")' />
			</div>

			<div class="mb-3 mt-6 flex items-center justify-between">
				<h2 class="aa-section-heading">{{ query ? "Search results" : "My accounts" }}</h2>
				<span class="text-xs font-medium text-gray-400">{{ rows.length }} shown</span>
			</div>

			<div class="aa-panel overflow-hidden">
				<Skeleton v-if="loading" class="p-4" :count="6" />
				<EmptyState v-else-if="!rows.length" class="p-6" :title='$t("No matches")' :subtitle='$t("Try a dealer name, area or account code.")' />
				<router-link
					v-for="r in rows"
					v-else
					:key="r.party_type + r.id"
					:to="r.party_type === 'Customer' ? { name: 'CustomerDetail', params: { name: r.id } } : { name: 'NewVisit', query: { ptype: r.party_type, id: r.id, label: r.label } }"
					class="aa-data-row group"
				>
					<span class="aa-avatar-mark">{{ initials(r.label) }}</span>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-sm font-semibold text-navy-800 group-active:text-saffron dark:text-white">{{ r.label }}</span>
						<span class="mt-0.5 flex items-center gap-1.5 text-xs text-gray-400">
							<MapPin v-if="r.sub" class="h-3 w-3" /> {{ r.sub || r.party_type }}
						</span>
					</span>
					<span class="aa-pill aa-pill-gray">{{ r.party_type === "Customer" ? "Dealer" : r.party_type }}</span>
					<ChevronRight class="h-4 w-4 text-gray-300" />
				</router-link>
			</div>
		</main>

		<BottomNav />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronRight, Search, UserRoundPlus, MapPin } from "lucide-vue-next"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { searchDealers } from "../data/cache"

const query = ref("")
const rows = ref([])
const loading = ref(true)
let timer = null

function initials(label) {
	return (label || "?").split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase()
}
async function load() {
	loading.value = true
	try { rows.value = (await searchDealers(query.value, "", 25)) || [] }
	catch (e) { rows.value = [] }
	finally { loading.value = false }
}
function onSearch() {
	clearTimeout(timer)
	timer = setTimeout(load, 300)
}
onMounted(load)
</script>
