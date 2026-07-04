<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import api from '../../../services/api'
import {
  Activity,
  CheckCircle,
  RefreshCw,
  Info,
  Layers,
  Sparkles,
  Accessibility
} from '@lucide/vue'

interface Slot {
  slot_id: number
  display_slot: string
  is_accessible: boolean
  is_occupied: boolean
  vehicle_type_id: number
}

interface VehicleType {
  vehicle_id: number
  vehicle_type: string
}

const slots = ref<Slot[]>([])
const vehicleTypes = ref<VehicleType[]>([])
const loading = ref(true)
const errorMsg = ref('')
const autoRefresh = ref(true)
let refreshInterval: any = null

const totalSlots = computed(() => slots.value.length)
const occupiedSlots = computed(() => slots.value.filter(s => s.is_occupied).length)
const availableSlots = computed(() => totalSlots.value - occupiedSlots.value)
const accessibleSlots = computed(() => slots.value.filter(s => s.is_accessible).length)
const occupancyRate = computed(() => totalSlots.value ? Math.round((occupiedSlots.value / totalSlots.value) * 100) : 0)

// Group slots by floor
const floors = computed(() => {
  const grouped: Record<string, Slot[]> = {}
  slots.value.forEach(s => {
    const floorName = s.display_slot.split('-')[0] || 'Unknown'
    if (!grouped[floorName]) {
      grouped[floorName] = []
    }
    grouped[floorName].push(s)
  })

  return Object.keys(grouped)
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }))
    .map(name => ({
      name,
      slots: grouped[name].sort((a, b) => a.display_slot.localeCompare(b.display_slot, undefined, { numeric: true }))
    }))
})

// Vehicle type map
const vehicleTypeMap = computed(() => {
  const map: Record<number, string> = {}
  vehicleTypes.value.forEach(v => {
    map[v.vehicle_id] = v.vehicle_type
  })
  return map
})

async function fetchData() {
  errorMsg.value = ''
  try {
    const typesRes = await api.get('/api/v1/admin/vehicle-types')
    vehicleTypes.value = typesRes.data

    const slotsRes = await api.get('/api/v1/admin/parking-grid')
    slots.value = slotsRes.data
  } catch (err: any) {
    console.error(err)
    if (err.response?.status === 404) {
      slots.value = []
      errorMsg.value = 'No parking slots configured. Please head to Parking Grid Config page.'
    } else {
      errorMsg.value = 'Failed to load parking metrics.'
    }
  } finally {
    loading.value = false
  }
}

function startRefresh() {
  if (refreshInterval) clearInterval(refreshInterval)
  refreshInterval = setInterval(() => {
    if (autoRefresh.value) {
      fetchData()
    }
  }, 10000) // refresh every 10s
}

