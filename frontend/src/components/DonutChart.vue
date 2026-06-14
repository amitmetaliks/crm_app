<template>
	<div class="flex flex-col items-center">
		<svg :viewBox="`0 0 ${size} ${size}`" :width="size" :height="size">
			<circle :cx="c" :cy="c" :r="r" fill="none" stroke="#eef1f5" :stroke-width="sw" />
			<circle
				v-for="(seg, i) in segments"
				:key="i"
				:cx="c"
				:cy="c"
				:r="r"
				fill="none"
				:stroke="seg.color"
				:stroke-width="sw"
				:stroke-dasharray="`${seg.len} ${circ - seg.len}`"
				:stroke-dashoffset="seg.offset"
				:transform="`rotate(-90 ${c} ${c})`"
				stroke-linecap="butt"
			/>
			<text :x="c" :y="c - 4" text-anchor="middle" class="fill-navy-700 dark:fill-white" font-size="13" font-weight="700">{{ centerTop }}</text>
			<text :x="c" :y="c + 14" text-anchor="middle" fill="#94a3b8" font-size="9">{{ centerSub }}</text>
		</svg>
		<div class="mt-3 w-full space-y-1.5">
			<div v-for="(it, i) in items" :key="i" class="flex items-center justify-between text-sm">
				<span class="flex items-center gap-2 truncate text-navy-700 dark:text-white">
					<span class="inline-block h-2.5 w-2.5 shrink-0 rounded-full" :style="{ background: color(i) }"></span>
					<span class="truncate">{{ it.name }}</span>
				</span>
				<span class="shrink-0 font-semibold" :style="{ color: color(i) }">{{ it.pct }}%</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"

const props = defineProps({
	items: { type: Array, default: () => [] }, // [{name, value, pct}]
	size: { type: Number, default: 150 },
	centerTop: { type: String, default: "" },
	centerSub: { type: String, default: "" },
})

const PALETTE = ["#E8541C", "#15264C", "#2f8f5b", "#7c3aed", "#0ea5b7", "#94a3b8"]
function color(i) {
	return PALETTE[i % PALETTE.length]
}
const c = computed(() => props.size / 2)
const sw = computed(() => Math.round(props.size * 0.13))
const r = computed(() => c.value - sw.value)
const circ = computed(() => 2 * Math.PI * r.value)

const segments = computed(() => {
	let acc = 0
	return props.items.map((it, i) => {
		const len = (Number(it.pct) || 0) / 100 * circ.value
		const seg = { len, offset: -acc, color: color(i) }
		acc += len
		return seg
	})
})
</script>
