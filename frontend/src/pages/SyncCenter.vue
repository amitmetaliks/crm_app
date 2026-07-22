<template>
	<div class="aa-workspace">
		<header class="aa-topbar !items-start">
			<button class="aa-back" @click="$router.back()"><ChevronLeft class="h-5 w-5" /></button>
			<div class="min-w-0 flex-1 px-1">
				<p class="aa-kicker">Offline reliability</p>
				<h1 class="mt-1 text-xl font-bold tracking-tight text-navy-800 dark:text-white">Sync centre</h1>
				<p class="mt-1 text-xs text-gray-400">Every saved submission stays visible until the server confirms it.</p>
			</div>
			<span class="aa-pill" :class="net.online ? 'aa-pill-green' : 'aa-pill-gray'">{{ net.online ? "Online" : "Offline" }}</span>
		</header>

		<main class="aa-content space-y-5 pt-3">
			<section class="aa-hero !p-5">
				<div class="flex items-start justify-between gap-4">
					<div><p class="text-sm font-semibold text-white/60">Saved on this device</p><p class="mt-1 text-3xl font-bold">{{ items.length }}</p><p class="mt-1 text-xs text-white/50">{{ failedCount }} need attention · {{ pendingCount }} waiting</p><p class="mt-2 text-xs text-white/50">Last confirmed sync: {{ net.lastSynced ? age(net.lastSynced) : "not yet" }}</p></div>
					<div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10"><CloudCog class="h-6 w-6 text-amber-200" /></div>
				</div>
				<button :disabled="!net.online || net.syncing || !pendingCount" class="aa-hero-action mt-5 w-full" @click="syncNow"><RefreshCw class="h-4 w-4" :class="net.syncing ? 'animate-spin' : ''" />{{ net.syncing ? "Syncing…" : "Sync now" }}</button>
			</section>

			<div v-if="!items.length" class="aa-panel p-8 text-center">
				<CheckCircle2 class="mx-auto h-10 w-10 text-green-600" />
				<h2 class="mt-3 font-bold text-navy-800 dark:text-white">Everything is synced</h2>
				<p class="mt-1 text-sm text-gray-400">New offline work will appear here until the server confirms it.</p>
			</div>

			<section v-else>
				<div class="aa-section-head"><h2 class="aa-section-heading">Submission queue</h2><button class="aa-section-link" @click="load">Refresh</button></div>
				<div class="aa-panel overflow-hidden">
					<div v-for="item in items" :key="item.id" class="border-b border-[#e7e5df] p-4 last:border-0 dark:border-navy-700">
						<div class="flex items-start gap-3">
							<span class="aa-icon-surface"><component :is="item.failed ? AlertTriangle : Clock3" class="h-5 w-5" /></span>
							<div class="min-w-0 flex-1"><p class="truncate text-sm font-semibold text-navy-800 dark:text-white">{{ item.label || friendly(item.method) }}</p><p class="mt-0.5 text-xs text-gray-400">Saved {{ age(item.ts) }}</p><p v-if="item.error" class="mt-2 rounded-lg bg-red-50 p-2 text-xs text-red-600">{{ item.error }}</p></div>
							<span class="aa-pill" :class="item.failed ? 'aa-pill-red' : 'aa-pill-amber'">{{ item.failed ? "Action needed" : "Waiting" }}</span>
						</div>
						<div v-if="item.failed" class="mt-3 flex gap-2 pl-[3.25rem]"><button class="aa-quiet-action flex-1 !min-h-10 !py-2" @click="retry(item.id)">Retry</button><button class="aa-quiet-action !min-h-10 !border-red-200 !py-2 !text-red-600" @click="discard(item.id)">Discard</button></div>
					</div>
				</div>
			</section>
		</main>
	</div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { ChevronLeft, CloudCog, RefreshCw, CheckCircle2, AlertTriangle, Clock3 } from "lucide-vue-next"
import { net, queuedRecs, flush, retryItem, discardItem } from "../data/offline"

const items = ref([])
const failedCount = computed(() => items.value.filter((item) => item.failed).length)
const pendingCount = computed(() => items.value.filter((item) => !item.failed).length)

async function load() { items.value = await queuedRecs() }
async function syncNow() { await flush(); await load() }
async function retry(id) { await retryItem(id); await load() }
async function discard(id) {
	if (!window.confirm("Discard this saved submission? This cannot be undone.")) return
	await discardItem(id)
	await load()
}
function friendly(method) { return String(method || "Submission").split(".").pop().replaceAll("_", " ") }
function age(timestamp) {
	const minutes = Math.max(0, Math.round((Date.now() - Number(timestamp || Date.now())) / 60000))
	if (minutes < 1) return "just now"
	if (minutes < 60) return `${minutes} min ago`
	const hours = Math.round(minutes / 60)
	return hours < 24 ? `${hours} hr ago` : `${Math.round(hours / 24)} day(s) ago`
}
onMounted(load)
</script>
