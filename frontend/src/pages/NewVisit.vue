<template>
	<div class="aa-workspace !pb-32">
		<header class="aa-topbar !items-start">
			<button class="aa-back" @click="goBack"><ChevronLeft class="h-5 w-5" /></button>
			<div class="min-w-0 flex-1 px-1">
				<p class="aa-kicker">Field visit</p>
				<h1 class="mt-1 text-xl font-bold tracking-tight text-navy-800 dark:text-white">{{ checkedIn ? "Visit in progress" : "Start a visit" }}</h1>
				<p class="mt-1 truncate text-xs text-gray-400">{{ selected?.label || "Choose the account, then check in" }}</p>
			</div>
			<span v-if="checkedIn" class="aa-pill aa-pill-green mt-1">Live</span>
		</header>

		<div class="aa-content pb-1 pt-3">
			<div class="aa-panel flex items-center px-4 py-3">
				<div class="flex flex-1 items-center gap-2"><span class="aa-progress-step" :class="selected ? 'aa-progress-step-active' : ''">1</span><span class="text-xs font-semibold" :class="selected ? 'text-navy-700 dark:text-white' : 'text-gray-400'">Account</span></div>
				<div class="mx-2 h-px w-5 bg-gray-200 dark:bg-navy-700" />
				<div class="flex flex-1 items-center justify-center gap-2"><span class="aa-progress-step" :class="checkedIn ? 'aa-progress-step-active' : ''">2</span><span class="text-xs font-semibold" :class="checkedIn ? 'text-navy-700 dark:text-white' : 'text-gray-400'">Capture</span></div>
				<div class="mx-2 h-px w-5 bg-gray-200 dark:bg-navy-700" />
				<div class="flex flex-1 items-center justify-end gap-2"><span class="aa-progress-step">3</span><span class="text-xs font-semibold text-gray-400">Close</span></div>
			</div>
		</div>

		<div class="aa-content space-y-4 pt-4">
			<!-- Resume an unsaved visit the app killed before Save -->
			<div v-if="resumable" class="aa-card border border-amber-200 bg-amber-50 dark:border-amber-900/40">
				<p class="text-sm text-amber-900">{{ $t("You have an unsaved visit for") }} <strong>{{ resumable.selected?.label }}</strong>.</p>
				<p class="mt-0.5 text-xs text-amber-800">{{ $t("Your notes and orders were saved; any photos need to be retaken.") }}</p>
				<div class="mt-2 flex gap-2">
					<button @click="resumeDraft" class="aa-btn-primary !py-2">{{ $t("Resume") }}</button>
					<button @click="discardDraft" class="aa-btn-ghost !py-2">{{ $t("Discard") }}</button>
				</div>
			</div>

			<!-- STEP 1: choose party (locked once checked in) -->
			<div class="aa-panel p-4">
				<p class="aa-kicker">Step 1</p>
				<p class="mb-3 mt-1 text-base font-bold text-navy-800 dark:text-white">{{ $t("Who are you visiting?") }}</p>

				<div v-if="selected" class="flex items-center justify-between rounded-xl bg-saffron/5 p-3">
					<div class="min-w-0">
						<p class="truncate font-semibold text-navy-700 dark:text-white">{{ selected.label }}</p>
						<p class="text-xs text-gray-400">{{ selected.party_type }}{{ selected.sub ? " · " + selected.sub : "" }}</p>
					</div>
					<button v-if="!checkedIn" @click="clearSelected" class="text-xs font-medium text-saffron">{{ $t("Change") }}</button>
				</div>

				<div v-else>
					<div v-if="!prospectMode">
						<input
							v-model="query"
							@input="onSearch"
							class="aa-input"
							:placeholder='$t("Search dealer / customer / lead…")'
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
						<p v-else-if="query.length > 1" class="py-3 text-center text-xs text-gray-400">{{ $t("No matches") }}</p>
						<button @click="prospectMode = true" class="mt-3 text-xs font-medium text-saffron">
							+ New prospect (not in system)
						</button>
					</div>
					<div v-else>
						<input v-model="prospectName" class="aa-input" :placeholder='$t("Prospect / shop name")' />
						<div class="mt-2 flex gap-2">
							<button @click="confirmProspect" class="aa-btn-primary !py-2 text-sm">{{ $t("Use this") }}</button>
							<button @click="prospectMode = false" class="text-xs text-gray-400">{{ $t("Cancel") }}</button>
						</div>
					</div>
				</div>
			</div>

			<!-- STEP 2: purpose + contact (before check-in) -->
			<div v-if="!checkedIn" class="aa-panel space-y-3 p-4">
				<div>
					<label class="mb-1 block text-sm font-medium text-navy-600 dark:text-navy-200">{{ $t("Purpose") }}</label>
					<select v-model="purpose" class="aa-input">
						<option v-for="p in PURPOSES" :key="p">{{ p }}</option>
					</select>
				</div>
				<div class="grid grid-cols-2 gap-2">
					<input v-model="contactName" class="aa-input" :placeholder='$t("Contact name")' />
					<input v-model="contactPhone" class="aa-input" type="tel" :placeholder='$t("Phone")' />
				</div>
			</div>

			<!-- CHECK-IN button -->
			<button
				v-if="!checkedIn"
				@click="doCheckIn"
				:disabled="!canCheckIn || busy"
				class="aa-hero-action w-full !py-4"
			>
				<MapPin class="h-5 w-5" /> {{ busy ? "Getting location…" : "Check in here" }}
			</button>

			<!-- AFTER CHECK-IN: details -->
			<template v-if="checkedIn">
				<div class="aa-panel flex items-center justify-between p-4 text-sm text-green-700">
					<span class="flex items-center gap-2">
					<CheckCircle2 class="h-5 w-5" /> Checked in at {{ checkInLabel }}
					</span>
					<span class="text-xs text-gray-400">Draft saves automatically</span>
				</div>

				<!-- Photos -->
				<div class="aa-panel p-4">
					<p class="mb-2 text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Photos") }}</p>
					<div class="flex flex-wrap gap-2">
						<div v-for="(p, i) in photos" :key="i" class="relative">
							<img :src="p.thumb" class="h-20 w-20 rounded-lg object-cover" />
						</div>
						<label class="flex h-20 w-20 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 text-gray-400">
							<Camera class="h-6 w-6" />
							<span class="mt-1 text-xs">{{ $t("Add") }}</span>
							<input type="file" accept="image/*" capture="environment" class="hidden" @change="onPhoto" />
						</label>
					</div>
					<p v-if="photoBusy" class="mt-2 text-xs text-gray-400">Uploading photo…</p>
				</div>

				<!-- Orders / inquiries -->
				<div class="aa-panel p-4">
					<div class="mb-2 flex items-center justify-between">
						<p class="text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Orders / Inquiries") }}</p>
						<button @click="addOrder" class="text-xs font-medium text-saffron">+ Add</button>
					</div>
					<div v-for="(o, i) in orders" :key="i" class="mb-3 rounded-xl bg-gray-50 p-3 dark:bg-navy-800">
						<div class="mb-2 flex items-center justify-between">
							<select v-model="o.order_type" class="aa-input !w-auto !py-1 text-sm">
								<option>{{ $t("Inquiry") }}</option>
								<option>{{ $t("Firm Order") }}</option>
							</select>
							<button @click="orders.splice(i, 1)"><Trash2 class="h-4 w-4 text-gray-400" /></button>
						</div>
						<div class="grid grid-cols-2 gap-2">
							<select v-model="o.grade" class="aa-input !py-1.5 text-sm">
								<option value="">{{ $t("Grade") }}</option>
								<option v-for="g in GRADES" :key="g">{{ g }}</option>
							</select>
							<input v-model.number="o.quantity_mt" type="number" class="aa-input !py-1.5 text-sm" :placeholder='$t("Qty (MT)")' />
							<input v-model.number="o.rate_per_mt" type="number" class="aa-input !py-1.5 text-sm" :placeholder='$t("Rate/MT")' />
							<input v-model.number="o.expected_value" type="number" class="aa-input !py-1.5 text-sm" :placeholder='$t("Value ₹")' />
						</div>
					</div>
					<p v-if="!orders.length" class="text-xs text-gray-400">{{ $t("No orders/inquiries added.") }}</p>
				</div>

				<!-- Competitors -->
				<div class="aa-panel p-4">
					<div class="mb-2 flex items-center justify-between">
						<p class="text-sm font-semibold text-navy-600 dark:text-navy-200">{{ $t("Competitor info") }}</p>
						<button @click="addCompetitor" class="text-xs font-medium text-saffron">+ Add</button>
					</div>
					<div v-for="(c, i) in competitors" :key="i" class="mb-3 rounded-xl bg-gray-50 p-3 dark:bg-navy-800">
						<div class="mb-2 flex items-center justify-between">
							<input v-model="c.competitor_brand" class="aa-input !py-1 text-sm" :placeholder='$t("Brand")' />
							<button @click="competitors.splice(i, 1)" class="ml-2"><Trash2 class="h-4 w-4 text-gray-400" /></button>
						</div>
						<div class="grid grid-cols-2 gap-2">
							<input v-model.number="c.price_per_mt" type="number" class="aa-input !py-1.5 text-sm" :placeholder='$t("Price/MT")' />
							<select v-model="c.stock_status" class="aa-input !py-1.5 text-sm">
								<option value="">{{ $t("Stock") }}</option>
								<option>{{ $t("In Stock") }}</option>
								<option>{{ $t("Low Stock") }}</option>
								<option>{{ $t("Out of Stock") }}</option>
							</select>
						</div>
					</div>
					<p v-if="!competitors.length" class="text-xs text-gray-400">{{ $t("No competitor info added.") }}</p>
				</div>

				<!-- Notes + outcome -->
				<div class="aa-panel space-y-3 p-4">
					<div>
						<label class="mb-1 block text-sm font-medium text-navy-600 dark:text-navy-200">{{ $t("Notes") }}</label>
						<textarea v-model="notes" rows="3" class="aa-input" :placeholder='$t("What happened on this visit?")'></textarea>
					</div>
					<div class="grid grid-cols-2 gap-2">
						<select v-model="outcome" class="aa-input">
							<option value="">Outcome…</option>
							<option>{{ $t("Positive") }}</option>
							<option>{{ $t("Neutral") }}</option>
							<option>{{ $t("Negative") }}</option>
							<option>{{ $t("Order Received") }}</option>
							<option>{{ $t("No Interest") }}</option>
						</select>
						<input v-model="nextVisitDate" type="date" class="aa-input" />
					</div>
					<input v-model="nextAction" class="aa-input" :placeholder='$t("Next action")' />
				</div>

				<div class="sticky bottom-3 z-20 flex gap-3 rounded-[1.35rem] border border-black/5 bg-white/95 p-2 shadow-[0_12px_35px_rgba(23,32,51,0.18)] backdrop-blur dark:bg-navy-800/95">
					<button @click="save(false)" :disabled="busy" class="aa-quiet-action flex-1"> {{ $t("Save draft") }} </button>
					<button @click="save(true)" :disabled="busy" class="aa-hero-action flex-1"> {{ $t("Check out") }} </button>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from "vue"
