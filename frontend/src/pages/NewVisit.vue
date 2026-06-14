<template>
	<div class="min-h-screen bg-gray-50 pb-28 dark:bg-navy-900">
		<header class="flex items-center gap-3 bg-navy-700 px-4 py-4 text-white">
			<button @click="goBack"><ChevronLeft class="h-6 w-6" /></button>
			<h1 class="text-lg font-semibold">{{ checkedIn ? "Visit in progress" : "Start a Visit" }}</h1>
		</header>

		<div class="mx-auto max-w-xl space-y-4 p-4">
			<!-- STEP 1: choose party (locked once checked in) -->
			<div class="aa-card">
				<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">Who are you visiting?</p>

				<div v-if="selected" class="flex items-center justify-between rounded-xl bg-saffron/5 p-3">
					<div class="min-w-0">
						<p class="truncate font-semibold text-navy-700 dark:text-white">{{ selected.label }}</p>
						<p class="text-xs text-gray-400">{{ selected.party_type }}{{ selected.sub ? " · " + selected.sub : "" }}</p>
					</div>
					<button v-if="!checkedIn" @click="clearSelected" class="text-xs font-medium text-saffron">Change</button>
				</div>

				<div v-else>
					<div v-if="!prospectMode">
						<input
							v-model="query"
							@input="onSearch"
							class="aa-input"
							placeholder="Search dealer / customer / lead…"
						/>
						<div v-if="searching" class="py-3 text-center text-xs text-gray-400">Searching…</div>
						<ul v-else-if="results.length" class="mt-2 divide-y divide-gray-100">
							<li
								v-for="r in results"
								:key="r.party_type + r.id"
								@click="pick(r)"
								class="flex cursor-pointer items-center justify-between py-2.5"
							>
								<div class="min-w-0">
									<p class="truncate text-sm font-medium text-navy-700 dark:text-white">{{ r.label }}</p>
									<p class="text-xs text-gray-400">{{ r.party_type }}{{ r.sub ? " · " + r.sub : "" }}</p>
								</div>
								<ChevronRight class="h-4 w-4 text-gray-300" />
							</li>
						</ul>
						<p v-else-if="query.length > 1" class="py-3 text-center text-xs text-gray-400">No matches</p>
						<button @click="prospectMode = true" class="mt-3 text-xs font-medium text-saffron">
							+ New prospect (not in system)
						</button>
					</div>
					<div v-else>
						<input v-model="prospectName" class="aa-input" placeholder="Prospect / shop name" />
						<div class="mt-2 flex gap-2">
							<button @click="confirmProspect" class="aa-btn-primary !py-2 text-sm">Use this</button>
							<button @click="prospectMode = false" class="text-xs text-gray-400">Cancel</button>
						</div>
					</div>
				</div>
			</div>

			<!-- STEP 2: purpose + contact (before check-in) -->
			<div v-if="!checkedIn" class="aa-card space-y-3">
				<div>
					<label class="mb-1 block text-sm font-medium text-navy-600 dark:text-navy-200">Purpose</label>
					<select v-model="purpose" class="aa-input">
						<option v-for="p in PURPOSES" :key="p">{{ p }}</option>
					</select>
				</div>
				<div class="grid grid-cols-2 gap-2">
					<input v-model="contactName" class="aa-input" placeholder="Contact name" />
					<input v-model="contactPhone" class="aa-input" type="tel" placeholder="Phone" />
				</div>
			</div>

			<!-- CHECK-IN button -->
			<button
				v-if="!checkedIn"
				@click="doCheckIn"
				:disabled="!canCheckIn || busy"
				class="flex w-full items-center justify-center gap-2 rounded-2xl bg-saffron px-4 py-4 font-semibold text-white shadow-lg shadow-saffron/30 disabled:opacity-50 active:scale-[0.99]"
			>
				<MapPin class="h-5 w-5" /> {{ busy ? "Getting location…" : "Check in here" }}
			</button>

			<!-- AFTER CHECK-IN: details -->
			<template v-if="checkedIn">
				<div class="aa-card flex items-center gap-2 text-sm text-green-700">
					<CheckCircle2 class="h-5 w-5" /> Checked in at {{ checkInLabel }}
				</div>

				<!-- Photos -->
				<div class="aa-card">
					<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">Photos</p>
					<div class="flex flex-wrap gap-2">
						<div v-for="(p, i) in photos" :key="i" class="relative">
							<img :src="p.thumb" class="h-20 w-20 rounded-lg object-cover" />
						</div>
						<label class="flex h-20 w-20 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 text-gray-400">
							<Camera class="h-6 w-6" />
							<span class="mt-1 text-[10px]">Add</span>
							<input type="file" accept="image/*" capture="environment" class="hidden" @change="onPhoto" />
						</label>
					</div>
					<p v-if="photoBusy" class="mt-2 text-xs text-gray-400">Uploading photo…</p>
				</div>

				<!-- Orders / inquiries -->
				<div class="aa-card">
					<div class="mb-2 flex items-center justify-between">
						<p class="text-sm font-semibold text-navy-600 dark:text-navy-200">Orders / Inquiries</p>
						<button @click="addOrder" class="text-xs font-medium text-saffron">+ Add</button>
					</div>
					<div v-for="(o, i) in orders" :key="i" class="mb-3 rounded-xl bg-gray-50 p-3 dark:bg-navy-800">
						<div class="mb-2 flex items-center justify-between">
							<select v-model="o.order_type" class="aa-input !w-auto !py-1 text-sm">
								<option>Inquiry</option>
								<option>Firm Order</option>
							</select>
							<button @click="orders.splice(i, 1)"><Trash2 class="h-4 w-4 text-gray-400" /></button>
						</div>
						<div class="grid grid-cols-2 gap-2">
							<select v-model="o.grade" class="aa-input !py-1.5 text-sm">
								<option value="">Grade</option>
								<option v-for="g in GRADES" :key="g">{{ g }}</option>
							</select>
							<input v-model.number="o.quantity_mt" type="number" class="aa-input !py-1.5 text-sm" placeholder="Qty (MT)" />
							<input v-model.number="o.rate_per_mt" type="number" class="aa-input !py-1.5 text-sm" placeholder="Rate/MT" />
							<input v-model.number="o.expected_value" type="number" class="aa-input !py-1.5 text-sm" placeholder="Value ₹" />
						</div>
					</div>
					<p v-if="!orders.length" class="text-xs text-gray-400">No orders/inquiries added.</p>
				</div>

				<!-- Competitors -->
				<div class="aa-card">
					<div class="mb-2 flex items-center justify-between">
						<p class="text-sm font-semibold text-navy-600 dark:text-navy-200">Competitor info</p>
						<button @click="addCompetitor" class="text-xs font-medium text-saffron">+ Add</button>
					</div>
					<div v-for="(c, i) in competitors" :key="i" class="mb-3 rounded-xl bg-gray-50 p-3 dark:bg-navy-800">
						<div class="mb-2 flex items-center justify-between">
							<input v-model="c.competitor_brand" class="aa-input !py-1 text-sm" placeholder="Brand" />
							<button @click="competitors.splice(i, 1)" class="ml-2"><Trash2 class="h-4 w-4 text-gray-400" /></button>
						</div>
						<div class="grid grid-cols-2 gap-2">
							<input v-model.number="c.price_per_mt" type="number" class="aa-input !py-1.5 text-sm" placeholder="Price/MT" />
							<select v-model="c.stock_status" class="aa-input !py-1.5 text-sm">
								<option value="">Stock</option>
								<option>In Stock</option>
								<option>Low Stock</option>
								<option>Out of Stock</option>
							</select>
						</div>
					</div>
					<p v-if="!competitors.length" class="text-xs text-gray-400">No competitor info added.</p>
				</div>

				<!-- Notes + outcome -->
				<div class="aa-card space-y-3">
					<div>
						<label class="mb-1 block text-sm font-medium text-navy-600 dark:text-navy-200">Notes</label>
						<textarea v-model="notes" rows="3" class="aa-input" placeholder="What happened on this visit?"></textarea>
					</div>
					<div class="grid grid-cols-2 gap-2">
						<select v-model="outcome" class="aa-input">
							<option value="">Outcome…</option>
							<option>Positive</option>
							<option>Neutral</option>
							<option>Negative</option>
							<option>Order Received</option>
							<option>No Interest</option>
						</select>
						<input v-model="nextVisitDate" type="date" class="aa-input" />
					</div>
					<input v-model="nextAction" class="aa-input" placeholder="Next action" />
				</div>

				<div class="flex gap-3">
					<button @click="save(false)" :disabled="busy" class="flex-1 rounded-2xl bg-navy-700 px-4 py-3.5 font-semibold text-white disabled:opacity-50">
						Save
					</button>
					<button @click="save(true)" :disabled="busy" class="flex-1 rounded-2xl bg-saffron px-4 py-3.5 font-semibold text-white shadow-lg shadow-saffron/30 disabled:opacity-50">
						Check out
					</button>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue"
