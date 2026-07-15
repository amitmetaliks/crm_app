<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="bg-navy-700 px-5 pb-5 pt-6 text-white">
			<div class="flex items-center gap-3">
				<router-link to="/more"><ChevronLeft class="h-6 w-6" /></router-link>
				<h1 class="text-xl font-bold">Conveyance</h1>
			</div>
			<p class="mt-1 text-sm text-navy-200">{{ todayLabel }}</p>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<Skeleton v-if="loading" :count="3" />

			<template v-else>
				<!-- Already claimed -->
				<div v-if="c.claimed" class="aa-card text-center">
					<CheckCircle2 class="mx-auto h-10 w-10 text-green-500" />
					<p class="mt-2 font-semibold text-navy-700 dark:text-white">Conveyance already claimed</p>
					<p class="mt-1 text-sm text-gray-500">
						{{ inr(c.claim?.amount) }} · {{ c.claim?.approval_status || c.claim?.status }}
					</p>
					<router-link to="/expense" class="mt-3 inline-block text-sm font-semibold text-saffron">View my claims</router-link>
				</div>

				<!-- No rate configured -->
				<EmptyState
					v-else-if="c.rate_missing"
					title="No travel rate set"
					subtitle="Ask HR to set 'Travel Allowance Per Km' on your Sales Person record, then this will calculate automatically."
				/>

				<template v-else>
					<!-- The calculation -->
					<div class="aa-card">
						<p class="text-xs uppercase tracking-wide text-gray-400">Distance recorded today</p>
						<p class="text-4xl font-bold text-navy-700 dark:text-white">{{ c.gps_km }} <span class="text-lg font-medium text-gray-400">km</span></p>
						<div class="mt-3 flex items-center justify-between border-t border-gray-100 pt-3 text-sm dark:border-navy-700">
							<span class="text-gray-500">{{ c.gps_km }} km × ₹{{ c.rate_per_km }}/km</span>
							<span class="text-2xl font-bold text-saffron">{{ inr(c.amount) }}</span>
						</div>
					</div>

					<p class="px-1 text-xs leading-relaxed text-gray-500">{{ c.note }}</p>

					<!-- Correction -->
					<div class="aa-card">
						<label class="flex items-center gap-2 text-sm font-medium text-navy-700 dark:text-white">
							<input v-model="correct" type="checkbox" class="h-4 w-4 rounded" />
							The distance is wrong — I want to correct it
						</label>

						<div v-if="correct" class="mt-3 space-y-3">
							<div>
								<label class="text-xs text-gray-500">Actual distance (km)</label>
								<input v-model.number="km" type="number" min="0" step="0.1" class="aa-input w-full" placeholder="e.g. 82" />
							</div>
							<div>
								<label class="text-xs text-gray-500">Reason <span class="text-red-500">*</span></label>
								<textarea v-model="remarks" rows="3" class="aa-input w-full" placeholder="e.g. Went via Durgapur bypass; GPS lost signal for 20 km"></textarea>
							</div>
							<div>
								<label class="text-xs text-gray-500">Attach proof (optional)</label>
								<input ref="cam" type="file" accept="image/*" capture="environment" class="hidden" @change="onFile" />
								<button
									class="mt-1 flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-semibold text-navy-700 dark:border-navy-700 dark:bg-navy-800 dark:text-white"
									@click="cam?.click()"
								>
									<Camera class="h-4 w-4" /> {{ fileName || "Add photo (toll slip, odometer…)" }}
								</button>
							</div>
							<p v-if="km" class="rounded-lg bg-amber-50 p-2 text-center text-sm text-amber-800">
								Claiming <strong>{{ km }} km</strong> = <strong>{{ inr(km * c.rate_per_km) }}</strong>
								<span class="block text-xs">Your manager will see the GPS reading of {{ c.gps_km }} km too.</span>
							</p>
						</div>
					</div>

					<button class="aa-btn-primary w-full" :disabled="busy || !canSubmit" @click="submit">
						{{ busy ? "Submitting…" : `Claim ${inr(payable)}` }}
					</button>
				</template>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { ChevronLeft, CheckCircle2, Camera } from "lucide-vue-next"
import dayjs from "dayjs"
import BottomNav from "../components/BottomNav.vue"
import Skeleton from "../components/Skeleton.vue"
import EmptyState from "../components/EmptyState.vue"
import { call } from "../data/api"
import { resizeImageToDataURL } from "../utils/image"
import { toast } from "../utils/toast"
import { inr } from "../utils/money"

const c = ref({ gps_km: 0, rate_per_km: 0, amount: 0, claimed: false })
const loading = ref(true)
const busy = ref(false)
const correct = ref(false)
const km = ref(null)
const remarks = ref("")
const photo = ref("")
const fileName = ref("")
const cam = ref(null)
const todayLabel = dayjs().format("dddd, DD MMM YYYY")

const payable = computed(() => {
	const d = correct.value && km.value ? km.value : c.value.gps_km
	return (d || 0) * (c.value.rate_per_km || 0)
})
const canSubmit = computed(() => {
	if (correct.value) return km.value > 0 && remarks.value.trim().length > 0
	return c.value.gps_km > 0
})

async function onFile(e) {
	const f = e.target.files?.[0]
	if (!f) return
	photo.value = await resizeImageToDataURL(f, 900, 0.8)
	fileName.value = f.name || "photo.jpg"
}

async function load() {
	try {
		c.value = await call("crm_app.conveyance.get_today_conveyance")
	} catch (e) {
		toast.error("Could not load conveyance")
	} finally {
		loading.value = false
	}
}

async function submit() {
	busy.value = true
	try {
		const res = await call("crm_app.conveyance.claim_conveyance", {
			claimed_km: correct.value ? km.value : null,
			remarks: remarks.value || null,
			attachment_base64: photo.value || null,
			attachment_filename: fileName.value || null,
		})
		toast.success(`Claimed ${inr(res.amount)}${res.submitted ? "" : " (pending submit)"}`)
		correct.value = false
		await load()
	} catch (err) {
		toast.error(err?.messages?.[0] || err?.message || "Could not claim conveyance")
	} finally {
		busy.value = false
	}
}

onMounted(load)
</script>
