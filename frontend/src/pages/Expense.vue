<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header !pb-5 !pt-5 flex items-center gap-3">
			<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="text-lg font-semibold">{{ $t("Expense Claims") }}</h1>
		</header>

		<div class="mx-auto max-w-xl space-y-3 p-4">
			<div class="aa-card">
				<button v-if="!adding" @click="adding = true" class="flex w-full items-center justify-center gap-2 text-sm font-semibold text-saffron">
					<Plus class="h-4 w-4" /> {{ $t("New claim") }} </button>
				<div v-else class="space-y-2">
					<select v-model="form.expense_type" class="aa-input">
						<option value="">Expense type…</option>
						<option v-for="t in types" :key="t.name">{{ t.name }}</option>
					</select>
					<div class="grid grid-cols-2 gap-2">
						<input v-model.number="form.amount" type="number" class="aa-input" :placeholder='$t("Amount ₹")' />
						<input v-model="form.expense_date" type="date" class="aa-input" />
					</div>
					<input v-model="form.description" class="aa-input" :placeholder='$t("Description (e.g. fuel Kolkata-Durgapur)")' />
					<label class="flex items-center gap-2 text-sm text-gray-500">
						<Camera class="h-5 w-5 text-saffron" />
						<span>{{ receiptName || "Attach receipt photo" }}</span>
						<input type="file" accept="image/*" capture="environment" class="hidden" @change="onReceipt" />
					</label>
					<div class="flex gap-2">
						<button @click="cancel" class="flex-1 rounded-xl bg-gray-200 py-2.5 text-sm text-gray-600">{{ $t("Cancel") }}</button>
						<button @click="submit" :disabled="busy || !form.expense_type || !form.amount" class="aa-btn-primary flex-1 !py-2.5 text-sm">{{ $t("Submit") }}</button>
					</div>
				</div>
			</div>

			<Skeleton v-if="loading" :count="4" />
			<EmptyState v-else-if="!rows.length" :title='$t("No claims yet")' :subtitle='$t("Submit your first expense claim.")' />
			<div v-for="r in rows" v-else :key="r.name" class="aa-card flex items-center justify-between">
				<div>
					<p class="font-semibold text-navy-700 dark:text-white">₹{{ fmt(r.total_claimed_amount || r.grand_total) }}</p>
					<p class="text-xs text-gray-400">{{ fmtDate(r.posting_date) }} · {{ r.name }}</p>
				</div>
				<span class="rounded-full px-2.5 py-1 text-[11px] font-semibold" :class="badge(r.approval_status)">{{ r.approval_status || r.status }}</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue"
import { ChevronLeft, Plus, Camera } from "lucide-vue-next"
import dayjs from "dayjs"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { callOrQueue } from "../data/offline"
import { resizeImageToDataURL } from "../utils/image"
import { toast } from "../utils/toast"

const rows = ref([])
const types = ref([])
const loading = ref(true)
const adding = ref(false)
const busy = ref(false)
const receiptB64 = ref("")
const receiptName = ref("")
const form = reactive({ expense_type: "", amount: null, expense_date: dayjs().format("YYYY-MM-DD"), description: "" })

function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }
function fmtDate(d) { return d ? dayjs(d).format("DD MMM YYYY") : "" }
function badge(s) {
	return { Approved: "bg-green-100 text-green-700", Rejected: "bg-red-100 text-red-600", Draft: "bg-gray-100 text-gray-500" }[s] || "bg-gray-100 text-gray-500"
}

async function onReceipt(e) {
	const file = e.target.files?.[0]
	if (!file) return
	receiptName.value = file.name
	receiptB64.value = await resizeImageToDataURL(file, 1280, 0.8)
}
function cancel() { adding.value = false; receiptB64.value = ""; receiptName.value = "" }

async function load() {
	loading.value = true
	try {
		rows.value = (await call("crm_app.expense.get_my_expenses")) || []
	} finally { loading.value = false }
}
async function submit() {
	busy.value = true
	try {
		const res = await callOrQueue("crm_app.expense.create_expense_claim", {
			items: JSON.stringify([{ expense_type: form.expense_type, amount: Number(form.amount), expense_date: form.expense_date, description: form.description }]),
			receipt_base64: receiptB64.value || undefined,
			receipt_filename: receiptName.value || undefined,
		}, "Expense")
		toast.success(res?.queued ? "Saved offline — will sync" : (res.submitted ? "Claim submitted" : "Saved"))
		cancel(); adding.value = false
		Object.assign(form, { expense_type: "", amount: null, description: "" })
		await load()
	} catch (e) {
		toast.error(e?.messages?.[0] || "Could not submit claim")
	} finally { busy.value = false }
}
onMounted(async () => {
	types.value = (await call("crm_app.expense.get_expense_types")) || []
	await load()
})
</script>
