<template>
	<div @touchstart="onStart" @touchmove="onMove" @touchend="onEnd">
		<div class="flex items-center justify-center overflow-hidden text-saffron" :style="{ height: h + 'px', opacity: h > 4 ? 1 : 0 }">
			<RefreshCw class="h-5 w-5" :class="refreshing ? 'animate-spin' : ''" :style="refreshing ? {} : { transform: `rotate(${pull * 2.2}deg)` }" />
		</div>
		<slot />
	</div>
</template>

<script setup>
import { computed, ref } from "vue"
import { RefreshCw } from "lucide-vue-next"

const props = defineProps({ onRefresh: { type: Function, default: null } })
const startY = ref(-1)
const pull = ref(0)
const refreshing = ref(false)
const THRESHOLD = 70

const h = computed(() => (refreshing.value ? 38 : Math.min(pull.value, 80)))

function atTop() {
	return (window.scrollY || document.documentElement.scrollTop || 0) <= 0
}
function onStart(e) {
	startY.value = !refreshing.value && atTop() ? e.touches[0].clientY : -1
	pull.value = 0
}
function onMove(e) {
	if (startY.value < 0 || refreshing.value) return
	const d = e.touches[0].clientY - startY.value
	if (d > 0 && atTop()) {
		pull.value = d * 0.5
		if (e.cancelable) e.preventDefault()
	} else {
		pull.value = 0
	}
}
async function onEnd() {
	if (refreshing.value) return
	const trigger = pull.value >= THRESHOLD
	pull.value = 0
	startY.value = -1
	if (trigger && props.onRefresh) {
		refreshing.value = true
		try {
			await props.onRefresh()
		} catch (e) {
			/* ignore */
		} finally {
			refreshing.value = false
		}
	}
}
</script>
