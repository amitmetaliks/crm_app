<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<h1 class="text-xl font-bold">{{ $t("Visits") }}</h1>
			<div class="mt-3 flex gap-2 overflow-x-auto pb-1">
				<button
					v-for="f in filters"
					:key="f.value"
					@click="setStatus(f.value)"
					class="shrink-0 rounded-full px-3 py-1.5 text-xs font-medium"
					:class="status === f.value ? 'bg-saffron text-navy-700' : 'bg-white/10 text-navy-100'"
				>
					{{ f.label }}
				</button>
			</div>
			<label v-if="session.isSalesManager" class="mt-2 flex items-center gap-2 text-xs text-navy-100">
				<input type="checkbox" v-model="teamScope" @change="load" /> {{ $t("Show whole team") }} </label>
		</header>

		<div class="mx-auto max-w-xl space-y-2 p-4">
			<Skeleton v-if="loading" :count="5" />
			<EmptyState v-else-if="!visits.length" :title='$t("No visits found")' :subtitle="emptyMsg" />
			<VisitRow v-for="v in visits" v-else :key="v.name" :visit="v" />
		</div>

		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import VisitRow from "../components/VisitRow.vue"
import { callCached } from "../data/cache"
import { session } from "../data/session"

const filters = [
	{ label: "All", value: "" },
	{ label: "In Progress", value: "In Progress" },
	{ label: "Completed", value: "Completed" },
	{ label: "Planned", value: "Planned" },
]
const status = ref("")
const teamScope = ref(false)
const visits = ref([])
const loading = ref(true)

const emptyMsg = computed(() =>
	status.value ? `No ${status.value.toLowerCase()} visits.` : "Start logging dealer visits."
)

async function load() {
	loading.value = true
	try {
		visits.value =
			(await callCached("crm_app.field_visit.get_my_visits", {
				scope: teamScope.value ? "team" : "mine",
				status: status.value || undefined,
				limit: 200,
			})) || []
	} catch (e) {
		visits.value = []
	} finally {
		loading.value = false
	}
}
function setStatus(v) {
	status.value = v
	load()
}
onMounted(load)
</script>
