<template>
	<div>
		<div class="flex items-end justify-between gap-1.5" :style="{ height: height + 'px' }">
			<div v-for="(d, i) in data" :key="i" class="flex flex-1 flex-col items-center justify-end gap-1">
				<span class="text-[10px] font-semibold text-navy-600 dark:text-navy-200">{{ d.achieved }}</span>
				<div class="w-full rounded-t-md bg-saffron" :style="{ height: barH(d.achieved) + 'px' }"></div>
			</div>
		</div>
		<div class="mt-1 flex justify-between gap-1.5">
			<span v-for="(d, i) in data" :key="i" class="flex-1 text-center text-[10px] text-gray-400">{{ d.label }}</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"

const props = defineProps({
	data: { type: Array, default: () => [] }, // [{label, achieved}]
	height: { type: Number, default: 110 },
})

const max = computed(() => Math.max(1, ...props.data.map((d) => Number(d.achieved) || 0)))
function barH(v) {
	return Math.max(3, Math.round(((Number(v) || 0) / max.value) * (props.height - 18)))
}
</script>
