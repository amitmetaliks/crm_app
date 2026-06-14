<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="flex items-center gap-3 bg-navy-700 px-4 py-4 text-white">
			<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="text-lg font-semibold">Salary Slips</h1>
		</header>

		<div class="mx-auto max-w-xl space-y-3 p-4">
			<Skeleton v-if="loading" :count="4" />
			<EmptyState v-else-if="!rows.length" title="No salary slips" subtitle="Your payslips will appear here." />
			<div v-for="r in rows" v-else :key="r.name" class="aa-card">
				<div class="flex items-center justify-between" @click="toggle(r.name)">
					<div>
						<p class="font-semibold text-navy-700 dark:text-white">{{ fmtDate(r.start_date) }} – {{ fmtDate(r.end_date) }}</p>
						<p class="text-xs text-gray-400">Net ₹{{ fmt(r.net_pay) }}</p>
					</div>
					<ChevronDown class="h-5 w-5 text-gray-300 transition" :class="open === r.name ? 'rotate-180' : ''" />
				</div>
				<div v-if="open === r.name && detail" class="mt-3 border-t border-gray-100 pt-3 text-sm">
					<div class="space-y-1">
						<div v-for="(e, i) in detail.earnings" :key="'e'+i" class="flex justify-between"><span class="text-gray-500">{{ e.component }}</span><span class="text-green-700">+₹{{ fmt(e.amount) }}</span></div>
						<div v-for="(d, i) in detail.deductions" :key="'d'+i" class="flex justify-between"><span class="text-gray-500">{{ d.component }}</span><span class="text-red-600">−₹{{ fmt(d.amount) }}</span></div>
					</div>
					<div class="mt-2 flex justify-between border-t border-gray-100 pt-2 font-semibold text-navy-700 dark:text-white"><span>Net Pay</span><span>₹{{ fmt(detail.net_pay) }}</span></div>
					<button @click="downloadPdf(r.name)" :disabled="dl" class="mt-3 w-full rounded-xl bg-navy-700 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{{ dl ? "Preparing…" : "Download PDF" }}</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronLeft, ChevronDown } from "lucide-vue-next"
import dayjs from "dayjs"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { toast } from "../utils/toast"

const rows = ref([])
const loading = ref(true)
const open = ref(null)
const detail = ref(null)
const dl = ref(false)

function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }
function fmtDate(d) { return d ? dayjs(d).format("DD MMM YYYY") : "" }

async function toggle(name) {
	if (open.value === name) { open.value = null; return }
	open.value = name; detail.value = null
	try { detail.value = await call("crm_app.salary.get_salary_slip", { name }) } catch (e) { toast.error("Could not load slip") }
}
async function downloadPdf(name) {
	dl.value = true
	try {
		const res = await call("crm_app.salary.download_salary_slip_pdf", { name })
		const bin = atob(res.content_base64)
		const arr = Uint8Array.from([...bin].map((c) => c.charCodeAt(0)))
		const url = URL.createObjectURL(new Blob([arr], { type: "application/pdf" }))
		const a = document.createElement("a"); a.href = url; a.download = res.filename; a.click()
		URL.revokeObjectURL(url)
	} catch (e) { toast.error("Could not download") } finally { dl.value = false }
}
onMounted(async () => {
	try { rows.value = (await call("crm_app.salary.get_my_salary_slips")) || [] } finally { loading.value = false }
})
</script>
