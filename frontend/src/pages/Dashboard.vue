<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<!-- Header -->
		<header class="bg-gradient-to-b from-navy-700 to-navy-600 px-5 pb-6 pt-6 text-white">
			<div class="flex items-center justify-between">
				<div class="rounded-lg bg-white px-3 py-1.5 shadow-sm">
					<img :src="wordmark" alt="TRIAM A+" class="h-6" />
				</div>
				<router-link :to="{ name: 'Notifications' }" class="rounded-full bg-white/10 p-2.5"><Bell class="h-5 w-5" /></router-link>
			</div>
			<div class="mt-4">
				<p class="text-sm text-navy-200">{{ greeting }},</p>
				<h1 class="text-xl font-bold">{{ home.employee_name || session.employeeName || "Field Sales" }}</h1>
			</div>
			<!-- Week strip -->
			<div class="mt-4 flex justify-between gap-1">
				<div v-for="d in week" :key="d.iso" class="flex flex-1 flex-col items-center rounded-xl py-2"
					:class="d.isToday ? 'bg-white text-navy-700' : 'text-navy-100'">
					<span class="text-[10px]">{{ d.dow }}</span>
					<span class="text-sm font-bold">{{ d.day }}</span>
				</div>
			</div>
		</header>

		<div class="mx-auto -mt-3 max-w-xl space-y-4 px-4">
			<p v-if="session.gateLoaded && !session.hasEmployee" class="aa-card border border-amber-200 bg-amber-50 text-sm text-amber-800">
				Your login isn't linked to an Employee record yet, so data can't be saved. Please ask your admin to link your account.
			</p>

			<!-- Attendance -->
			<router-link :to="{ name: 'Attendance' }" class="aa-card flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="flex h-10 w-10 items-center justify-center rounded-full" :class="home.attendance?.checked_in ? 'bg-green-100 text-green-600' : 'bg-navy-100 text-navy-700'">
						<CalendarCheck class="h-5 w-5" />
					</div>
					<div>
						<p class="font-semibold text-navy-700 dark:text-white">{{ home.attendance?.checked_in ? "On duty" : "Mark attendance" }}</p>
						<p class="text-xs text-gray-400">
							In {{ fmtTime(home.attendance?.first_in) || "--:--" }} · Out {{ fmtTime(home.attendance?.last_out) || "--:--" }}
						</p>
					</div>
				</div>
				<span class="rounded-lg bg-saffron px-3 py-1.5 text-xs font-semibold text-white">{{ home.attendance?.checked_in ? "Check out" : "Check in" }}</span>
			</router-link>

			<!-- Quick action -->
			<router-link :to="{ name: 'NewVisit' }" class="flex items-center justify-center gap-2 rounded-2xl bg-saffron px-4 py-4 font-semibold text-white shadow-lg shadow-saffron/30 active:scale-[0.99]">
				<MapPin class="h-5 w-5" /> Start a Visit
			</router-link>

			<!-- Today's beat + productivity -->
			<div class="aa-card">
				<div class="mb-3 flex items-center justify-between">
					<p class="text-sm font-semibold text-navy-600 dark:text-navy-200">Today</p>
					<router-link :to="{ name: 'Beat' }" class="text-xs font-medium text-saffron">Beat: {{ home.beat?.visited || 0 }}/{{ home.beat?.planned || 0 }}</router-link>
				</div>
				<div class="grid grid-cols-4 gap-2 text-center">
					<div><p class="text-lg font-bold text-navy-700 dark:text-white">{{ v.total || 0 }}</p><p class="text-[10px] text-gray-400">Visits</p></div>
					<div><p class="text-lg font-bold text-green-600">{{ v.productive || 0 }}</p><p class="text-[10px] text-gray-400">Productive</p></div>
					<div><p class="text-lg font-bold text-amber-500">{{ v.zero_order || 0 }}</p><p class="text-[10px] text-gray-400">Zero order</p></div>
					<div><p class="text-lg font-bold text-saffron">{{ v.strike_rate || 0 }}%</p><p class="text-[10px] text-gray-400">Strike</p></div>
				</div>
			</div>

			<!-- Order summary -->
			<div class="grid grid-cols-2 gap-3">
				<div class="aa-card"><p class="text-xl font-bold text-navy-700 dark:text-white">{{ o.orders || 0 }}</p><p class="text-xs text-gray-400">Orders today</p></div>
				<div class="aa-card"><p class="text-xl font-bold text-navy-700 dark:text-white">{{ inrShort(o.value) }}</p><p class="text-xs text-gray-400">Order value</p></div>
				<div class="aa-card"><p class="text-xl font-bold text-navy-700 dark:text-white">{{ fmt(o.qty) }} MT</p><p class="text-xs text-gray-400">Total qty</p></div>
				<div class="aa-card"><p class="text-xl font-bold text-navy-700 dark:text-white">{{ home.new_retailers || 0 }}</p><p class="text-xs text-gray-400">New retailers (mo)</p></div>
			</div>

			<!-- Sales target -->
			<router-link :to="{ name: 'Targets' }" class="aa-card block">
				<div class="mb-1 flex justify-between text-sm">
					<span class="font-semibold text-navy-600 dark:text-navy-200">Sales target (month)</span>
					<span class="text-gray-500">{{ inrShort(home.sales_target?.achieved) }} / {{ inrShort(home.sales_target?.target) }}</span>
				</div>
				<div class="h-2.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-navy-700">
					<div class="h-full rounded-full bg-saffron" :style="{ width: Math.min(100, home.sales_target?.pct || 0) + '%' }"></div>
				</div>
				<p class="mt-1 text-right text-xs text-gray-400">{{ home.sales_target?.pct || 0 }}%</p>
			</router-link>

			<!-- Expense -->
			<router-link :to="{ name: 'Expense' }" class="aa-card flex items-center justify-between">
				<div>
					<p class="font-semibold text-navy-700 dark:text-white">Expenses</p>
					<p class="text-xs text-gray-400">Today {{ inrShort(home.expense?.today) }} · Month {{ inrShort(home.expense?.month) }}</p>
				</div>
				<span class="rounded-lg bg-navy-100 px-3 py-1.5 text-xs font-semibold text-navy-700">+ Add</span>
			</router-link>

			<!-- Quick access -->
			<div class="grid grid-cols-4 gap-3">
				<router-link :to="{ name: 'Kra' }" class="aa-card flex flex-col items-center gap-1 py-3 text-center"><Award class="h-6 w-6 text-saffron" /><span class="text-[11px] font-medium text-navy-700 dark:text-white">KRA</span></router-link>
				<router-link :to="{ name: 'Timeline' }" class="aa-card flex flex-col items-center gap-1 py-3 text-center"><Clock class="h-6 w-6 text-saffron" /><span class="text-[11px] font-medium text-navy-700 dark:text-white">Timeline</span></router-link>
				<router-link :to="{ name: 'Collections' }" class="aa-card flex flex-col items-center gap-1 py-3 text-center"><IndianRupee class="h-6 w-6 text-saffron" /><span class="text-[11px] font-medium text-navy-700 dark:text-white">Collect</span></router-link>
				<router-link :to="{ name: 'Customers' }" class="aa-card flex flex-col items-center gap-1 py-3 text-center"><Store class="h-6 w-6 text-saffron" /><span class="text-[11px] font-medium text-navy-700 dark:text-white">Dealers</span></router-link>
			</div>
		</div>

		<BottomNav />
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue"
import { Bell, MapPin, CalendarCheck, Award, Clock, IndianRupee, Store } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import { session } from "../data/session"
import { call } from "../data/api"
import { inrShort } from "../utils/money"
import wordmark from "../assets/logo-wordmark.png"

const home = ref({})
const v = computed(() => home.value.visits || {})
const o = computed(() => home.value.order_summary || {})

const greeting = computed(() => {
	const h = new Date().getHours()
	return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening"
})

const week = computed(() => {
	const today = dayjs()
	const monday = today.subtract((today.day() + 6) % 7, "day")
	return Array.from({ length: 7 }, (_, i) => {
		const d = monday.add(i, "day")
		return { iso: d.format("YYYY-MM-DD"), dow: d.format("dd")[0], day: d.format("D"), isToday: d.isSame(today, "day") }
	})
})

function fmtTime(t) { return t ? dayjs(t).format("h:mm A") : "" }
function fmt(n) { return Number(n || 0).toLocaleString("en-IN") }

onMounted(async () => {
	try { home.value = await call("crm_app.sfa.get_home_summary") } catch (e) { /* */ }
})
</script>
