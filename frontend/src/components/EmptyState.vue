<template>
	<div class="aa-card flex flex-col items-center justify-center px-6 py-10 text-center">
		<div class="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-saffron/10 text-saffron">
			<component :is="icon" class="h-7 w-7" />
		</div>
		<p class="font-semibold text-navy-700">{{ title }}</p>
		<p v-if="subtitle" class="mt-1 max-w-xs text-sm text-gray-400">{{ subtitle }}</p>
		<div v-if="$slots.default" class="mt-4"><slot /></div>
	</div>
</template>

<script setup>
import { Inbox } from "lucide-vue-next"
defineProps({
	icon: { type: [Object, Function], default: () => Inbox },
	title: { type: String, default: "Nothing here yet" },
	subtitle: { type: String, default: "" },
})
</script>