import { useRouter, useRoute } from "vue-router"
import {
	ChevronLeft, ChevronRight, MapPin, Camera, Trash2, CheckCircle2,
} from "lucide-vue-next"
import dayjs from "dayjs"
import { call } from "../data/api"
import { getPosition } from "../utils/geo"
import { resizeImageToDataURL } from "../utils/image"
import { toast } from "../utils/toast"

const router = useRouter()
const route = useRoute()

// Pre-select a dealer when arriving from a customer card (?ptype&id&label).
onMounted(() => {
	if (route.query.id && route.query.ptype) {
		selected.value = {
			party_type: route.query.ptype,
			id: route.query.id,
			label: route.query.label || route.query.id,
			sub: route.query.sub || "",
		}
	}
	if (route.query.purpose) purpose.value = route.query.purpose
})

const PURPOSES = [
	"New Dealer Onboarding", "Follow-up", "Order Booking", "Payment Collection",
	"Complaint Resolution", "Site Inspection", "Relationship", "Market Survey", "Other",
]
const GRADES = ["Fe 415", "Fe 500", "Fe 500D", "Fe 550", "Fe 550D", "Fe 600", "Other"]

// selection
const query = ref("")
const results = ref([])
const searching = ref(false)
const selected = ref(null)
const prospectMode = ref(false)
const prospectName = ref("")
let searchTimer = null

