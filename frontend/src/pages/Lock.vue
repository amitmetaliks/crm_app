<template>
	<div class="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-navy-700 to-navy-900 px-6 text-white">
		<div class="aa-logo-pill mb-6 !rounded-2xl !px-5 !py-3 shadow-lg"><img :src="wordmark" alt="TRIAM A+" class="h-7" /></div>
		<p class="mb-1 text-lg font-semibold">{{ $t("App locked") }}</p>
		<p class="mb-6 text-sm text-navy-200">{{ $t("Enter your PIN to continue") }}</p>

		<div class="mb-5 flex gap-3">
			<span v-for="i in 4" :key="i" class="h-4 w-4 rounded-full" :class="entry.length >= i ? 'bg-saffron' : 'bg-white/25'"></span>
		</div>
		<p v-if="error" class="mb-3 text-sm font-medium text-red-300">{{ $t("Wrong PIN, try again") }}</p>

		<div class="grid w-full max-w-[260px] grid-cols-3 gap-3">
			<button v-for="n in 9" :key="n" @click="press(n)" class="rounded-full bg-white/10 py-4 text-xl font-semibold active:bg-white/20">{{ n }}</button>
			<button v-if="canBio" @click="useBio" class="rounded-full bg-white/10 py-4"><Fingerprint class="mx-auto h-6 w-6" /></button>
			<span v-else></span>
			<button @click="press(0)" class="rounded-full bg-white/10 py-4 text-xl font-semibold active:bg-white/20">0</button>
			<button @click="back" class="rounded-full bg-white/10 py-4"><Delete class="mx-auto h-6 w-6" /></button>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { useRouter } from "vue-router"
import { Fingerprint, Delete } from "lucide-vue-next"
import wordmark from "../assets/logo-wordmark.png"
import { verifyPin, unlock, bioEnabled, bioUnlock } from "../data/lock"

const router = useRouter()
const entry = ref("")
const error = ref(false)
const canBio = bioEnabled()

async function press(n) {
	error.value = false
	if (entry.value.length >= 4) return
	entry.value += String(n)
	if (entry.value.length === 4) {
		if (await verifyPin(entry.value)) {
			unlock()
			router.replace({ name: "Dashboard" })
		} else {
			error.value = true
			entry.value = ""
		}
	}
}
function back() {
	entry.value = entry.value.slice(0, -1)
}
async function useBio() {
	if (await bioUnlock()) router.replace({ name: "Dashboard" })
}
onMounted(() => {
	if (canBio) useBio()
})
</script>
