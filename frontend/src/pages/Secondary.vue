<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<div class="flex items-center gap-3">
				<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
				<h1 class="text-xl font-bold">{{ $t("Secondary sales") }}</h1>
			</div>
			<div v-if="!loading && d.checks" class="mt-3 grid grid-cols-3 gap-3">
				<div class="rounded-xl bg-white/10 p-2">
					<p class="text-xs text-navy-200">{{ $t("Dealer reported") }}</p>
					<p class="text-lg font-bold">{{ num(d.reported_mt) }} MT</p>
				</div>
				<div class="rounded-xl bg-white/10 p-2">
					<p class="text-xs text-navy-200">{{ $t("Stock implies") }}</p>
					<p class="text-lg font-bold">{{ num(d.implied_mt) }} MT</p>
				</div>
				<div class="rounded-xl bg-white/10 p-2">
					<p class="text-xs text-navy-200">{{ $t("Our shelf share") }}</p>
					<p class="text-lg font-bold text-amber-300">{{ d.our_share_pct }}%</p>
				</div>
			</div>
		</header>

		<div class="mx-auto max-w-xl space-y-3 p-4">
			<Skeleton v-if="loading" :count="4" />
			<EmptyState
				v-else-if="!d.checks"
				:title='$t("No stock checks yet")'
				:subtitle='$t("Record a dealer stock check during a visit and it will show here.")'
			/>

			<template v-else>
				<p class="px-1 text-xs leading-relaxed text-gray-500">
					{{ $t("Dealer reported is what dealers told you. Stock implies is what their own stock movement says. Gaps are worth asking about.") }}
				</p>

				<div v-for="row in d.dealers" :key="row.customer" class="aa-card">
					<div class="flex items-start justify-between gap-2">
						<router-link :to="{ name: 'CustomerDetail', params: { name: row.customer } }" class="min-w-0">
							<p class="truncate font-semibold text-navy-700 dark:text-white">{{ row.customer_name }}</p>
							<p class="text-xs text-gray-400">
								{{ row.checks }} {{ $t("checks") }} · {{ $t("last") }} {{ fmtDate(row.last_check) }} · {{ row.our_share_pct }}% {{ $t("ours") }}
							</p>
						</router-link>
						<router-link
							:to="{ name: 'StockCheck', query: { customer: row.customer, label: row.customer_name } }"
							class="aa-pill-btn shrink-0 !rounded-lg !px-3 !py-1.5 !text-xs"
						>{{ $t("Check") }}</router-link>
					</div>
					<div class="mt-2 flex items-center justify-between border-t border-gray-100 pt-2 text-sm dark:border-navy-700">
						<span class="text-gray-500">{{ num(row.reported_mt) }} MT {{ $t("reported") }}</span>
						<span :class="Math.abs(row.gap_mt) > 0.5 ? 'font-semibold text-amber-600' : 'text-gray-400'">
							{{ num(row.implied_mt) }} MT {{ $t("implied") }}
							<template v-if="Math.abs(row.gap_mt) > 0.5"> ({{ row.gap_mt > 0 ? "+" : "" }}{{ num(row.gap_mt) }})</template>
						</span>
					</div>
				</div>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronLeft } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { num } from "../utils/money"

const d = ref({ dealers: [], checks: 0 })
const loading = ref(true)

function fmtDate(x) { return x ? dayjs(x).format("DD MMM") : "" }

onMounted(async () => {
	try {
		d.value = await call("crm_app.dms.get_secondary_summary", { days: 90 })
	} catch (e) {
		/* empty state */
	} finally {
		loading.value = false
	}
})
</script>