import { useRouter, useRoute } from "vue-router"
import { saveDraft, loadDraft, clearDraft } from "../data/draft"
import {
	ChevronLeft, ChevronRight, MapPin, Camera, Trash2, CheckCircle2,
} from "lucide-vue-next"
import dayjs from "dayjs"
import { call } from "../data/api"
import { searchDealers } from "../data/cache"
import { enqueue } from "../data/offline"
import { getPosition } from "../utils/geo"
import { resizeImageToDataURL } from "../utils/image"
import { watermark } from "../utils/watermark"
import { toast } from "../utils/toast"

const router = useRouter()
const route = useRoute()

// Pre-select a dealer when arriving from a customer card (?ptype&id&label).
const resumable = ref(null)

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
	// A saved draft from a visit the app killed before Save — offer to resume it. Surfaced even
	// when arriving for a different dealer (route.query.id present), so an unsaved write-up for
	// dealer A isn't silently overwritten when the rep jumps to dealer B.
	const d = loadDraft()
	if (d && d.selected) resumable.value = d
})

// The serializable write-up (no photos — see draft.js). Snapshotted as the rep types so an
// app-kill can't lose the orders/notes/competitors they entered at the counter.
function snapshot() {
	return {
		selected: selected.value,
		purpose: purpose.value,
		contactName: contactName.value,
		contactPhone: contactPhone.value,
		visitName: visitName.value,
		checkInTime: checkInTime.value,
		checkInData: checkInData.value,
		orders: [...orders],
		competitors: [...competitors],
		notes: notes.value,
		outcome: outcome.value,
		nextAction: nextAction.value,
		nextVisitDate: nextVisitDate.value,
	}
}
function applyDraft(d) {
	if (d.selected) selected.value = d.selected
	purpose.value = d.purpose || "Follow-up"
	contactName.value = d.contactName || ""
	contactPhone.value = d.contactPhone || ""
	visitName.value = d.visitName || null
	checkInTime.value = d.checkInTime || null
	checkInData.value = d.checkInData || {}
	// If the draft was already checked in, restore that state — otherwise the write-up UI
	// (orders/notes/Save, all under v-if="checkedIn") stays hidden and the only control is
	// "Check in" again, which would mint a duplicate visit.
	checkedIn.value = !!d.checkInTime
	orders.splice(0, orders.length, ...(d.orders || []))
	competitors.splice(0, competitors.length, ...(d.competitors || []))
	notes.value = d.notes || ""
	outcome.value = d.outcome || ""
	nextAction.value = d.nextAction || ""
	nextVisitDate.value = d.nextVisitDate || ""
}
function resumeDraft() {
	if (resumable.value) applyDraft(resumable.value)
	resumable.value = null
}
function discardDraft() {
	clearDraft()
	resumable.value = null
}

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
const offlineMode = ref(false)
const photoData = ref([]) // base64 photos kept for offline one-shot submit
const checkInData = ref({})
const clientRef = "v" + Date.now() + "-" + Math.random().toString(36).slice(2, 8)

