<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="flex items-center gap-3 bg-navy-700 px-4 py-4 text-white">
			<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="truncate text-lg font-semibold">{{ c?.customer_name || name }}</h1>
		</header>

		<div v-if="loading" class="mx-auto max-w-xl p-4"><Skeleton :count="3" /></div>

		<div v-else-if="c" class="mx-auto max-w-xl space-y-4 p-4">
			<div class="aa-card space-y-1">
				<p class="text-lg font-bold text-navy-700 dark:text-white">{{ c.customer_name }}</p>
				<p v-if="c.territory || c.customer_group" class="text-sm text-gray-500">
					{{ [c.territory, c.customer_group].filter(Boolean).join(" · ") }}
				</p>
				<p v-if="c.mobile_no" class="text-sm text-gray-500">{{ c.mobile_no }}</p>
			</div>

			<div class="aa-card flex items-center justify-between">
				<div>
					<p class="text-xs text-gray-400">Outstanding</p>
					<p class="text-xl font-bold" :class="outstanding > 0 ? 'text-red-600' : 'text-green-600'">
						₹{{ fmt(outstanding) }}
					</p>
				</div>
				<router-link
					:to="{ name: 'NewVisit', query: { ptype: 'Customer', id: name, label: c.customer_name } }"
					class="rounded-xl bg-saffron px-4 py-2.5 text-sm font-semibold text-white"
				>
					Start visit
				</router-link>
			</div>

			<div>
				<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">Visit history</h2>
				<EmptyState v-if="!visits.length" title="No visits yet" />
				<div v-else class="space-y-2">
					<router-link
						v-for="vi in visits"
						:key="vi.name"
						:to="{ name: 'VisitDetail', params: { name: vi.name } }"
						class="aa-card flex items-center justify-between"
					>
						<div>
							<p class="text-sm font-medium text-navy-700 dark:text-white">{{ vi.visit_purpose }}</p>
							<p class="text-xs text-gray-400">{{ formatDate(vi.visit_date) }} · {{ vi.sales_person_name }}</p>
						</div>
						<span class="text-xs text-gray-400">{{ vi.visit_status }}</span>
					</router-link>
				</div>
			</div>
		</div>

		<EmptyState v-else class="m-4" title="Customer not found" />
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronLeft } from "lucide-vue-next"
import dayjs from "dayjs"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"

const props = defineProps({ name: { type: String, required: true } })
const c = ref(null)
const visits = ref([])
const outstanding = ref(0)
const loading = ref(true)

function formatDate(d) { return d ? dayjs(d).format("DD MMM YYYY") : "" }
function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }

onMounted(async () => {
	try {
		const d = await call("crm_app.customers.get_customer", { name: props.name })
		c.value = d.customer
		visits.value = d.visits || []
		outstanding.value = d.outstanding || 0
	} catch (e) {
		c.value = null
	} finally {
		loading.value = false
	}
})
</script>
