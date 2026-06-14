<template>
	<div
		class="pointer-events-none fixed inset-x-0 top-0 z-[100] flex flex-col items-center gap-2 px-4 pt-3"
		style="padding-top: calc(env(safe-area-inset-top) + 0.5rem)"
	>
		<transition-group name="toast">
			<div
				v-for="t in toasts"
				:key="t.id"
				class="pointer-events-auto flex w-full max-w-sm items-start gap-2.5 rounded-xl px-4 py-3 text-sm font-medium text-white shadow-lg"
				:class="cls(t.type)"
			>
				<component :is="icon(t.type)" class="mt-0.5 h-4 w-4 shrink-0" />
				<span class="flex-1 leading-snug">{{ t.message }}</span>
			</div>
		</transition-group>
	</div>
</template>

<script setup>
import { toasts } from "../utils/toast"
import { CheckCircle2, XCircle, Info } from "lucide-vue-next"

function cls(t) {
	return { success: "bg-green-600", error: "bg-red-600", info: "bg-navy-700" }[t] || "bg-navy-700"
}
function icon(t) {
	return { success: CheckCircle2, error: XCircle, info: Info }[t] || Info
}
</script>
