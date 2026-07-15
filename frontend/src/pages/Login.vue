<template>
	<div
		class="flex min-h-screen flex-col justify-center bg-gradient-to-b from-navy-700 to-navy-900 px-6 py-10"
	>
		<div class="mx-auto w-full max-w-sm">
			<!-- Brand -->
			<div class="mb-10 text-center">
				<div class="mx-auto mb-4 rounded-2xl bg-white px-5 py-4 shadow-lg">
					<img :src="logoUrl" alt="TRIAM A+ — New-Age Rebars" class="mx-auto w-full max-w-[230px]" />
				</div>
				<p class="mt-1 text-sm font-medium text-navy-200">{{ $t("Field Sales") }}</p>
			</div>

			<!-- Form -->
			<div class="rounded-2xl bg-white p-6 shadow-xl">
				<h2 class="mb-1 text-lg font-semibold text-navy-700">{{ $t("Sign in") }}</h2>
				<p class="mb-5 text-sm text-gray-400">{{ $t("Use your company login") }}</p>

				<form @submit.prevent="onSubmit" class="space-y-4">
					<div>
						<label class="mb-1 block text-sm font-medium text-navy-600">{{ $t("Email / Username") }}</label>
						<input
							v-model="email"
							type="text"
							autocomplete="username"
							class="aa-input"
							placeholder="you@amitalliance.com"
							required
						/>
					</div>
					<div>
						<label class="mb-1 block text-sm font-medium text-navy-600">{{ $t("Password") }}</label>
						<input
							v-model="password"
							type="password"
							autocomplete="current-password"
							class="aa-input"
							placeholder="••••••••"
							required
						/>
					</div>

					<p v-if="error" class="text-sm font-medium text-red-600">{{ error }}</p>

					<button type="submit" class="aa-btn-primary" :disabled="loading">
						<span v-if="loading">Signing in…</span>
						<span v-else>{{ $t("Sign in") }}</span>
					</button>
				</form>
			</div>

			<p class="mt-6 text-center text-xs text-navy-300">Amit Metaliks Limited · TRIAM A+</p>
		</div>
	</div>
</template>

<script setup>
import { ref } from "vue"
import { loginResource } from "../data/session"
import logoUrl from "../assets/triam-logo.jpg"

const email = ref("")
const password = ref("")
const error = ref("")
const loading = ref(false)

async function onSubmit() {
	error.value = ""
	loading.value = true
	try {
		await loginResource.submit({ email: email.value, password: password.value })
		// Full reload so the server injects this session's CSRF token (needed for POSTs)
		window.location.href = "/amit-crm/dashboard"
	} catch (e) {
		error.value = e?.messages?.[0] || e?.message || "Invalid login. Check your email and password."
	} finally {
		loading.value = false
	}
}
</script>
