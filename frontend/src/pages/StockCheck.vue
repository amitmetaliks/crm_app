<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-5 pt-6 text-white">
			<div class="flex items-center gap-3">
				<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
				<h1 class="text-xl font-bold">{{ $t("Stock check") }}</h1>
			</div>
			<p v-if="label" class="mt-1 truncate text-sm text-navy-200">{{ label }}</p>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<!-- Saved -->
			<div v-if="done" class="aa-card text-center">
				<CheckCircle2 class="mx-auto h-10 w-10 text-green-500" />
				<p class="mt-2 font-semibold text-navy-700 dark:text-white">{{ $t("Stock recorded") }}</p>
				<div class="mt-3 grid grid-cols-3 gap-2 text-center">
					<div>
						<p class="text-xs text-gray-400">{{ $t("Closing") }}</p>
						<p class="font-bold text-navy-700 dark:text-white">{{ num(done.total_closing_mt) }} MT</p>
					</div>
					<div>
						<p class="text-xs text-gray-400">{{ $t("Our share") }}</p>
						<p class="font-bold text-saffron">{{ done.our_share_pct }}%</p>
					</div>
					<div>
						<p class="text-xs text-gray-400">{{ $t("Sold") }}</p>
						<p class="font-bold text-navy-700 dark:text-white">{{ num(done.total_sold_mt) }} MT</p>
					</div>
				</div>
				<!-- The number worth arguing about, shown plainly. -->
				<p v-if="gap > 0.5" class="mt-3 rounded-lg bg-amber-50 p-2 text-left text-xs text-amber-900">
					{{ $t("Stock movement suggests") }} <strong>{{ num(done.implied_total_mt) }} MT</strong>
					{{ $t("sold, but the dealer reported") }} <strong>{{ num(done.total_sold_mt) }} MT</strong>.
					{{ $t("Worth a second look at the count.") }}
				</p>
				<button class="aa-btn-primary mt-3 w-full" @click="reset">{{ $t("Done") }}</button>
			</div>

			<template v-else>
				<div v-if="last.exists" class="rounded-xl bg-navy-50 p-3 text-xs text-navy-700 dark:bg-navy-800 dark:text-navy-100">
					{{ $t("Last checked") }} {{ fmtDate(last.check_date) }} · {{ $t("our share was") }}
					<strong>{{ last.our_share_pct }}%</strong>. {{ $t("Grades below are pre-filled from that visit.") }}
				</div>

				<div v-for="(row, i) in rows" :key="i" class="aa-card space-y-2">
					<div class="flex items-center gap-2">
						<input v-model="row.item_code" class="aa-input flex-1" :placeholder='$t("Grade / item")' />
						<button class="shrink-0 rounded-lg p-2 text-gray-400" @click="rows.splice(i, 1)">
							<Trash2 class="h-4 w-4" />
						</button>
					</div>
					<div class="flex gap-2">
						<button
							v-for="b in ['Ours', 'Competitor']"
							:key="b"
							class="flex-1 rounded-lg border px-2 py-1.5 text-xs font-semibold"
							:class="row.brand_type === b ? 'border-saffron bg-saffron text-white' : 'border-gray-200 text-navy-700 dark:border-navy-700 dark:text-white'"
							@click="row.brand_type = b"
						>{{ $t(b) }}</button>
					</div>
					<div class="grid grid-cols-2 gap-2">
						<div>
							<label class="text-xs text-gray-500">{{ $t("Closing stock (MT)") }}</label>
							<input v-model.number="row.closing_qty_mt" type="number" step="0.001" min="0" inputmode="decimal" class="aa-input w-full" />
						</div>
						<div>
							<label class="text-xs text-gray-500">{{ $t("Sold since last (MT)") }}</label>
							<input v-model.number="row.sold_qty_mt" type="number" step="0.001" min="0" inputmode="decimal" class="aa-input w-full" />
						</div>
					</div>
				</div>

				<button
					class="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-gray-300 py-2.5 text-sm font-semibold text-navy-700 dark:border-navy-700 dark:text-white"
					@click="addRow"
				>
					<Plus class="h-4 w-4" /> {{ $t("Add grade") }}
				</button>

				<div class="aa-card">
					<label class="text-xs text-gray-500">{{ $t("Remarks") }}</label>
					<input v-model="remarks" class="aa-input w-full" :placeholder='$t("Optional")' />
				</div>

				<div class="aa-card flex items-center justify-between text-sm">
					<span class="text-gray-500">{{ $t("Total closing") }}</span>
					<span class="font-bold text-navy-700 dark:text-white">{{ num(totalClosing) }} MT · {{ sharePct }}% {{ $t("ours") }}</span>
				</div>

				<button class="aa-btn-primary w-full" :disabled="busy || !valid" @click="save">
					{{ busy ? $t("Saving…") : $t("Save stock check") }}
				</button>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { useRoute } from "vue-router"
import { ChevronLeft, Plus, Trash2, CheckCircle2 } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import { call } from "../data/api"
import { toast } from "../utils/toast"
import { num } from "../utils/money"

const route = useRoute()
const customer = route.query.customer
const label = route.query.label || customer
const visit = route.query.visit || null

const rows = ref([])
const remarks = ref("")
const busy = ref(false)
const done = ref(null)
const last = ref({ exists: false, items: [] })

function fmtDate(d) { return d ? dayjs(d).format("DD MMM") : "" }
function addRow() { rows.value.push({ item_code: "", brand_type: "Ours", closing_qty_mt: null, sold_qty_mt: null }) }

const totalClosing = computed(() => rows.value.reduce((s, r) => s + (Number(r.closing_qty_mt) || 0), 0))
const sharePct = computed(() => {
	const ours = rows.value.filter((r) => r.brand_type === "Ours").reduce((s, r) => s + (Number(r.closing_qty_mt) || 0), 0)
	return totalClosing.value ? Math.round((ours / totalClosing.value) * 100) : 0
})
const valid = computed(() => rows.value.some((r) => (r.item_code || "").trim()))
const gap = computed(() => (done.value ? (done.value.implied_total_mt || 0) - (done.value.total_sold_mt || 0) : 0))

function reset() {
	done.value = null
	load()
}

async function save() {
	busy.value = true
	try {
		done.value = await call("crm_app.dms.record_stock", {
			customer,
			visit,
			remarks: remarks.value || null,
			items: JSON.stringify(rows.value.filter((r) => (r.item_code || "").trim())),
		})
		toast.success("Stock check saved")
	} catch (err) {
		toast.error(err?.messages?.[0] || err?.message || "Could not save the stock check")
	} finally {
		busy.value = false
	}
}

async function load() {
	try {
		last.value = await call("crm_app.dms.get_last_stock", { customer })
		// Re-counting the same grades is the normal case — start from last time's list.
		rows.value = (last.value.items || []).map((i) => ({
			item_code: i.item_code,
			item_name: i.item_name,
			brand_type: i.brand_type || "Ours",
			closing_qty_mt: null,
			sold_qty_mt: null,
		}))
	} catch (e) {
		/* first ever check for this dealer */
	}
	if (!rows.value.length) addRow()
}

onMounted(load)
</script>
