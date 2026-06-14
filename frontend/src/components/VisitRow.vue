<template>
	<router-link
		:to="{ name: 'VisitDetail', params: { name: visit.name } }"
		class="aa-card flex items-center justify-between"
	>
		<div class="min-w-0">
			<p class="truncate font-semibold text-navy-700 dark:text-white">
				{{ visit.party_display || visit.name }}
			</p>
			<p class="truncate text-xs text-gray-400">
				{{ visit.visit_purpose }} · {{ formatDate(visit.visit_date) }}
			</p>
		</div>
		<span class="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold" :class="badgeClass">
			{{ visit.visit_status }}
		</span>
	</router-link>
</template>

<script setup>
import dayjs from "dayjs"

const props = defineProps({ visit: { type: Object, required: true } })

function formatDate(d) {
	return d ? dayjs(d).format("DD MMM") : ""
}

const STATUS_CLASS = {
	Planned: "bg-gray-100 text-gray-600",
	"In Progress": "bg-saffron/15 text-saffron",
	Completed: "bg-green-100 text-green-700",
	Cancelled: "bg-gray-100 text-gray-400 line-through",
	Missed: "bg-red-100 text-red-600",
}
import { computed } from "vue"
const badgeClass = computed(() => STATUS_CLASS[props.visit.visit_status] || "bg-gray-100 text-gray-600")
</script>
