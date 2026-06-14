<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-8 pt-6 text-white">
			<div class="flex items-center gap-3">
				<div class="flex h-12 w-12 items-center justify-center rounded-full bg-saffron text-lg font-bold">
					{{ initials }}
				</div>
				<div>
					<p class="font-semibold">{{ session.employeeName || session.user }}</p>
					<p class="text-xs text-navy-200">{{ session.isSalesManager ? "Sales Manager" : "Field Sales" }}</p>
				</div>
			</div>
		</header>

		<div class="mx-auto -mt-4 max-w-xl space-y-3 px-4">
			<div class="aa-card divide-y divide-gray-100 !p-0 dark:divide-navy-700">
				<router-link :to="{ name: 'Notifications' }" class="flex items-center gap-3 px-4 py-3.5">
					<Bell class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Notifications</span>
				</router-link>
				<button @click="toggleTheme" class="flex w-full items-center gap-3 px-4 py-3.5 text-left">
					<Moon class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">{{ dark ? "Light mode" : "Dark mode" }}</span>
				</button>
			</div>

			<button @click="onLogout" class="aa-card flex w-full items-center gap-3 text-left text-sm font-medium text-red-600">
				<LogOut class="h-5 w-5" /> Sign out
			</button>

			<p class="pt-2 text-center text-xs text-gray-400">TRIAM A+ · Field Sales · v{{ version }}</p>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed } from "vue"
import { useRouter } from "vue-router"
import { Bell, Moon, LogOut } from "lucide-vue-next"
import BottomNav from "../components/BottomNav.vue"
import { session, logoutResource } from "../data/session"
import { isDark, setDark } from "../utils/theme"

const router = useRouter()
const version = "0.1.0"
const dark = ref(isDark())

const initials = computed(() => {
	const n = session.employeeName || session.user || "?"
	return n.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()
})

function toggleTheme() {
	dark.value = setDark(!dark.value)
}

async function onLogout() {
	try {
		await logoutResource.submit()
	} catch (e) {
		/* ignore */
	}
	window.location.href = "/amit-crm/login"
}
</script>
