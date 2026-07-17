<template>
	<div class="min-h-screen bg-gray-50 pb-24 dark:bg-navy-900">
		<header class="aa-page-header">
			<div class="flex items-center gap-3">
				<button @click="$router.back()"><ChevronLeft class="h-6 w-6" /></button>
				<h1 class="text-xl font-bold">{{ $t("Collect payment") }}</h1>
			</div>
			<p v-if="label" class="mt-1 truncate text-sm text-navy-200">{{ label }}</p>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<!-- Done -->
			<div v-if="done" class="aa-card text-center">
				<CheckCircle2 class="mx-auto h-12 w-12 text-green-500" />
				<p class="mt-2 text-2xl font-bold text-navy-700 dark:text-white">{{ inr(done.amount) }}</p>
				<p class="text-sm text-gray-500">{{ done.mode }} · {{ done.name }}</p>
				<p class="mt-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-800">{{ done.status }}</p>
				<div class="mt-3 flex gap-2">
					<button class="aa-btn-primary flex-1" @click="sendReceipt">{{ $t("Send receipt on WhatsApp") }}</button>
					<router-link to="/collections" class="flex-1 rounded-xl border border-gray-200 py-2.5 text-center text-sm font-semibold text-navy-700 dark:border-navy-700 dark:text-white">{{ $t("Done") }}</router-link>
				</div>
			</div>

			<template v-else>
				<div class="aa-card space-y-3">
					<div>
						<label class="text-xs text-gray-500">{{ $t("Amount collected") }} <span class="text-red-500">*</span></label>
						<input v-model.number="amount" type="number" min="1" step="1" inputmode="numeric" class="aa-input w-full text-2xl font-bold" placeholder="0" />
					</div>

					<div>
						<label class="text-xs text-gray-500">{{ $t("Mode") }}</label>
						<div class="mt-1 flex flex-wrap gap-2">
							<button
								v-for="m in modes"
								:key="m.name"
								class="rounded-lg border px-3 py-1.5 text-sm font-medium"
								:class="mode === m.name ? 'border-saffron bg-saffron text-navy-700' : 'border-gray-200 text-navy-700 dark:border-navy-700 dark:text-white'"
								@click="mode = m.name"
							>{{ m.name }}</button>
						</div>
					</div>

					<div v-if="needsRef">
						<label class="text-xs text-gray-500">{{ mode }} number</label>
						<input v-model="referenceNo" class="aa-input w-full" :placeholder="`${mode} no.`" />
						<label class="mt-2 block text-xs text-gray-500">{{ mode }} date</label>
						<input v-model="referenceDate" type="date" class="aa-input w-full" />
					</div>

					<div>
						<label class="text-xs text-gray-500">{{ $t("Remarks") }}</label>
						<input v-model="remarks" class="aa-input w-full" :placeholder='$t("Optional")' />
					</div>

					<div>
						<label class="text-xs text-gray-500">{{ $t("Photo (cash / cheque / slip)") }}</label>
						<input ref="cam" type="file" accept="image/*" capture="environment" class="hidden" @change="onPhoto" />
						<button
							class="mt-1 flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-semibold text-navy-700 dark:border-navy-700 dark:text-white"
							@click="cam?.click()"
						>
							<Camera class="h-4 w-4" /> {{ photoName || "Add photo" }}
						</button>
					</div>
				</div>

				<p class="px-1 text-xs leading-relaxed text-gray-500">
					The receipt is recorded against the dealer and sent to accounts for verification —
					it is not posted to the books until they confirm the money reached office.
				</p>

				<button class="aa-btn-primary w-full" :disabled="busy || !(amount > 0)" @click="submit">
					{{ busy ? "Recording…" : amount > 0 ? `Record ${inr(amount)}` : "Record payment" }}
				</button>
			</template>
		</div>
		<BottomNav />
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { useRoute } from "vue-router"
import { ChevronLeft, Camera, CheckCircle2 } from "lucide-vue-next"
import BottomNav from "../components/BottomNav.vue"
import { call } from "../data/api"
import { getPosition } from "../utils/geo"
import { resizeImageToDataURL } from "../utils/image"
import { openWhatsApp } from "../utils/wa"
import { toast } from "../utils/toast"
import { inr } from "../utils/money"

const route = useRoute()
const customer = route.query.customer
const label = route.query.label || customer
const phone = route.query.phone || ""

const modes = ref([{ name: "Cash", type: "Cash" }])
const mode = ref("Cash")
const amount = ref(null)
const referenceNo = ref("")
const referenceDate = ref("")
const remarks = ref("")
const photo = ref("")
const photoName = ref("")
const cam = ref(null)
const busy = ref(false)
const done = ref(null)

const needsRef = computed(() => mode.value && mode.value !== "Cash")

async function onPhoto(e) {
	const f = e.target.files?.[0]
	if (!f) return
	photo.value = await resizeImageToDataURL(f, 900, 0.8)
	photoName.value = f.name || "receipt.jpg"
}

async function submit() {
	busy.value = true
	try {
		let pos = {}
		try {
			pos = await getPosition()
		} catch (e) {
			/* location is a nice-to-have on a receipt, not a blocker */
		}
		done.value = await call("crm_app.collections.record_payment", {
			customer,
			amount: amount.value,
			mode_of_payment: mode.value,
			reference_no: referenceNo.value || null,
			reference_date: referenceDate.value || null,
			remarks: remarks.value || null,
			photo_base64: photo.value || null,
			photo_filename: photoName.value || null,
			latitude: pos.latitude ?? null,
			longitude: pos.longitude ?? null,
		})
		toast.success("Payment recorded")
	} catch (err) {
		toast.error(err?.messages?.[0] || err?.message || "Could not record the payment")
	} finally {
		busy.value = false
	}
}

function sendReceipt() {
	const msg =
		`*TRIAM A+ — Payment Receipt*\n\n` +
		`Received with thanks from *${label}*\n` +
		`Amount: *${inr(done.value.amount)}*\n` +
		`Mode: ${done.value.mode}${referenceNo.value ? ` (${referenceNo.value})` : ""}\n` +
		`Date: ${done.value.date}\n` +
		`Ref: ${done.value.name}\n\n` +
		`Subject to realisation. Thank you.`
	openWhatsApp(phone, msg)
}

onMounted(async () => {
	try {
		const m = await call("crm_app.collections.get_payment_modes")
		if (m?.length) {
			modes.value = m
			mode.value = m[0].name
		}
	} catch (e) {
		/* keep the Cash default */
	}
})
</script>
