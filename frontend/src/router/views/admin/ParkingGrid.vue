<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import api from '../../../services/api'
import {
  Trash2,
  Info,
  CheckCircle2,
  AlertTriangle
} from '@lucide/vue'

interface VehicleType {
  vehicle_id: number
  vehicle_type: string
}

interface FloorConfig {
  floor_number: number
  total_slots: number
  accessible_slots: number
  vehicle_distribution: Record<string, number>
}

const vehicleTypes = ref<VehicleType[]>([])
const gridExists = ref(false)
const existingSlotsCount = ref(0)
const loading = ref(true)
const actionLoading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

// Form states
const numOfFloors = ref(1)
const floorsConfig = ref<FloorConfig[]>([])

async function checkGridStatus() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await api.get('/api/v1/admin/parking-grid')
    if (res.data && res.data.length > 0) {
      gridExists.value = true
      existingSlotsCount.value = res.data.length
    } else {
      gridExists.value = false
      existingSlotsCount.value = 0
    }
  } catch (err: any) {
    if (err.response?.status === 404) {
      gridExists.value = false
      existingSlotsCount.value = 0
    } else {
      errorMsg.value = 'Failed to check grid configuration.'
    }
  } finally {
    loading.value = false
  }
}

async function fetchVehicleTypes() {
  try {
    const res = await api.get('/api/v1/admin/vehicle-types')
    vehicleTypes.value = res.data
    initializeFloorsConfig()
  } catch (err) {
    console.error('Failed to load types:', err)
  }
}

function initializeFloorsConfig() {
  floorsConfig.value = Array.from({ length: numOfFloors.value }, (_, i) => {
    // Keep existing config if available
    const existing = floorsConfig.value[i]
    if (existing) return existing

    const dist: Record<string, number> = {}
    vehicleTypes.value.forEach(t => {
      dist[t.vehicle_type] = 0
    })

    return {
      floor_number: i + 1,
      total_slots: 10,
      accessible_slots: 2,
      vehicle_distribution: dist
    }
  })
}

// Watch floors count to update configuration list
watch(numOfFloors, () => {
  if (numOfFloors.value < 1) numOfFloors.value = 1
  initializeFloorsConfig()
})

onMounted(async () => {
  await fetchVehicleTypes()
  await checkGridStatus()
})

// Calculate total allocated slots for a floor
function getAllocatedSum(floor: FloorConfig) {
  const vehicleSum = Object.values(floor.vehicle_distribution).reduce((sum, val) => sum + (Number(val) || 0), 0)
  return floor.accessible_slots + vehicleSum
}

// Check if a floor config is valid (allocated slots == total slots)
function isFloorValid(floor: FloorConfig) {
  return getAllocatedSum(floor) === floor.total_slots
}

const isFormValid = computed(() => {
  if (floorsConfig.value.length === 0) return false
  return floorsConfig.value.every(isFloorValid)
})

async function handleClearGrid() {
  if (!confirm('Are you sure you want to CLEAR the entire parking grid? All slots will be deleted and active occupancy records will be lost!')) {
    return
  }

  actionLoading.value = true
  errorMsg.value = ''
  try {
    await api.delete('/api/v1/admin/parking-grid/clear')
    gridExists.value = false
    existingSlotsCount.value = 0
    successMsg.value = 'Parking grid cleared successfully.'
    initializeFloorsConfig()
  } catch (err: any) {
    console.error(err)
    errorMsg.value = err.response?.data?.detail || 'Failed to clear parking grid.'
  } finally {
    actionLoading.value = false
  }
}

