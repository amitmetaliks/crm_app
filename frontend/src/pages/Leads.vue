<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<h1 class="text-xl font-bold">{{ $t("Leads & Deals") }}</h1>
			<div class="mt-3 flex gap-2">
				<button @click="tab = 'leads'" class="rounded-full px-4 py-1.5 text-sm font-medium" :class="tab === 'leads' ? 'bg-saffron-600 text-white' : 'bg-white/10 text-navy-100'">{{ $t("Leads") }}</button>
				<button @click="tab = 'deals'" class="rounded-full px-4 py-1.5 text-sm font-medium" :class="tab === 'deals' ? 'bg-saffron-600 text-white' : 'bg-white/10 text-navy-100'">{{ $t("Deals") }}</button>
			</div>
		</header>

		<div class="mx-auto max-w-xl space-y-3 p-4">
			<!-- Create lead -->
			<div v-if="tab === 'leads'" class="aa-card">
				<button v-if="!adding" @click="adding = true" class="flex w-full items-center justify-center gap-2 text-sm font-semibold text-saffron">
					<Plus class="h-4 w-4" /> {{ $t("New lead") }} </button>
				<div v-else class="space-y-2">
					<input v-model="form.lead_name" class="aa-input" :placeholder='$t("Name / Shop / Firm *")' />
					<div class="grid grid-cols-2 gap-2">
						<input v-model="form.mobile_no" class="aa-input" type="tel" :placeholder='$t("Mobile")' />
						<input v-model="form.email" class="aa-input" type="email" :placeholder='$t("Email")' />
					</div>
					<input v-model="form.territory" class="aa-input" :placeholder='$t("Area / Territory")' />
					<div class="flex gap-2">
						<button @click="adding = false" class="flex-1 rounded-xl bg-gray-200 py-2.5 text-sm text-gray-600">{{ $t("Cancel") }}</button>
						<button @click="createLead" :disabled="busy || !form.lead_name" class="aa-btn-primary flex-1 !py-2.5 text-sm">{{ $t("Save") }}</button>
					</div>
				</div>
			</div>

			<input v-model="search" @input="onSearch" class="aa-input" :placeholder="`Search ${tab}…`" />

			<Skeleton v-if="loading" :count="5" />
			<EmptyState v-else-if="!rows.length" :title="`No ${tab} yet`" />
			<template v-else>
				<router-link
					v-for="r in rows"
					:key="r.name"
					:to="{ name: 'NewVisit', query: { ptype: tab === 'leads' ? 'CRM Lead' : 'CRM Deal', id: r.name, label: label(r) } }"
					class="aa-card flex items-center justify-between"
				>
					<div class="min-w-0">
						<p class="truncate font-semibold text-navy-700 dark:text-white">{{ label(r) }}</p>
						<p class="text-xs text-gray-400">{{ r.status || "—" }}<span v-if="r.mobile_no"> · {{ r.mobile_no }}</span></p>
					</div>
					<MapPin class="h-5 w-5 text-saffron" />
				</router-link>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from "vue"
import { Plus, MapPin } from "lucide-vue-next"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { toast } from "../utils/toast"

const tab = ref("leads")
const rows = ref([])
const loading = ref(true)
const search = ref("")
const adding = ref(false)
const busy = ref(false)
const form = reactive({ lead_name: "", mobile_no: "", email: "", territory: "" })
let timer = null

function label(r) {
	return r.organization || r.lead_name || r.name
}

async function load() {
	loading.value = true
	try {
		const method = tab.value === "leads" ? "crm_app.leads.get_leads" : "crm_app.leads.get_deals"
		rows.value = (await call(method, { scope: "mine", search: search.value || undefined })) || []
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
async function createLead() {
	busy.value = true
	try {
		await call("crm_app.leads.create_lead", { ...form })
		toast.success("Lead created")
		adding.value = false
		form.lead_name = form.mobile_no = form.email = form.territory = ""
		await load()
	} catch (e) {
		toast.error(e?.messages?.[0] || "Could not create lead")
	} finally {
		busy.value = false
	}
}
watch(tab, () => { search.value = ""; load() })
onMounted(load)
</script>
