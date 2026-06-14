<template>
	<router-view v-slot="{ Component }">
		<transition name="page" mode="out-in">
			<component :is="Component" />
		</transition>
	</router-view>
	<ToastHost />
</template>

<script setup>
import ToastHost from "./components/ToastHost.vue"
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
