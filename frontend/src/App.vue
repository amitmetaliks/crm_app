<template>
	<!-- Failed submissions win the banner: they are held, not lost, and need the rep to
	     act. Red, and tappable to retry them all. -->
	<div
		v-if="net.failed"
		class="fixed inset-x-0 top-0 z-50 cursor-pointer px-3 py-1.5 text-center text-xs font-semibold text-white"
		style="padding-top: env(safe-area-inset-top); background-color: #cc2929"
		@click="retryFailed"
	>
		{{ net.failed }} submission(s) couldn't be saved — tap to retry
	</div>
	<div
		v-else-if="!net.online || net.pending"
		class="fixed inset-x-0 top-0 z-50 px-3 py-1.5 text-center text-xs font-medium"
		:class="!net.online ? 'bg-gray-600 text-white' : 'bg-saffron text-navy-700'"
		style="padding-top: env(safe-area-inset-top)"
	>
		<span v-if="!net.online">Offline — your check-ins, visits &amp; claims are saved and will sync<span v-if="net.pending"> ({{ net.pending }} pending)</span></span>
		<span v-else-if="net.pending">{{ net.syncing ? "Syncing" : "Pending sync" }} — {{ net.pending }} item(s)…</span>
	</div>

	<router-view v-slot="{ Component }">
		<transition name="page" mode="out-in">
			<component :is="Component" />
		</transition>
	</router-view>
	<ToastHost />
</template>

<script setup>
import ToastHost from "./components/ToastHost.vue"
import { net, retryFailed } from "./data/offline"
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
