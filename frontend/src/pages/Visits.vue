<template>
	<div class="aa-workspace">
		<header class="aa-topbar !items-end">
			<div><p class="aa-kicker">Activity</p><h1 class="aa-display mt-1">Visits</h1><p class="aa-subtitle">Your field conversations and outcomes.</p></div>
			<router-link :to="{ name: 'NewVisit' }" class="aa-hero-action !min-h-11 !px-3"><Plus class="h-4 w-4" /> New</router-link>
		</header>

		<main class="aa-content pt-3">
			<div class="flex gap-2 overflow-x-auto pb-2">
				<button
					v-for="f in filters"
					:key="f.value"
					@click="setStatus(f.value)"
					class="min-h-10 shrink-0 rounded-full border px-4 text-xs font-semibold transition"
					:class="status === f.value ? 'border-navy-700 bg-navy-700 text-white' : 'border-[#e7e5df] bg-white text-gray-500 dark:border-navy-700 dark:bg-navy-800'"
				>{{ f.label }}</button>
			</div>
			<label v-if="session.isSalesManager" class="mt-2 flex items-center gap-2 text-xs text-gray-500"><input type="checkbox" v-model="teamScope" @change="load" /> Show whole team</label>

			<div class="mb-3 mt-6 flex items-center justify-between"><h2 class="aa-section-heading">{{ status || "All visits" }}</h2><span class="text-xs font-medium text-gray-400">{{ visits.length }} records</span></div>
			<div class="space-y-2">
				<Skeleton v-if="loading" :count="5" />
				<EmptyState v-else-if="!visits.length" class="aa-panel p-6" :title='$t("No visits found")' :subtitle="emptyMsg" />
				<VisitRow v-for="v in visits" v-else :key="v.name" :visit="v" />
			</div>
		</main>

		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { Plus } from "lucide-vue-next"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import VisitRow from "../components/VisitRow.vue"
import { callCached } from "../data/cache"
import { session } from "../data/session"

const filters = [
	{ label: "All", value: "" },
	{ label: "In progress", value: "In Progress" },
	{ label: "Completed", value: "Completed" },
	{ label: "Planned", value: "Planned" },
]
const status = ref("")
const teamScope = ref(false)
const visits = ref([])
const loading = ref(true)
const emptyMsg = computed(() => status.value ? `No ${status.value.toLowerCase()} visits.` : "Start logging dealer visits.")

async function load() {
	loading.value = true
	try {
		visits.value = (await callCached("crm_app.field_visit.get_my_visits", {
			scope: teamScope.value ? "team" : "mine",
			status: status.value || undefined,
			limit: 200,
		})) || []
	} catch (e) { visits.value = [] }
	finally { loading.value = false }
}
function setStatus(value) { status.value = value; load() }
onMounted(load)
</script>
