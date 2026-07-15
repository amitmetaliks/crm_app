<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-6 pt-6 text-white">
			<button @click="$router.back()" class="mb-2 flex items-center gap-1 text-sm text-navy-200"><ChevronLeft class="h-5 w-5" /> Back</button>
			<h1 class="text-xl font-bold">Attendance</h1>
			<p class="text-sm text-navy-200">{{ todayLabel }}</p>
		</header>

		<div class="mx-auto -mt-3 max-w-xl space-y-4 px-4">
			<div class="aa-card text-center">
				<p class="text-sm text-gray-400">
					{{ ov.checked_in ? "You are checked IN" : (ov.first_in ? "Checked out for the day" : "Not checked in yet") }}
				</p>
				<div class="mt-2 flex justify-center gap-6 text-sm">
					<div><p class="text-xs text-gray-400">In</p><p class="font-semibold text-navy-700 dark:text-white">{{ fmtTime(ov.first_in) || "—" }}</p></div>
					<div><p class="text-xs text-gray-400">Out</p><p class="font-semibold text-navy-700 dark:text-white">{{ fmtTime(ov.last_out) || "—" }}</p></div>
				</div>

				<img v-if="preview" :src="preview" class="mx-auto mt-3 h-28 w-28 rounded-xl object-cover ring-2 ring-saffron/30" />

				<button
					@click="startCapture"
					:disabled="busy"
					class="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-4 font-semibold text-white shadow-lg disabled:opacity-50 active:scale-[0.99]"
					:class="nextAction === 'IN' ? 'bg-saffron shadow-saffron/30' : 'bg-navy-700'"
				>
					<Camera class="h-5 w-5" /> {{ busy ? "Recording…" : (nextAction === "IN" ? "Selfie Check-IN" : "Selfie Check-OUT") }}
				</button>
				<p class="mt-2 text-xs text-gray-400">A selfie + your location are captured to mark attendance.</p>
				<input ref="cam" type="file" accept="image/*" capture="user" class="hidden" @change="onSelfie" />
			</div>

			<div>
				<h2 class="mb-2 px-1 text-sm font-semibold text-navy-600 dark:text-navy-200">Today's punches</h2>
				<EmptyState v-if="!ov.logs_today || !ov.logs_today.length" title="No punches yet today" />
				<div v-else class="space-y-2">
					<div v-for="(l, i) in ov.logs_today" :key="i" class="aa-card flex items-center justify-between">
						<span class="flex items-center gap-2 text-sm font-medium" :class="l.log_type === 'IN' ? 'text-green-600' : 'text-navy-700 dark:text-white'">
							<LogIn v-if="l.log_type === 'IN'" class="h-4 w-4" /><LogOut v-else class="h-4 w-4" /> {{ l.log_type }}
						</span>
						<span class="text-sm text-gray-500">{{ fmtTime(l.time) }}</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { ChevronLeft, Camera, LogIn, LogOut } from "lucide-vue-next"
import dayjs from "dayjs"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { callOrQueue } from "../data/offline"
import { getPosition } from "../utils/geo"
import { resizeImageToDataURL } from "../utils/image"
import { watermark } from "../utils/watermark"
import { toast } from "../utils/toast"
import { startDutyTracking, stopDutyTracking } from "../data/native"

const ov = ref({ logs_today: [], next_action: "IN" })
const busy = ref(false)
const preview = ref("")
const cam = ref(null)
const todayLabel = dayjs().format("dddd, DD MMM YYYY")
const nextAction = computed(() => ov.value.next_action || "IN")

function fmtTime(t) { return t ? dayjs(t).format("h:mm A") : "" }

async function load() {
	try { ov.value = await call("crm_app.attendance.get_attendance_overview") } catch (e) { /* */ }
}
function startCapture() { cam.value?.click() }

async function onSelfie(e) {
	const file = e.target.files?.[0]
	if (!file) return
	busy.value = true
	try {
		const pos = await getPosition()
		let selfie = await resizeImageToDataURL(file, 720, 0.8)
		const stamp = [
			dayjs().format("DD MMM YYYY, h:mm A"),
			pos.latitude ? `GPS ${pos.latitude.toFixed(5)}, ${pos.longitude.toFixed(5)}` : "GPS unavailable",
		]
		selfie = await watermark(selfie, stamp)
		preview.value = selfie
		const res = await callOrQueue(
			"crm_app.attendance.check_in_out",
			{ latitude: pos.latitude, longitude: pos.longitude, selfie_base64: selfie },
			"Attendance",
		)
		if (res?.queued) toast.success("Saved offline — will sync when online")
		else toast.success(`Checked ${res.log_type} at ${fmtTime(res.time)}`)
		// Route recording (native app) runs only between check-IN and check-OUT.
		// On the web/PWA these are no-ops.
		const action = res?.log_type || (res?.queued ? nextAction.value : null)
		if (action === "IN") startDutyTracking()
		else if (action === "OUT") stopDutyTracking()
		await load()
	} catch (err) {
		toast.error(err?.messages?.[0] || err?.message || "Could not record attendance")
	} finally {
		busy.value = false
		e.target.value = ""
	}
}
onMounted(load)
</script>
