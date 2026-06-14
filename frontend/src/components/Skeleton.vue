<template>
	<div class="space-y-2">
		<div v-for="n in count" :key="n" class="aa-card">
			<div class="aa-skel h-4 w-2/3 rounded"></div>
			<div class="aa-skel mt-2.5 h-3 w-2/5 rounded"></div>
			<div v-if="bar" class="aa-skel mt-3 h-2 w-full rounded-full"></div>
		</div>
	</div>
</template>

<script setup>
defineProps({
	count: { type: Number, default: 4 },
	bar: { type: Boolean, default: false },
})
</script>
