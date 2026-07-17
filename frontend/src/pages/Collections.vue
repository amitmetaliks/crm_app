<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<h1 class="text-xl font-bold">{{ $t("Collections") }}</h1>
			<div v-if="!loading" class="mt-3 grid grid-cols-2 gap-3">
				<div class="rounded-xl bg-white/10 p-3">
					<p class="text-xs text-navy-200">{{ $t("Outstanding") }}</p>
					<p class="text-lg font-bold">{{ inrShort(data.total) }}</p>
				</div>
				<div class="rounded-xl bg-white/10 p-3">
					<p class="text-xs text-navy-200">{{ $t("Overdue") }}</p>
					<p class="text-lg font-bold text-amber-300">{{ inrShort(data.overdue) }}</p>
				</div>
			</div>
		</header>

		<div class="mx-auto max-w-xl space-y-2 p-4">
			<Skeleton v-if="loading" :count="5" />
			<EmptyState
				v-else-if="!data.customers.length"
				:title='$t("Nothing outstanding")'
				:subtitle='$t("No unpaid invoices found for your dealers. To collect money anyway, open the dealer and tap Collect.")'
			/>
			<div v-for="c in data.customers" v-else :key="c.customer" class="aa-card flex items-center justify-between">
				<div class="min-w-0">
					<p class="truncate font-semibold text-navy-700 dark:text-white">{{ c.customer_name }}</p>
					<p class="text-xs" :class="c.overdue > 0 ? 'text-red-500' : 'text-gray-400'">
						₹{{ fmt(c.outstanding) }} · {{ c.invoices }} invoice(s)<span v-if="c.overdue > 0"> · ₹{{ fmt(c.overdue) }} overdue</span>
					</p>
				</div>
				<div class="flex shrink-0 gap-2">
					<button @click="remind(c)" class="rounded-lg bg-green-50 px-3 py-1.5 text-xs font-semibold text-green-600">{{ $t("Remind") }}</button>
					<router-link
						:to="{ name: 'Collect', query: { customer: c.customer, label: c.customer_name } }"
						class="aa-pill-btn !rounded-lg !px-3 !py-1.5 !text-xs"
					>{{ $t("Collect") }}</router-link>
				</div>
			</div>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { openWhatsApp } from "../utils/wa"
import { toast } from "../utils/toast"
import { inrShort } from "../utils/money"

const data = ref({ total: 0, overdue: 0, customers: [] })
const loading = ref(true)

function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }
async function remind(c) {
	// Hands-free send via Meta Cloud API when configured; otherwise free deep-link.
	try {
		await call("crm_app.whatsapp.send_payment_reminder", { customer: c.customer })
		toast.success("Reminder sent on WhatsApp")
		return
	} catch (e) {
		/* not configured / blocked — fall back to deep link */
	}
	const msg = `Dear ${c.customer_name},\nA gentle reminder from *TRIAM A+*: ₹${fmt(c.outstanding)} is outstanding on your account${c.overdue > 0 ? ` (₹${fmt(c.overdue)} overdue)` : ""}. Kindly arrange payment. Thank you.`
	openWhatsApp("", msg)
}

onMounted(async () => {
	try {
		data.value = await call("crm_app.collections.get_my_collections", { scope: "mine" })
	} finally {
		loading.value = false
	}
})
</script>
