<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-8 pt-6 text-white">
			<div class="mb-4 inline-block rounded-lg bg-white px-3 py-1.5 shadow-sm">
				<img :src="wordmark" alt="TRIAM A+" class="h-6" />
			</div>
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
				<router-link :to="{ name: 'Beat' }" class="flex items-center gap-3 px-4 py-3.5">
					<Route class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Beat plan</span>
				</router-link>
				<router-link :to="{ name: 'Targets' }" class="flex items-center gap-3 px-4 py-3.5">
					<Target class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">My targets</span>
				</router-link>
				<router-link :to="{ name: 'Collections' }" class="flex items-center gap-3 px-4 py-3.5">
					<IndianRupee class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Collections</span>
				</router-link>
				<router-link :to="{ name: 'Leads' }" class="flex items-center gap-3 px-4 py-3.5">
					<UserPlus class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Leads &amp; Deals</span>
				</router-link>
			</div>

			<p class="px-1 pt-2 text-xs font-semibold uppercase tracking-wide text-gray-400">My workplace</p>
			<div class="aa-card divide-y divide-gray-100 !p-0 dark:divide-navy-700">
				<router-link :to="{ name: 'Attendance' }" class="flex items-center gap-3 px-4 py-3.5">
					<CalendarCheck class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Attendance</span>
				</router-link>
				<router-link :to="{ name: 'Conveyance' }" class="flex items-center gap-3 px-4 py-3.5">
					<Fuel class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Conveyance (auto)</span>
				</router-link>
				<router-link :to="{ name: 'Expense' }" class="flex items-center gap-3 px-4 py-3.5">
					<Receipt class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Expense claims</span>
				</router-link>
				<router-link :to="{ name: 'Leave' }" class="flex items-center gap-3 px-4 py-3.5">
					<CalendarOff class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Leave</span>
				</router-link>
				<router-link :to="{ name: 'Salary' }" class="flex items-center gap-3 px-4 py-3.5">
					<Wallet class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Salary slips</span>
				</router-link>
				<router-link :to="{ name: 'Kra' }" class="flex items-center gap-3 px-4 py-3.5">
					<Award class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">My KRA scorecard</span>
				</router-link>
				<router-link :to="{ name: 'Timeline' }" class="flex items-center gap-3 px-4 py-3.5">
					<Clock class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Activity timeline</span>
				</router-link>
				<router-link :to="{ name: 'Route' }" class="flex items-center gap-3 px-4 py-3.5">
					<MapPin class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">My route &amp; distance</span>
				</router-link>
				<router-link :to="{ name: 'Insights' }" class="flex items-center gap-3 px-4 py-3.5">
					<Sparkles class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Smart insights</span>
				</router-link>
				<router-link :to="{ name: 'Schemes' }" class="flex items-center gap-3 px-4 py-3.5">
					<Tag class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Active schemes</span>
				</router-link>
			</div>

			<p class="px-1 pt-2 text-xs font-semibold uppercase tracking-wide text-gray-400">Security</p>
			<div class="aa-card divide-y divide-gray-100 !p-0 dark:divide-navy-700">
				<button @click="setupPin" class="flex w-full items-center gap-3 px-4 py-3.5 text-left">
					<KeyRound class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">{{ pinOn ? "Change app PIN" : "Set app PIN" }}</span>
				</button>
				<button v-if="pinOn" @click="removePin" class="flex w-full items-center gap-3 px-4 py-3.5 text-left">
					<KeyRound class="h-5 w-5 text-gray-400" /> <span class="text-sm text-gray-500">Remove app PIN</span>
				</button>
				<button v-if="pinOn && bioCan" @click="toggleBio" class="flex w-full items-center gap-3 px-4 py-3.5 text-left">
					<Fingerprint class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">{{ bioOn ? "Disable biometric unlock" : "Enable biometric unlock" }}</span>
				</button>
			</div>

			<div v-if="session.isSalesManager">
				<p class="px-1 pt-2 text-xs font-semibold uppercase tracking-wide text-gray-400">Manager</p>
				<div class="aa-card divide-y divide-gray-100 !p-0 dark:divide-navy-700">
					<router-link :to="{ name: 'Approvals' }" class="flex items-center gap-3 px-4 py-3.5">
						<CheckSquare class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Approvals</span>
					</router-link>
					<router-link :to="{ name: 'Analytics' }" class="flex items-center gap-3 px-4 py-3.5">
						<BarChart3 class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Analytics</span>
					</router-link>
					<router-link :to="{ name: 'Team' }" class="flex items-center gap-3 px-4 py-3.5">
						<Users class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Team activity</span>
					</router-link>
					<router-link :to="{ name: 'TeamMap' }" class="flex items-center gap-3 px-4 py-3.5">
						<MapPin class="h-5 w-5 text-saffron" /> <span class="text-sm text-navy-700 dark:text-white">Team live map</span>
					</router-link>
				</div>
			</div>

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
import { Bell, Moon, LogOut, Route, Target, IndianRupee, UserPlus, Users, CalendarCheck, Receipt, CalendarOff, Wallet, CheckSquare, BarChart3, Award, Clock, MapPin, Sparkles, KeyRound, Fingerprint, Tag, Fuel } from "lucide-vue-next"
import { hasPin, setPin, clearLock, bioSupported, bioEnabled, enableBio, disableBio } from "../data/lock"
import { toast } from "../utils/toast"
import BottomNav from "../components/BottomNav.vue"
import { session, logoutResource } from "../data/session"
import { isDark, setDark } from "../utils/theme"
import wordmark from "../assets/logo-wordmark.png"

const router = useRouter()
const version = "0.1.0"
const dark = ref(isDark())
const pinOn = ref(hasPin())
const bioOn = ref(bioEnabled())
const bioCan = bioSupported()

async function setupPin() {
	const pin = window.prompt("Set a 4-digit app PIN:")
	if (!pin) return
	if (!/^\d{4}$/.test(pin)) { toast.error("PIN must be 4 digits"); return }
	await setPin(pin)
	pinOn.value = true
	toast.success("App PIN set")
}
function removePin() {
	clearLock()
	pinOn.value = false
	bioOn.value = false
	toast.info("App PIN removed")
}
async function toggleBio() {
	if (bioOn.value) { disableBio(); bioOn.value = false; toast.info("Biometric unlock off") }
	else {
		const ok = await enableBio()
		bioOn.value = ok
		toast[ok ? "success" : "error"](ok ? "Biometric unlock enabled" : "Couldn't enable biometric")
	}
}

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