async function handleSetupGrid() {
  if (!isFormValid.value) {
    errorMsg.value = 'Please make sure all floor slot allocations match their total capacity.'
    return
  }

  actionLoading.value = true
  errorMsg.value = ''
  successMsg.value = ''

  const payload = {
    num_of_floors: numOfFloors.value,
    floors_config: floorsConfig.value.map(f => ({
      floor_number: f.floor_number,
      total_slots: f.total_slots,
      accessible_slots: f.accessible_slots,
      vehicle_distribution: Object.fromEntries(
        Object.entries(f.vehicle_distribution).map(([k, v]) => [k, Number(v)])
      )
    }))
  }

  try {
    await api.post('/api/v1/admin/parking-grid', payload)
    successMsg.value = 'Parking grid initialized successfully!'
    await checkGridStatus()
  } catch (err: any) {
    console.error(err)
    errorMsg.value = err.response?.data?.detail || 'Failed to initialize parking grid.'
  } finally {
    actionLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">Parking Grid Setup</h1>
      <p class="text-slate-500 dark:text-slate-400 mt-1">Configure layout, floors, accessible bays, and slot capacities</p>
    </div>

    <!-- Loading Screen -->
    <div v-if="loading" class="flex flex-col items-center justify-center min-h-[300px] gap-3">
      <div class="h-8 w-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
      <span class="text-sm font-semibold text-slate-400">Verifying grid status...</span>
    </div>

    <div v-else class="space-y-8">
      <!-- Error & Success Alerts -->
      <div v-if="errorMsg" class="p-4 border border-rose-200 bg-rose-50/50 text-rose-600 dark:border-rose-950/50 dark:bg-rose-950/20 dark:text-rose-400 rounded-2xl text-sm">
        {{ errorMsg }}
      </div>
      <div v-if="successMsg" class="p-4 border border-emerald-200 bg-emerald-50/50 text-emerald-600 dark:border-emerald-950/50 dark:bg-emerald-950/20 dark:text-emerald-400 rounded-2xl text-sm">
        {{ successMsg }}
      </div>

      <!-- State: Grid Already Configured -->
      <div
        v-if="gridExists"
        class="border border-slate-200/80 bg-white rounded-3xl p-8 shadow-sm dark:border-slate-800/80 dark:bg-slate-900 flex flex-col md:flex-row items-center justify-between gap-6"
      >
        <div class="flex items-start gap-4">
          <div class="p-4 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 rounded-2xl">
            <CheckCircle2 class="w-8 h-8" />
          </div>
          <div>
            <h3 class="font-extrabold text-lg text-slate-900 dark:text-white">Parking Grid is Configured</h3>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Active configuration contains <strong class="text-slate-800 dark:text-slate-200">{{ existingSlotsCount }}</strong> total parking slots.
            </p>
            <p class="text-xs text-amber-600 dark:text-amber-400 mt-2 font-medium flex items-center gap-1.5">
              <AlertTriangle class="w-3.5 h-3.5" />
              To change layout, you must clear the current layout first.
            </p>
          </div>
        </div>

        <button
          @click="handleClearGrid"
          :disabled="actionLoading"
          class="w-full md:w-auto inline-flex items-center justify-center gap-2 py-3.5 px-6 rounded-2xl border border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100 hover:text-rose-700 dark:border-rose-950/50 dark:bg-rose-950/20 dark:text-rose-400 dark:hover:bg-rose-950/40 font-semibold text-sm transition-all cursor-pointer disabled:opacity-50"
        >
          <Trash2 class="w-4 h-4" />
          Clear Parking Grid
        </button>
      </div>

      <!-- State: Grid Config Builder -->
      <div v-else class="space-y-6">
        <!-- Floor Count Configurator Card -->
        <div class="border border-slate-200/80 bg-white rounded-3xl p-6 shadow-sm dark:border-slate-800/80 dark:bg-slate-900">
          <h3 class="font-extrabold text-base text-slate-950 dark:text-white mb-4">Initial Configuration</h3>
          
          <div class="flex items-end gap-4 max-w-sm">
            <div class="space-y-1 flex-1">
              <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Number of Floors</label>
              <input
                type="number"
                min="1"
                max="10"
                v-model.number="numOfFloors"
                class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-800 dark:bg-slate-950 dark:text-white outline-none text-sm transition-all"
              />
            </div>
          </div>
        </div>

        <!-- Warning: Set up vehicle types first -->
        <div
          v-if="vehicleTypes.length === 0"
          class="p-6 border border-amber-200/50 bg-amber-50/50 text-amber-800 dark:border-amber-950/50 dark:bg-amber-950/20 dark:text-amber-300 rounded-3xl flex items-start gap-4"
        >
          <Info class="w-6 h-6 shrink-0 mt-0.5 text-amber-600" />
          <div>
            <h4 class="font-bold">No Vehicle Types Found</h4>
            <p class="text-sm mt-1 text-amber-700 dark:text-amber-400">
              You must register vehicle types (e.g. cars, bikes) before configuring floor structures.
            </p>
            <router-link
              to="/admin/vehicle-types"
              class="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-amber-600 text-white font-semibold text-sm rounded-xl hover:bg-amber-500 transition-colors"
            >
              Add Vehicle Types
            </router-link>
          </div>
        </div>

        <!-- Floors Configuration List -->
        <div v-else class="space-y-6">
          <div
            v-for="floor in floorsConfig"
            :key="floor.floor_number"
            class="border border-slate-200/80 bg-white rounded-3xl p-6 shadow-sm dark:border-slate-800/80 dark:bg-slate-900 space-y-6"
          >
            <!-- Floor title bar -->
            <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
              <h4 class="font-extrabold text-base text-slate-900 dark:text-white">Floor {{ floor.floor_number }} Setup</h4>
              
              <!-- Checkmark badge if valid -->
              <span
                :class="[
                  isFloorValid(floor)
                    ? 'bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900'
                    : 'bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-950/20 dark:text-rose-400 dark:border-rose-900',
                  'border text-xs px-3 py-1 rounded-full font-bold transition-all duration-300'
                ]"
              >
                Allocated: {{ getAllocatedSum(floor) }} / {{ floor.total_slots }}
              </span>
            </div>

            <!-- Floor capacities inputs -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div class="space-y-1">
                <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Floor Slots</label>
                <input
                  type="number"
                  min="1"
                  v-model.number="floor.total_slots"
                  class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-800 dark:bg-slate-950 dark:text-white outline-none text-sm transition-all"
                />
              </div>

              <div class="space-y-1">
                <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Accessible (Disabled) Slots</label>
                <input
                  type="number"
                  min="0"
                  v-model.number="floor.accessible_slots"
                  class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-800 dark:bg-slate-950 dark:text-white outline-none text-sm transition-all"
                />
              </div>
            </div>

            <!-- Vehicle type distribution grid -->
            <div class="space-y-3 pt-2">
              <h5 class="text-xs font-bold uppercase tracking-wider text-slate-500">Vehicle Type Slots Allocation</h5>
              <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                <div
                  v-for="type in vehicleTypes"
                  :key="type.vehicle_id"
                  class="space-y-1"
                >
                  <label class="text-xs font-semibold text-slate-400 capitalize">{{ type.vehicle_type }}</label>
                  <input
                    type="number"
                    min="0"
                    v-model.number="floor.vehicle_distribution[type.vehicle_type]"
                    class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-800 dark:bg-slate-950 dark:text-white outline-none text-sm transition-all"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Submit setup -->
          <div class="flex justify-end gap-4 mt-8">
            <button
              @click="handleSetupGrid"
              :disabled="actionLoading || !isFormValid"
              class="w-full sm:w-auto inline-flex items-center justify-center gap-2 py-4 px-8 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 active:from-violet-700 active:to-indigo-700 text-white font-semibold text-sm shadow-lg shadow-violet-500/20 hover:shadow-xl transition-all duration-300 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg v-if="actionLoading" class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Initialize Grid Layout</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