const photos = ref([])
const orders = reactive([])
const competitors = reactive([])
const notes = ref("")
const outcome = ref("")
const nextAction = ref("")
const nextVisitDate = ref("")

// Persist the draft whenever there's real content to lose (a dealer plus a check-in or any
// captured write-up). Declared AFTER the refs it watches (a watch evaluates its source array
// immediately, so referencing a not-yet-declared const here would crash the page on mount).
// Debounced so a long note doesn't run a synchronous localStorage write on every keystroke.
let draftTimer = null
watch(
	[selected, purpose, contactName, contactPhone, visitName, checkInTime, notes, outcome, nextAction, nextVisitDate, orders, competitors],
	() => {
		if (!selected.value) return
		if (!(checkInTime.value || orders.length || competitors.length || notes.value || outcome.value)) return
		clearTimeout(draftTimer)
		draftTimer = setTimeout(() => saveDraft(snapshot()), 600)
	},
	{ deep: true }
)
// Clear the draft AND cancel any pending debounced save — otherwise a save within the debounce
// window lets the timer fire after clearDraft() and resurrect the just-completed visit's draft.
function dropDraft() {
	clearTimeout(draftTimer)
	clearDraft()
}
onBeforeUnmount(() => clearTimeout(draftTimer))

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
			// Online searches all party types (customers, leads, deals); offline falls back to
			// the locally-cached Customer directory so a visit can still be attached to a dealer.
			results.value = (await searchDealers(query.value, "", 15)) || []
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
		const ts = new Date().toISOString()
		checkInData.value = { time: ts, lat: pos.latitude, lng: pos.longitude }
		if (navigator.onLine) {
			const res = await call("crm_app.field_visit.start_visit", {
				...partyParams(),
				visit_purpose: purpose.value,
				contact_name: contactName.value,
				contact_phone: contactPhone.value,
				latitude: pos.latitude,
				longitude: pos.longitude,
			})
			visitName.value = res.name
			checkInTime.value = res.check_in_time || ts
			toast.success("Checked in")
		} else {
			offlineMode.value = true
			checkInTime.value = ts
			toast.info("Offline — this visit will sync when you're back online")
		}
		checkedIn.value = true
	} catch (e) {
		// Network failure mid-call: continue in offline mode (visit syncs later).
		offlineMode.value = true
		checkInTime.value = checkInData.value.time || new Date().toISOString()
		checkedIn.value = true
		toast.info("Offline — this visit will sync later")
	} finally {
		busy.value = false
	}
}

