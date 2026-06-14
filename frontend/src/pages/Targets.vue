<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-5 pt-6 text-white">
			<h1 class="text-xl font-bold">My Targets</h1>
			<p class="text-sm text-navy-200">Target vs achievement</p>
		</header>

		<div class="mx-auto max-w-xl space-y-3 p-4">
			<Skeleton v-if="loading" :count="3" />
			<EmptyState v-else-if="!targets.length" title="No targets set" subtitle="Your manager hasn't assigned targets yet." />
			<div v-for="t in targets" v-else :key="t.name" class="aa-card space-y-3">
				<div class="flex items-center justify-between">
					<p class="font-semibold text-navy-700 dark:text-white">{{ t.period_label }}</p>
					<span class="text-xs text-gray-400">{{ fmtDate(t.from_date) }} – {{ fmtDate(t.to_date) }}</span>
				</div>

				<div>
					<div class="mb-1 flex justify-between text-sm">
						<span class="text-gray-500">Value</span>
						<span class="font-medium text-navy-700 dark:text-white">₹{{ fmt(t.achieved_amount) }} / ₹{{ fmt(t.target_amount) }}</span>
					</div>
					<Bar :pct="t.amount_pct" />
				</div>

				<div>
					<div class="mb-1 flex justify-between text-sm">
						<span class="text-gray-500">Quantity</span>
						<span class="font-medium text-navy-700 dark:text-white">{{ fmt(t.achieved_qty_mt) }} / {{ fmt(t.target_qty_mt) }} MT</span>
					</div>
					<Bar :pct="t.qty_pct" />
				</div>
				<p class="text-xs text-gray-400">{{ t.order_count }} order(s) in this period</p>
			</div>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, onMounted, defineComponent, h } from "vue"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"

const Bar = defineComponent({
	props: { pct: { type: Number, default: 0 } },
	setup(props) {
		return () =>
			h("div", { class: "h-2.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-navy-700" }, [
				h("div", {
					class: "h-full rounded-full " + (props.pct >= 100 ? "bg-green-500" : "bg-saffron"),
					style: { width: Math.min(100, props.pct || 0) + "%" },
				}),
			])
	},
})

const targets = ref([])
const loading = ref(true)

function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }
function fmtDate(d) { return d ? dayjs(d).format("DD MMM") : "" }

onMounted(async () => {
	try {
		targets.value = (await call("crm_app.targets.get_my_targets", { scope: "mine" })) || []
	} finally {
		loading.value = false
	}
})
</script>
