<template>
	<nav
		class="fixed inset-x-0 bottom-0 z-40 px-3 pb-2"
		style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom))"
	>
		<div class="mx-auto grid max-w-lg grid-cols-5 rounded-[1.4rem] border border-black/5 bg-white/95 px-1 shadow-[0_12px_40px_rgba(23,32,51,0.16)] backdrop-blur-xl dark:border-white/10 dark:bg-navy-800/95">
			<router-link
				v-for="item in items"
				:key="item.name"
				:to="{ name: item.name }"
				class="relative flex min-h-[4rem] flex-col items-center justify-center gap-1 text-[11px]"
				:class="[
					isActive(item.name) ? 'aa-nav-active font-semibold' : 'text-gray-400',
					item.name === 'NewVisit' ? '-mt-5' : '',
				]"
			>
				<span
					class="flex items-center justify-center"
					:class="item.name === 'NewVisit'
						? 'h-14 w-14 rounded-2xl bg-saffron text-navy-800 shadow-[0_8px_22px_rgba(226,164,59,0.34)]'
						: 'h-7 w-10 rounded-xl'"
				>
					<component :is="item.icon" :class="item.name === 'NewVisit' ? 'h-7 w-7' : 'h-5 w-5'" :stroke-width="isActive(item.name) ? 2.4 : 1.8" />
				</span>
				<span :class="item.name === 'NewVisit' ? 'font-bold text-navy-700' : ''">{{ t(item.label) }}</span>
				<span v-if="isActive(item.name) && item.name !== 'NewVisit'" class="absolute bottom-1 h-1 w-1 rounded-full bg-saffron" />
			</router-link>
		</div>
	</nav>
</template>

<script setup>
import { useRoute } from "vue-router"
import { Home, ClipboardList, PlusCircle, Store, Menu } from "lucide-vue-next"
import { t } from "../data/i18n"

const route = useRoute()
const items = [
	{ name: "Dashboard", label: "Home", icon: Home },
	{ name: "Visits", label: "Visits", icon: ClipboardList },
	{ name: "NewVisit", label: "Visit", icon: PlusCircle },
	{ name: "Customers", label: "Dealers", icon: Store },
	{ name: "More", label: "More", icon: Menu },
]

const VISIT_SCREENS = ["Visits", "VisitDetail"]
const DEALER_SCREENS = ["Customers", "CustomerDetail"]

function isActive(name) {
	if (name === "Visits") return VISIT_SCREENS.includes(route.name)
	if (name === "Customers") return DEALER_SCREENS.includes(route.name)
	return route.name === name
}
</script>