onMounted(() => {
  fetchData()
  startRefresh()
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

function getVehicleTypeName(id: number) {
  return vehicleTypeMap.value[id] || 'Unknown'
}

function getSlotColor(slot: Slot) {
  if (slot.is_occupied) {
    return 'bg-rose-500 text-white border-rose-600 shadow-rose-500/20'
  }
  if (slot.is_accessible) {
    return 'bg-sky-50 dark:bg-sky-950/20 text-sky-600 dark:text-sky-400 border-sky-300 dark:border-sky-800 shadow-sky-500/10'
  }
  return 'bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800 shadow-emerald-500/10'
}
</script>

<template>
  <div class="space-y-8">
    <!-- Top Action bar -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
          <span>Overview Analytics</span>
          <Sparkles class="w-6 h-6 text-violet-500 animate-pulse" />
        </h1>
        <p class="text-slate-500 dark:text-slate-400 mt-1">Real-time occupancy status and grid visualization</p>
      </div>

      <div class="flex items-center gap-3">
        <!-- Auto refresh check -->
        <label
          class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500 cursor-pointer select-none">
          <input type="checkbox" v-model="autoRefresh"
            class="rounded border-slate-300 text-violet-600 focus:ring-violet-500 dark:border-slate-800 dark:bg-slate-900" />
          Auto-refresh (10s)
        </label>

        <button @click="fetchData" :disabled="loading"
          class="p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 transition-all cursor-pointer flex items-center gap-2 text-sm font-semibold">
          <RefreshCw :class="['w-4 h-4', loading ? 'animate-spin' : '']" />
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <!-- Error Alert when no slots -->
    <div v-if="errorMsg && slots.length === 0"
      class="flex items-start gap-4 p-6 rounded-3xl border border-amber-200/50 bg-amber-50/50 text-amber-800 dark:border-amber-950/50 dark:bg-amber-950/20 dark:text-amber-300">
      <Info class="w-6 h-6 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
      <div>
        <h3 class="font-bold text-base">Setup Required</h3>
        <p class="mt-1 text-sm text-amber-700/90 dark:text-amber-400/80">
          {{ errorMsg }}
        </p>
        <router-link to="/admin/parking-grid"
          class="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-amber-600 text-white rounded-xl text-sm font-semibold hover:bg-amber-500 transition-colors shadow-md shadow-amber-500/10">
          Configure Parking Grid
        </router-link>
      </div>
    </div>

    <!-- Statistics Panel -->
    <div v-else-if="!loading || slots.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Total Spots Card -->
      <div
        class="relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 shadow-sm transition-all hover:shadow-md">
        <div class="flex justify-between items-start">
          <div>
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Total
              capacity</span>
            <span class="block text-4xl font-extrabold mt-2 text-slate-900 dark:text-white">{{ totalSlots }}</span>
          </div>
          <div class="p-3 bg-violet-50 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400 rounded-2xl">
            <Layers class="w-6 h-6" />
          </div>
        </div>
        <div class="mt-4 text-xs font-medium text-slate-400">
          Global parking layout size
        </div>
      </div>

      <!-- Occupied Spots Card -->
      <div
        class="relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 shadow-sm transition-all hover:shadow-md">
        <div class="flex justify-between items-start">
          <div>
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Occupied
              spots</span>
            <span class="block text-4xl font-extrabold mt-2 text-slate-900 dark:text-white">{{ occupiedSlots }}</span>
          </div>
          <div class="p-3 bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 rounded-2xl">
            <Activity class="w-6 h-6" />
          </div>
        </div>
        <!-- Progress bar -->
        <div class="mt-4">
          <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
            <div class="bg-gradient-to-r from-rose-500 to-rose-600 h-full rounded-full transition-all duration-500"
              :style="{ width: `${occupancyRate}%` }"></div>
          </div>
          <div class="flex justify-between mt-2 text-xs font-semibold text-slate-400">
            <span>{{ occupancyRate }}% Occupancy</span>
            <span class="text-rose-500 dark:text-rose-400">In use</span>
          </div>
        </div>
      </div>

      <!-- Available Spots Card -->
      <div
        class="relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 shadow-sm transition-all hover:shadow-md">
        <div class="flex justify-between items-start">
          <div>
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Available
              spots</span>
            <span class="block text-4xl font-extrabold mt-2 text-slate-900 dark:text-white">{{ availableSlots }}</span>
          </div>
          <div class="p-3 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 rounded-2xl">
            <CheckCircle class="w-6 h-6" />
          </div>
        </div>
        <!-- Progress bar -->
        <div class="mt-4">
          <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              class="bg-gradient-to-r from-emerald-500 to-emerald-600 h-full rounded-full transition-all duration-500"
              :style="{ width: `${100 - occupancyRate}%` }"></div>
          </div>
          <div class="flex justify-between mt-2 text-xs font-semibold text-slate-400">
            <span>{{ 100 - occupancyRate }}% Available</span>
            <span class="text-emerald-500 dark:text-emerald-400">Vacant</span>
          </div>
        </div>
      </div>

      <!-- Accessible Spots Card -->
      <div
        class="relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 shadow-sm transition-all hover:shadow-md">
        <div class="flex justify-between items-start">
          <div>
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Accessible
              spots</span>
            <span class="block text-4xl font-extrabold mt-2 text-slate-900 dark:text-white">{{ accessibleSlots }}</span>
          </div>
          <div class="p-3 bg-sky-50 dark:bg-sky-950/40 text-sky-600 dark:text-sky-400 rounded-2xl">
            <Accessibility class="w-6 h-6" />
          </div>
        </div>
        <div class="mt-4 text-xs font-medium text-slate-400 flex items-center gap-1.5">
          <Accessibility class="w-3.5 h-3.5 text-sky-500" />
          Reserved for disabled drivers
        </div>
      </div>
    </div>

    <!-- Live Grid Map Visualization -->
    <div v-if="slots.length > 0" class="space-y-8">
      <div v-for="floor in floors" :key="floor.name"
        class="border border-slate-200/80 bg-white dark:border-slate-800/80 dark:bg-slate-900 rounded-3xl p-6 shadow-sm">
        <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4 mb-6">
          <div class="flex items-center gap-2.5">
            <div
              class="h-8 w-8 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 flex items-center justify-center font-bold text-sm">
              {{ floor.name }}
            </div>
            <div>
              <h3 class="font-extrabold text-base text-slate-950 dark:text-white">Floor {{ floor.name.replace('F', '')
                }}</h3>
              <p class="text-xs text-slate-400 mt-0.5">
                Occupied: {{floor.slots.filter(s => s.is_occupied).length}} / {{ floor.slots.length }}
              </p>
            </div>
          </div>
          <!-- Legend indicators -->
          <div class="flex items-center gap-4 text-xs text-slate-400 font-semibold">
            <div class="flex items-center gap-1.5">
              <span class="w-3 h-3 rounded bg-emerald-500 shadow shadow-emerald-500/20"></span>
              <span>Available</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="w-3 h-3 rounded bg-rose-500 shadow shadow-rose-500/20"></span>
              <span>Occupied</span>
            </div>
          </div>
        </div>

        <!-- Spots Layout Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 gap-4">
          <div v-for="slot in floor.slots" :key="slot.slot_id" :class="[
            getSlotColor(slot),
            'border rounded-2xl p-4 flex flex-col items-center justify-center min-h-[90px] relative transition-all duration-300 group hover:scale-[1.03] hover:shadow-md cursor-help border-dashed border-2'
          ]">
            <!-- Accessibility Icon top left -->
            <Accessibility v-if="slot.is_accessible"
              class="absolute top-2 left-2 w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />

           <span class="font-bold text-sm tracking-wide">{{ slot.display_slot }}</span>
            <span class="text-[10px] uppercase font-bold tracking-wider opacity-70 mt-1">
              {{ getVehicleTypeName(slot.vehicle_type_id) }}
            </span>

            <!-- Tooltip Info on hover -->
            <div
              class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 scale-0 pointer-events-none group-hover:scale-100 transition-all duration-200 origin-bottom bg-slate-900 text-white text-xs p-3 rounded-xl shadow-xl z-50 leading-relaxed border border-slate-800">
              <div>Type: {{ getVehicleTypeName(slot.vehicle_type_id) }}</div>
              <div>Status: <div class="font-extrabold mb-1">Spot: {{ slot.display_slot }}</div></div>
              <div v-if="slot.is_accessible" class="text-sky-300 font-medium">♿ Accessible Spot</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Spinner Loader -->
    <div v-if="loading && slots.length === 0" class="flex flex-col items-center justify-center min-h-[300px] gap-3">
      <div class="h-10 w-10 border-4 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
      <span class="text-sm font-semibold text-slate-400">Syncing database data...</span>
    </div>
  </div>
</template>
