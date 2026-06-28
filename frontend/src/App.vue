<script setup lang="ts">
import { onMounted } from 'vue'
import { useTheme } from './composables/useTheme'
import { isRouteLoading } from './router'

const { initTheme } = useTheme()

onMounted(() => {
  initTheme()
})
</script>

<template>
  <div class="relative min-h-screen">
    <!-- Premium Top Progress Loading Bar -->
    <transition name="fade">
      <div 
        v-if="isRouteLoading" 
        class="fixed top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-violet-600 via-indigo-600 to-violet-600 z-[9999] overflow-hidden"
      >
        <div class="h-full w-full bg-white/20 animate-infinite-loading"></div>
      </div>
    </transition>

    <router-view />
  </div>
</template>

<style>
@keyframes infinite-loading {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.animate-infinite-loading {
  animation: infinite-loading 1.5s infinite linear;
}

/* Fade animation for progress bar */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