async function onPhoto(e) {
	const file = e.target.files?.[0]
	if (!file) return
	photoBusy.value = true
	try {
		const pos = await getPosition()
		let dataUrl = await resizeImageToDataURL(file, 1280, 0.8)
		const stamp = [
			dayjs().format("DD MMM YYYY, h:mm A"),
			pos.latitude ? `GPS ${pos.latitude.toFixed(5)}, ${pos.longitude.toFixed(5)}` : "GPS unavailable",
			selected.value?.label || "",
		].filter(Boolean)
		dataUrl = await watermark(dataUrl, stamp)
		photoData.value.push(dataUrl) // kept for offline one-shot submit
		photos.value.push({ thumb: dataUrl, uploaded: false })
		const idx = photoData.value.length - 1
		// Live-upload when we have an online visit; otherwise it rides along on sync.
		if (!offlineMode.value && visitName.value && navigator.onLine) {
			try {
				await call("crm_app.field_visit.add_photo", {
					name: visitName.value,
					content_base64: dataUrl,
					filename: "visit-" + Date.now() + ".jpg",
					latitude: pos.latitude,
					longitude: pos.longitude,
				})
				// Uploaded already — must NOT ride along in the offline payload too, or a
				// later offline save would attach it a second time.
				photos.value[idx].uploaded = true
			} catch (err) {
				/* keep base64 for offline sync */
			}
		}
		toast.success("Photo added")
	} catch (err) {
		toast.error("Photo failed")
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
		const cleanOrders = orders.filter((o) => o.grade || o.quantity_mt || o.expected_value)
		const cleanComps = competitors.filter((c) => c.competitor_brand)

		if (visitName.value && navigator.onLine) {
			// ONLINE: update the already-created visit, then check out.
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
				order_items: JSON.stringify(cleanOrders),
				competitors: JSON.stringify(cleanComps),
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
			dropDraft() // visit saved — cancel any pending debounce + clear
			router.replace({ name: "VisitDetail", params: { name: visitName.value } })
		} else {
			// OFFLINE: queue the whole visit as a single submission (syncs later).
			const pos = checkout ? await getPosition() : {}
			const payload = {
				client_ref: clientRef,
				// If the visit was already created online (check-in) before we went offline,
				// pass its name so the server UPDATES that record instead of creating a second
				// one — the online-checkin + offline-checkout duplicate.
				visit_name: visitName.value || null,
				...partyParams(),
				visit_purpose: purpose.value,
				contact_name: contactName.value,
				contact_phone: contactPhone.value,
				visit_status: "Completed",
				check_in_time: checkInTime.value || checkInData.value.time,
				check_in_latitude: checkInData.value.lat,
				check_in_longitude: checkInData.value.lng,
				check_out_time: new Date().toISOString(),
				check_out_latitude: pos.latitude,
				check_out_longitude: pos.longitude,
				notes: notes.value,
				outcome: outcome.value,
				next_action: nextAction.value,
				next_visit_date: nextVisitDate.value || null,
				order_items: cleanOrders,
				competitors: cleanComps,
			}
			await enqueue("crm_app.field_visit.submit_full_visit", { payload: JSON.stringify(payload) }, "Visit: " + (selected.value?.label || ""))

			// Photos ride as INDEPENDENT queued uploads (not bundled into the visit blob): each
			// is a small, retryable request, visible one-by-one in the Sync Centre, attached by
			// client_ref once the visit lands. Skips any already live-uploaded while online.
			const label = selected.value?.label || "visit"
			const pendingPhotos = photoData.value.filter((b, i) => !photos.value[i]?.uploaded)
			for (let i = 0; i < pendingPhotos.length; i++) {
				await enqueue(
					"crm_app.field_visit.add_visit_photo_by_ref",
					{ client_ref: clientRef, content_base64: pendingPhotos[i], filename: `visit-${clientRef}-${i}.jpg` },
					`Photo ${i + 1} of ${pendingPhotos.length} · ${label}`,
				)
			}

			dropDraft() // queued for sync — cancel any pending debounce + clear
			toast.success(pendingPhotos.length ? `Saved offline — visit + ${pendingPhotos.length} photo(s) will sync` : "Saved offline — will sync automatically")
			router.replace({ name: "Visits" })
		}
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
