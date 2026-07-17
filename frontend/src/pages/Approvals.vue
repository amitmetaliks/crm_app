<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<h1 class="text-xl font-bold">{{ $t("Approvals") }}</h1>
			<p class="text-sm text-navy-200">{{ (data.leaves.length + data.expenses.length) }} pending · {{ data.visits.length }} visits to verify</p>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<Skeleton v-if="loading" :count="3" />
			<template v-else>
				<EmptyState v-if="empty" :title='$t("All clear")' :subtitle='$t("Nothing waiting for your approval.")' />

				<div v-if="data.expenses.length">
					<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Expense claims") }}</h2>
					<div v-for="e in data.expenses" :key="e.name" class="aa-card">
						<p class="font-semibold text-navy-700 dark:text-white">{{ e.employee_name }} · ₹{{ fmt(e.total_claimed_amount || e.grand_total) }}</p>
						<p class="text-xs text-gray-400">{{ fmtDate(e.posting_date) }} · {{ e.name }}</p>

						<!-- Auto-conveyance: show what GPS measured vs what the rep claimed. -->
						<div
							v-if="e.conveyance"
							class="mt-2 rounded-lg p-2 text-xs"
							:class="e.conveyance.corrected ? 'bg-amber-50 text-amber-900' : 'bg-gray-50 text-gray-600 dark:bg-navy-800 dark:text-gray-300'"
						>
							<div class="flex items-center justify-between font-medium">
								<span>{{ $t("GPS recorded") }} <strong>{{ e.conveyance.gps_km }} km</strong></span>
								<span v-if="e.conveyance.corrected" class="flex items-center gap-1">
									<AlertTriangle class="h-3.5 w-3.5" /> {{ $t("Rep claims") }} <strong>{{ e.conveyance.claimed_km }} km</strong>
								</span>
								<span v-else class="text-green-600">✓ matches GPS</span>
							</div>
							<p v-if="e.conveyance.corrected" class="mt-1">
								<strong>+{{ e.conveyance.extra_km }} km</strong> above GPS. {{ e.conveyance.description }}
							</p>
						</div>

						<div class="mt-2 flex gap-2">
							<button @click="act('Expense Claim', e.name, 'reject')" class="flex-1 rounded-lg bg-red-50 py-2 text-sm font-medium text-red-600">{{ $t("Reject") }}</button>
							<button @click="act('Expense Claim', e.name, 'approve')" class="flex-1 rounded-lg bg-green-600 py-2 text-sm font-semibold text-white">{{ $t("Approve") }}</button>
						</div>
					</div>
				</div>

				<div v-if="data.leaves.length">
					<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Leave requests") }}</h2>
					<div v-for="l in data.leaves" :key="l.name" class="aa-card">
						<p class="font-semibold text-navy-700 dark:text-white">{{ l.employee_name }} · {{ l.leave_type }}</p>
						<p class="text-xs text-gray-400">{{ fmtDate(l.from_date) }} – {{ fmtDate(l.to_date) }} · {{ l.total_leave_days }}d</p>
						<div class="mt-2 flex gap-2">
							<button @click="act('Leave Application', l.name, 'reject')" class="flex-1 rounded-lg bg-red-50 py-2 text-sm font-medium text-red-600">{{ $t("Reject") }}</button>
							<button @click="act('Leave Application', l.name, 'approve')" class="flex-1 rounded-lg bg-green-600 py-2 text-sm font-semibold text-white">{{ $t("Approve") }}</button>
						</div>
					</div>
				</div>

				<div v-if="data.visits.length">
					<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Visits to verify") }}</h2>
					<div v-for="v in data.visits" :key="v.name" class="aa-card flex items-center justify-between">
						<div class="min-w-0">
							<p class="truncate font-semibold text-navy-700 dark:text-white">{{ v.party_display }}</p>
							<p class="text-xs text-gray-400">{{ v.sales_person_name }} · {{ fmtDate(v.visit_date) }}</p>
						</div>
						<button @click="verify(v.name)" class="shrink-0 rounded-lg bg-saffron-600 px-3 py-1.5 text-xs font-semibold text-white">{{ $t("Verify") }}</button>
					</div>
				</div>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { AlertTriangle } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { toast } from "../utils/toast"

const data = ref({ leaves: [], expenses: [], visits: [] })
const loading = ref(true)
const empty = computed(() => !data.value.leaves.length && !data.value.expenses.length && !data.value.visits.length)

function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }
function fmtDate(d) { return d ? dayjs(d).format("DD MMM") : "" }

async function load() {
	loading.value = true
	try { data.value = await call("crm_app.approvals.get_pending_approvals") } finally { loading.value = false }
}
async function act(doctype, name, action) {
	try { await call("crm_app.approvals.act_on_approval", { doctype, name, action }); toast.success(action === "approve" ? "Approved" : "Rejected"); await load() }
	catch (e) { toast.error(e?.messages?.[0] || "Action failed") }
}
async function verify(name) {
	try { await call("crm_app.approvals.verify_visit", { name }); toast.success("Visit verified"); await load() }
	catch (e) { toast.error(e?.messages?.[0] || "Could not verify") }
}
onMounted(load)
</script>
