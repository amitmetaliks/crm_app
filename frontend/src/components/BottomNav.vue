<template>
	<nav
		class="fixed inset-x-0 bottom-0 z-40 border-t border-gray-100 bg-white/95 backdrop-blur dark:bg-navy-800/95"
		style="padding-bottom: env(safe-area-inset-bottom)"
	>
		<div class="mx-auto grid max-w-xl grid-cols-5">
			<router-link
				v-for="item in items"
				:key="item.name"
				:to="{ name: item.name }"
				class="flex flex-col items-center gap-1 py-2.5 text-[11px]"
				:class="isActive(item.name) ? 'text-saffron' : 'text-gray-400'"
			>
				<component :is="item.icon" class="h-6 w-6" :stroke-width="isActive(item.name) ? 2.4 : 1.8" />
				<span :class="isActive(item.name) ? 'font-semibold' : ''">{{ t(item.label) }}</span>
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
	{ name: "NewVisit", label: "Start", icon: PlusCircle },
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
