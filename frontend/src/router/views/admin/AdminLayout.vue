<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../../stores/auth'
import { useTheme } from '../../../composables/useTheme'
import {
  LayoutDashboard,
  Users,
  Grid3X3,
  Car,
  LogOut,
  Sun,
  Moon,
  Menu,
  X,
  UserCheck
} from '@lucide/vue'

const route = useRoute()
const authStore = useAuthStore()
const { isDark, toggleTheme } = useTheme()

const sidebarOpen = ref(false)

const navItems = [
  {
    name: 'Dashboard',
    path: '/admin/dashboard',
    icon: LayoutDashboard
  },
  {
    name: 'Guard Management',
    path: '/admin/guards',
    icon: Users
  },
  {
    name: 'Parking Grid Config',
    path: '/admin/parking-grid',
    icon: Grid3X3
  },
  {
    name: 'Vehicle Types',
    path: '/admin/vehicle-types',
    icon: Car
  }
]

function handleLogout() {
  authStore.logout()
}

function closeSidebar() {
  sidebarOpen.value = false
}
</script>

<template>
  <div class="min-h-screen flex bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
    <!-- Mobile Sidebar Backdrop -->
    <div
      v-if="sidebarOpen"
      @click="closeSidebar"
      class="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm lg:hidden"
    ></div>

    <!-- Sidebar -->
    <aside
      :class="[
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        'fixed inset-y-0 left-0 z-50 w-72 border-r border-slate-200/80 bg-white/90 backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-900/90 transition-all duration-300 ease-in-out lg:static lg:translate-x-0 flex flex-col'
      ]"
    >
      <!-- Brand Logo -->
      <div class="h-20 flex items-center gap-3 px-6 border-b border-slate-200/50 dark:border-slate-800/50">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-500/25">
          <Car class="w-6 h-6" />
        </div>
        <div>
          <span class="font-bold text-lg bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">Easy Parking</span>
          <span class="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Admin Panel</span>
        </div>
      </div>

      <!-- Navigation Links -->
      <nav class="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          @click="closeSidebar"
          custom
          v-slot="{ href, navigate, isActive }"
        >
          <a
            :href="href"
            @click="navigate"
            :class="[
              isActive
                ? 'bg-gradient-to-r from-violet-600/10 to-indigo-600/10 text-violet-600 dark:text-violet-400 font-semibold border-l-4 border-violet-600 dark:border-violet-500 pl-3.5'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white border-l-4 border-transparent pl-4',
              'flex items-center gap-3.5 py-3.5 px-4 rounded-xl transition-all duration-200 group text-sm'
            ]"
          >
            <component
              :is="item.icon"
              :class="[
                isActive ? 'text-violet-600 dark:text-violet-400' : 'text-slate-400 dark:text-slate-500 group-hover:text-slate-600 dark:group-hover:text-slate-300',
                'w-5 h-5 transition-colors duration-200'
              ]"
            />
            <span>{{ item.name }}</span>
          </a>
        </router-link>
      </nav>

      <!-- User Profile Card -->
      <div class="p-4 border-t border-slate-200/50 dark:border-slate-800/50 bg-slate-50/50 dark:bg-slate-900/30">
        <div class="flex items-center gap-3 p-2.5 rounded-2xl bg-white dark:bg-slate-950 border border-slate-200/50 dark:border-slate-800/50">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-100 dark:bg-violet-950/50 text-violet-600 dark:text-violet-400">
            <UserCheck class="w-5 h-5" />
          </div>
          <div class="flex-1 min-w-0">
            <span class="block font-semibold text-sm truncate text-slate-800 dark:text-slate-200">
              {{ authStore.user?.sub || 'Administrator' }}
            </span>
            <span class="block text-xs text-slate-400 capitalize truncate">
              {{ authStore.user?.role }}
            </span>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Content Layout -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Header -->
      <header class="h-20 shrink-0 flex items-center justify-between px-6 border-b border-slate-200/80 bg-white/70 backdrop-blur-md dark:border-slate-800/80 dark:bg-slate-900/70 z-30 transition-all duration-300">
        <!-- Toggle Button for Mobile -->
        <button
          @click="sidebarOpen = !sidebarOpen"
          class="p-2.5 rounded-xl border border-slate-200/80 text-slate-600 bg-white hover:bg-slate-100 lg:hidden dark:border-slate-800/80 dark:text-slate-400 dark:bg-slate-900 dark:hover:bg-slate-800 transition-colors"
          aria-label="Toggle menu"
        >
          <component :is="sidebarOpen ? X : Menu" class="w-5 h-5" />
        </button>

        <!-- Page Title -->
        <h2 class="text-xl font-bold tracking-tight text-slate-900 dark:text-white hidden sm:block">
          {{ route.name ? String(route.name).replace(/([A-Z])/g, ' $1').trim() : 'Admin Panel' }}
        </h2>

        <!-- Action Tools -->
        <div class="flex items-center gap-3 ml-auto lg:ml-0">
          <!-- Theme Toggle -->
          <button
            @click="toggleTheme"
            class="p-2.5 rounded-xl border border-slate-200/80 bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:border-slate-800/80 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white transition-all duration-300"
            aria-label="Toggle theme"
          >
            <component :is="isDark ? Sun : Moon" class="w-5 h-5" />
          </button>

          <!-- Logout Button -->
          <button
            @click="handleLogout"
            class="flex items-center gap-2 py-2.5 px-4 rounded-xl text-slate-600 bg-white border border-slate-200/80 hover:bg-rose-50 hover:border-rose-200/50 hover:text-rose-600 dark:bg-slate-900 dark:border-slate-800/80 dark:text-slate-400 dark:hover:bg-rose-950/20 dark:hover:border-rose-950/50 dark:hover:text-rose-400 font-medium text-sm transition-all duration-300 cursor-pointer"
          >
            <LogOut class="w-4 h-4" />
            <span class="hidden md:inline">Sign Out</span>
          </button>
        </div>
      </header>

      <!-- Main Work Panel -->
      <main class="flex-1 overflow-y-auto p-6 md:p-8">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style>
/* Page transition animation */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
