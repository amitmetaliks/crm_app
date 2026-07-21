<template>
	<span
		class="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full font-bold uppercase text-white"
		:class="sizeCls"
		:style="img ? {} : { backgroundColor: color }"
	>
		<img v-if="img" :src="img" class="h-full w-full object-cover" alt="" />
		<span v-else>{{ initials }}</span>
	</span>
</template>

<script setup>
import { computed } from "vue"

const props = defineProps({
	name: { type: String, default: "" },
	img: { type: String, default: "" },
	size: { type: String, default: "md" }, // sm | md | lg
})

const sizeCls = computed(
	() =>
		({ xs: "h-6 w-6 text-[9px]", sm: "h-8 w-8 text-xs", md: "h-11 w-11 text-sm", lg: "h-14 w-14 text-lg" }[
			props.size
		] || "h-11 w-11 text-sm")
)

const initials = computed(() =>
	(props.name || "")
		.trim()
		.split(/\s+/)
		.map((w) => w[0])
		.slice(0, 2)
		.join("")
)

// deterministic colour from the name (brand-friendly palette)
const PALETTE = ["#15264c", "#e8541c", "#2563eb", "#0891b2", "#7c3aed", "#db2777", "#059669", "#d97706", "#4f46e5"]
const color = computed(() => {
	const n = props.name || "?"
	let h = 0
	for (let i = 0; i < n.length; i++) h = (h * 31 + n.charCodeAt(i)) >>> 0
	return PALETTE[h % PALETTE.length]
})
</script>