const purpose = ref("Follow-up")
const contactName = ref("")
const contactPhone = ref("")

// active visit
const checkedIn = ref(false)
const visitName = ref(null)
const checkInTime = ref(null)
const busy = ref(false)
const photoBusy = ref(false)

const photos = ref([])
const orders = reactive([])
const competitors = reactive([])
const notes = ref("")
const outcome = ref("")
const nextAction = ref("")
const nextVisitDate = ref("")

const canCheckIn = computed(() => !!selected.value)
const checkInLabel = computed(() => (checkInTime.value ? dayjs(checkInTime.value).format("h:mm A") : ""))

function onSearch() {
	clearTimeout(searchTimer)
	if (query.value.trim().length < 2) {
		results.value = []
		return
	}
	searching.value = true
	searchTimer = setTimeout(async () => {
		try {
			results.value = (await call("crm_app.customers.search_parties", { query: query.value, limit: 15 })) || []
		} catch (e) {
			results.value = []
		} finally {
			searching.value = false
		}
	}, 300)
}

function pick(r) {
	selected.value = r
	if (r.phone && !contactPhone.value) contactPhone.value = r.phone
	results.value = []
	query.value = ""
}
function confirmProspect() {
	if (!prospectName.value.trim()) return
	selected.value = { party_type: "Prospect", id: null, label: prospectName.value.trim(), sub: "New prospect" }
	prospectMode.value = false
}
function clearSelected() {
	selected.value = null
}

function partyParams() {
	const s = selected.value
	const p = { party_type: s.party_type }
	if (s.party_type === "Customer") p.customer = s.id
	else if (s.party_type === "CRM Lead") p.crm_lead = s.id
	else if (s.party_type === "CRM Deal") p.crm_deal = s.id
	else if (s.party_type === "Prospect") p.prospect_name = s.label
	return p
}

async function doCheckIn() {
	if (!canCheckIn.value) return
	busy.value = true
	try {
		const pos = await getPosition()
		const res = await call("crm_app.field_visit.start_visit", {
			...partyParams(),
			visit_purpose: purpose.value,
			contact_name: contactName.value,
			contact_phone: contactPhone.value,
			latitude: pos.latitude,
			longitude: pos.longitude,
		})
		visitName.value = res.name
		checkInTime.value = res.check_in_time || new Date().toISOString()
		checkedIn.value = true
		toast.success("Checked in")
	} catch (e) {
		toast.error(e?.messages?.[0] || "Could not check in")
	} finally {
		busy.value = false
	}
}

async function onPhoto(e) {
	const file = e.target.files?.[0]
	if (!file) return
	photoBusy.value = true
	try {
		const dataUrl = await resizeImageToDataURL(file, 1280, 0.8)
		const pos = await getPosition()
		await call("crm_app.field_visit.add_photo", {
			name: visitName.value,
			content_base64: dataUrl,
			filename: "visit-" + Date.now() + ".jpg",
			latitude: pos.latitude,
			longitude: pos.longitude,
		})
		photos.value.push({ thumb: dataUrl })
		toast.success("Photo added")
	} catch (err) {
		toast.error(err?.messages?.[0] || "Photo upload failed")
	} finally {
		photoBusy.value = false
		e.target.value = ""
	}
}

function addOrder() {
	orders.push({ order_type: "Inquiry", grade: "", quantity_mt: null, rate_per_mt: null, expected_value: null })
}
function addCompetitor() {
	competitors.push({ competitor_brand: "", price_per_mt: null, stock_status: "" })
}

async function save(checkout) {
	busy.value = true
	try {
		await call("crm_app.field_visit.save_visit", {
			name: visitName.value,
			...partyParams(),
			visit_purpose: purpose.value,
			contact_name: contactName.value,
			contact_phone: contactPhone.value,
			notes: notes.value,
			outcome: outcome.value,
			next_action: nextAction.value,
			next_visit_date: nextVisitDate.value || null,
			order_items: JSON.stringify(orders.filter((o) => o.grade || o.quantity_mt || o.expected_value)),
			competitors: JSON.stringify(competitors.filter((c) => c.competitor_brand)),
		})
		if (checkout) {
			const pos = await getPosition()
			await call("crm_app.field_visit.check_out", {
				name: visitName.value,
				latitude: pos.latitude,
				longitude: pos.longitude,
			})
			toast.success("Visit completed")
		} else {
			toast.success("Saved")
		}
		router.replace({ name: "VisitDetail", params: { name: visitName.value } })
	} catch (e) {
		toast.error(e?.messages?.[0] || "Could not save")
	} finally {
		busy.value = false
	}
}

function goBack() {
	router.back()
}
</script>
