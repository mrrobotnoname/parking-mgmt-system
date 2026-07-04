<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useTheme } from '../../composables/useTheme'
import { Sun, Moon, Lock, User, Eye, EyeOff, Car, ShieldAlert } from '@lucide/vue'

const router = useRouter()
const authStore = useAuthStore()
const { isDark, toggleTheme } = useTheme()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const showPassword = ref(false)

async function handleLogin() {
  if (!username.value || !password.value) {
    error.value = 'Please enter username and password.'
    return
  }

  error.value = ''
  loading.value = true

  try {
    const user = await authStore.login(username.value, password.value)
    if (user.role === 'admin') {
      router.push('/admin/dashboard')
    } else if (user.role === 'guard') {
      router.push('/guard')
    } else {
      error.value = 'Unauthorized role.'
    }
  } catch (err: any) {
    console.error(err)
    if (err.response?.status === 401) {
      error.value = 'Invalid username or password.'
    } else {
      error.value = 'Connection error. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="relative min-h-screen flex items-center justify-center overflow-hidden transition-colors duration-500 bg-slate-50 dark:bg-slate-950">
    <!-- Abstract background glow elements -->
    <div class="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-violet-600/20 blur-3xl dark:bg-violet-900/30"></div>
    <div class="absolute -bottom-40 -right-40 w-96 h-96 rounded-full bg-indigo-600/20 blur-3xl dark:bg-indigo-900/30"></div>

    <!-- Theme Toggler -->
    <button
      @click="toggleTheme"
      class="absolute top-6 right-6 p-3 rounded-xl border border-slate-200 bg-white/70 backdrop-blur-md text-slate-700 hover:bg-slate-100 hover:text-slate-900 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white transition-all duration-300 shadow-sm"
      aria-label="Toggle theme"
    >
      <component :is="isDark ? Sun : Moon" class="w-5 h-5 animate-pulse" />
    </button>

    <!-- Login Card Wrapper -->
    <div class="w-full max-w-md p-2">
      <div class="relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white/80 p-8 shadow-2xl backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-900/80 transition-all duration-300">
        <!-- Accent line -->
        <div class="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-violet-600 to-indigo-600"></div>

        <!-- Header -->
        <div class="flex flex-col items-center mb-8">
          <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/20 mb-4 animate-bounce">
            <Car class="w-9 h-9" />
          </div>
          <h1 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Easy Parking
          </h1>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Sign in to manage parking space
          </p>
        </div>

        <!-- Error Alert -->
        <div
          v-if="error"
          class="flex items-center gap-3 p-4 mb-6 rounded-2xl border border-rose-200/50 bg-rose-50/50 text-rose-600 dark:border-rose-950/50 dark:bg-rose-950/20 dark:text-rose-400 text-sm animate-shake"
        >
          <ShieldAlert class="w-5 h-5 shrink-0" />
          <span>{{ error }}</span>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleLogin" class="space-y-5">
          <!-- Username -->
          <div class="space-y-2">
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Username
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 flex items-center pl-4 text-slate-400 dark:text-slate-500">
                <User class="w-5 h-5" />
              </span>
              <input
                type="text"
                v-model="username"
                required
                placeholder="Enter your username"
                class="w-full pl-11 pr-4 py-3.5 rounded-2xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white focus:ring-4 focus:ring-violet-500/10 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white dark:placeholder-slate-600 dark:focus:border-violet-400 dark:focus:bg-slate-950 dark:focus:ring-violet-400/10 outline-none transition-all duration-300"
              />
            </div>
          </div>

          <!-- Password -->
          <div class="space-y-2">
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Password
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 flex items-center pl-4 text-slate-400 dark:text-slate-500">
                <Lock class="w-5 h-5" />
              </span>
              <input
                :type="showPassword ? 'text' : 'password'"
                v-model="password"
                required
                placeholder="••••••••"
                class="w-full pl-11 pr-12 py-3.5 rounded-2xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white focus:ring-4 focus:ring-violet-500/10 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white dark:placeholder-slate-600 dark:focus:border-violet-400 dark:focus:bg-slate-950 dark:focus:ring-violet-400/10 outline-none transition-all duration-300"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute inset-y-0 right-0 flex items-center pr-4 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
              >
                <component :is="showPassword ? EyeOff : Eye" class="w-5 h-5" />
              </button>
            </div>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            :disabled="loading"
            class="relative w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-semibold text-sm hover:from-violet-500 hover:to-indigo-500 active:from-violet-700 active:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-violet-500/25 hover:shadow-xl hover:shadow-violet-500/30 transition-all duration-300 cursor-pointer overflow-hidden group"
          >
            <!-- Background shiny hover effect -->
            <div class="absolute inset-0 w-1/2 h-full bg-white/10 skew-x-[-20deg] -translate-x-full group-hover:animate-shine"></div>
            
            <span v-if="loading" class="flex items-center justify-center gap-2">
              <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Authenticating...
            </span>
            <span v-else>Sign In</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

.animate-shake {
  animation: shake 0.3s ease-in-out;
}

@keyframes shine {
  100% {
    transform: translateX(300%);
  }
}

.group-hover\:animate-shine {
  animation: shine 1.2s infinite ease-in-out;
}
</style>
