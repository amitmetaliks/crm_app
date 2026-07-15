<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="flex items-center gap-3 bg-navy-700 px-4 py-4 text-white">
			<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="text-lg font-semibold">{{ $t("Notifications") }}</h1>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<div class="aa-card flex items-center justify-between">
				<div class="pr-4">
					<p class="font-semibold text-navy-700 dark:text-white">{{ $t("Push notifications") }}</p>
					<p class="text-xs text-gray-400">Get alerts for visit reminders & follow-ups, even when the app is closed.</p>
				</div>
				<button
					@click="toggle"
					:disabled="busy"
					class="shrink-0 rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
					:class="enabled ? 'bg-gray-400' : 'bg-saffron'"
				>
					{{ busy ? "…" : enabled ? "Turn off" : "Enable" }}
				</button>
			</div>

			<button @click="test" class="aa-card w-full text-left text-sm font-medium text-saffron"> {{ $t("Send a test notification") }} </button>

			<p class="px-1 text-xs text-gray-400">
				If notifications don't appear, allow them for your browser in your phone settings (Settings →
				Apps → Chrome → Notifications).
			</p>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { ChevronLeft } from "lucide-vue-next"
import { enablePush, disablePush, isPushEnabled, showTestNotification } from "../data/push"
import { toast } from "../utils/toast"

const enabled = ref(false)
const busy = ref(false)

async function toggle() {
	busy.value = true
	try {
		if (enabled.value) {
			await disablePush()
			enabled.value = false
			toast.info("Notifications turned off")
		} else {
			await enablePush()
			enabled.value = true
			toast.success("Notifications enabled")
		}
	} catch (e) {
		toast.error(e?.message || "Could not change notifications")
	} finally {
		busy.value = false
	}
}

async function test() {
	try {
		await showTestNotification()
	} catch (e) {
		toast.error(e?.message || "Test failed")
	}
}

onMounted(async () => {
	enabled.value = await isPushEnabled()
})
</script>
