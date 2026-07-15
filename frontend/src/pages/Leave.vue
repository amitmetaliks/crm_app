<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="flex items-center gap-3 bg-navy-700 px-4 py-4 text-white">
			<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="text-lg font-semibold">{{ $t("Leave") }}</h1>
		</header>

		<div class="mx-auto max-w-xl space-y-3 p-4">
			<div v-if="balanceRows.length" class="aa-card">
				<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Balance") }}</p>
				<div class="grid grid-cols-2 gap-2">
					<div v-for="b in balanceRows" :key="b.type" class="rounded-xl bg-gray-50 p-2.5 text-center dark:bg-navy-800">
						<p class="text-lg font-bold text-navy-700 dark:text-white">{{ b.value }}</p>
						<p class="text-[11px] text-gray-400">{{ b.type }}</p>
					</div>
				</div>
			</div>

			<div class="aa-card">
				<button v-if="!adding" @click="adding = true" class="flex w-full items-center justify-center gap-2 text-sm font-semibold text-saffron">
					<Plus class="h-4 w-4" /> {{ $t("Apply for leave") }} </button>
				<div v-else class="space-y-2">
					<select v-model="form.leave_type" class="aa-input">
						<option value="">Leave type…</option>
						<option v-for="t in types" :key="t.name">{{ t.name }}</option>
					</select>
					<div class="grid grid-cols-2 gap-2">
						<input v-model="form.from_date" type="date" class="aa-input" />
						<input v-model="form.to_date" type="date" class="aa-input" />
					</div>
					<input v-model="form.description" class="aa-input" :placeholder='$t("Reason")' />
					<div class="flex gap-2">
						<button @click="adding = false" class="flex-1 rounded-xl bg-gray-200 py-2.5 text-sm text-gray-600">{{ $t("Cancel") }}</button>
						<button @click="apply" :disabled="busy || !form.leave_type || !form.from_date || !form.to_date" class="flex-1 rounded-xl bg-saffron py-2.5 text-sm font-semibold text-white disabled:opacity-50">{{ $t("Apply") }}</button>
					</div>
				</div>
			</div>

			<Skeleton v-if="loading" :count="3" />
			<div v-for="r in rows" v-else :key="r.name" class="aa-card flex items-center justify-between">
				<div>
					<p class="font-semibold text-navy-700 dark:text-white">{{ r.leave_type }}</p>
					<p class="text-xs text-gray-400">{{ fmtDate(r.from_date) }} – {{ fmtDate(r.to_date) }} · {{ r.total_leave_days }}d</p>
				</div>
				<span class="rounded-full px-2.5 py-1 text-[11px] font-semibold" :class="badge(r.status)">{{ r.status }}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue"
import { ChevronLeft, Plus } from "lucide-vue-next"
import dayjs from "dayjs"
import Skeleton from "../components/Skeleton.vue"
import { call } from "../data/api"
import { toast } from "../utils/toast"

const rows = ref([])
const types = ref([])
const balance = ref({})
const loading = ref(true)
const adding = ref(false)
const busy = ref(false)
const form = reactive({ leave_type: "", from_date: "", to_date: "", description: "" })

const balanceRows = computed(() => Object.entries(balance.value || {}).map(([type, value]) => ({ type, value })))

function fmtDate(d) { return d ? dayjs(d).format("DD MMM") : "" }
function badge(s) {
	return { Approved: "bg-green-100 text-green-700", Rejected: "bg-red-100 text-red-600", Open: "bg-amber-100 text-amber-700" }[s] || "bg-gray-100 text-gray-500"
}

async function load() {
	loading.value = true
	try { rows.value = (await call("crm_app.leave.get_my_leaves")) || [] } finally { loading.value = false }
}
async function apply() {
	busy.value = true
	try {
		const res = await call("crm_app.leave.apply_leave", { ...form })
		toast.success(res.submitted ? "Leave applied" : (res.message || "Saved"))
		adding.value = false
		Object.assign(form, { leave_type: "", from_date: "", to_date: "", description: "" })
		await load()
	} catch (e) {
		toast.error(e?.messages?.[0] || "Could not apply")
	} finally { busy.value = false }
}
onMounted(async () => {
	types.value = (await call("crm_app.leave.get_leave_types")) || []
	try { balance.value = (await call("crm_app.leave.get_leave_summary")).balance || {} } catch (e) { /* */ }
	await load()
})
</script>
