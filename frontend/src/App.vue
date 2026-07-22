<template>
	<!-- Failed submissions win the banner: they are held, not lost, and need the rep to
	     act. Red, and tappable to retry them all. -->
	<router-link
		v-if="net.failed"
		:to="{ name: 'SyncCenter' }"
		class="fixed inset-x-0 top-0 z-50 cursor-pointer px-3 py-1.5 text-center text-xs font-semibold text-white"
		style="padding-top: env(safe-area-inset-top); background-color: #cc2929"
	>
		{{ net.failed }} submission(s) couldn't be saved — tap to retry
	</router-link>
	<router-link
		v-else-if="!net.online || net.pending"
		:to="{ name: 'SyncCenter' }"
		class="fixed inset-x-0 top-0 z-50 px-3 py-1.5 text-center text-xs font-medium"
		:class="!net.online ? 'bg-gray-600 text-white' : 'bg-saffron text-navy-700'"
		style="padding-top: env(safe-area-inset-top)"
	>
		<span v-if="!net.online">Offline — your check-ins, visits &amp; claims are saved and will sync<span v-if="net.pending"> ({{ net.pending }} pending)</span></span>
		<span v-else-if="net.pending">{{ net.syncing ? "Syncing" : "Pending sync" }} — {{ net.pending }} item(s)…</span>
	</router-link>
	<!-- Online but the last read was served from cache (a live request failed on weak signal):
	     say so, so last-known numbers aren't mistaken for live ones. -->
	<div
		v-else-if="cacheState.stale"
		class="fixed inset-x-0 top-0 z-50 bg-gray-500 px-3 py-1.5 text-center text-xs font-medium text-white"
		style="padding-top: env(safe-area-inset-top)"
	>
		Showing saved data<span v-if="cacheState.at"> from {{ savedAgo }}</span> — reconnecting…
	</div>

	<router-view v-slot="{ Component }">
		<transition name="page" mode="out-in">
			<component :is="Component" />
		</transition>
	</router-view>
	<ToastHost />
</template>

<script setup>
import { computed } from "vue"
import ToastHost from "./components/ToastHost.vue"
import { net } from "./data/offline"
import { cacheState } from "./data/cache"

const savedAgo = computed(() => {
	if (!cacheState.at) return ""
	const mins = Math.round((Date.now() - cacheState.at) / 60000)
	if (mins < 1) return "just now"
	if (mins < 60) return `${mins} min ago`
	const hrs = Math.round(mins / 60)
	if (hrs < 24) return `${hrs} hr ago`
	return `${Math.round(hrs / 24)} day(s) ago`
})
</script>

<style>
/* page transition — gentle slide-fade, feels native */
.page-enter-active {
	transition: opacity 0.22s ease, transform 0.22s ease;
}
.page-leave-active {
	transition: opacity 0.13s ease;
}
.page-enter-from {
	opacity: 0;
	transform: translateY(8px);
}
.page-leave-to {
	opacity: 0;
}

/* toast transition */
.toast-enter-active {
	transition: opacity 0.25s ease, transform 0.25s ease;
}
.toast-leave-active {
	transition: opacity 0.2s ease, transform 0.2s ease;
}
.toast-enter-from,
.toast-leave-to {
	opacity: 0;
	transform: translateY(-12px);
}
</style>
