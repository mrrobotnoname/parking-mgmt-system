<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import api from '../../../services/api'
import { Car, Trash2, Plus, Info, Sparkles, DollarSign } from '@lucide/vue'

interface VehicleType {
  vehicle_id: number
  vehicle_type: string
}

const vehicleTypes = ref<VehicleType[]>([])
const loading = ref(true)
const submitLoading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const selectedVehicleTypeId = ref<number | null>(null)
const pricingLoading = ref(false)
const pricingError = ref('')
const pricingSuccess = ref('')
const hourlyRate = ref(0)
const fixedRate = ref(0)
const thresholdMinutes = ref(1)

const selectedVehicleType = computed(() => {
  return vehicleTypes.value.find((type) => type.vehicle_id === selectedVehicleTypeId.value) || null
})

// Form fields
const newTypeName = ref('')
const formError = ref('')

async function fetchVehicleTypes() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await api.get('/api/v1/admin/vehicle-types')
    vehicleTypes.value = res.data
  } catch (err: any) {
    console.error(err)
    errorMsg.value = 'Failed to load vehicle types.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchVehicleTypes()
})

async function handleAddVehicleType() {
  const typeName = newTypeName.value.trim().toLowerCase()
  if (!typeName) {
    formError.value = 'Vehicle type name is required.'
    return
  }

  // Basic check for duplicates locally
  if (vehicleTypes.value.some(vt => vt.vehicle_type.toLowerCase() === typeName)) {
    formError.value = 'This vehicle type is already registered.'
    return
  }

  formError.value = ''
  submitLoading.value = true
  successMsg.value = ''

  try {
    const payload = {
      vehicle_type: typeName
    }
    await api.post('/api/v1/admin/vehicle-types', payload)
    newTypeName.value = ''
    successMsg.value = `Vehicle type "${typeName}" successfully added.`
    await fetchVehicleTypes()
    
    // Clear success message after 3 seconds
    setTimeout(() => {
      successMsg.value = ''
    }, 3000)
  } catch (err: any) {
    console.error(err)
    if (err.response?.data?.detail) {
      formError.value = err.response.data.detail
    } else {
      formError.value = 'Failed to add vehicle type.'
    }
  } finally {
    submitLoading.value = false
  }
}

async function fetchPricingForType(vehicleId: number) {
  pricingError.value = ''
  pricingSuccess.value = ''
  pricingLoading.value = true

  try {
    const res = await api.get(`/api/v1/admin/pricing/${vehicleId}`)
    hourlyRate.value = res.data.hourly_rate
    fixedRate.value = res.data.fixed_rate
    thresholdMinutes.value = res.data.threshold_minutes
  } catch (err: any) {
    if (err.response?.status === 404) {
      hourlyRate.value = 0
      fixedRate.value = 0
      thresholdMinutes.value = 1
    } else {
      pricingError.value = 'Failed to load pricing details.'
    }
  } finally {
    pricingLoading.value = false
  }
}

watch(selectedVehicleTypeId, async (id) => {
  if (id !== null) {
    await fetchPricingForType(id)
  }
})

async function handleSavePricing() {
  if (!selectedVehicleType.value) {
    pricingError.value = 'Please select a vehicle type first.'
    return
  }

  if (thresholdMinutes.value <= 0) {
    pricingError.value = 'Threshold minutes must be greater than zero.'
    return
  }

  pricingLoading.value = true
  pricingError.value = ''
  pricingSuccess.value = ''

  try {
    const payload = {
      hourly_rate: Number(hourlyRate.value),
      fixed_rate: Number(fixedRate.value),
      threshold_minutes: Number(thresholdMinutes.value)
    }
    await api.put(`/api/v1/admin/pricing/${selectedVehicleType.value.vehicle_id}`, payload)
    pricingSuccess.value = `Pricing for ${selectedVehicleType.value.vehicle_type} saved successfully.`
  } catch (err: any) {
    console.error(err)
    pricingError.value = err.response?.data?.detail || 'Failed to save pricing.'
  } finally {
    pricingLoading.value = false
  }
}

async function handleDelete(typeId: number, typeName: string) {
  if (!confirm(`Are you sure you want to delete vehicle type "${typeName}"? This might impact existing slots configured with this type.`)) {
    return
  }

  try {
    await api.delete(`/api/v1/admin/vehicle-types/${typeId}`)
    await fetchVehicleTypes()
  } catch (err: any) {
    console.error(err)
    alert(err.response?.data?.detail || 'Failed to delete vehicle type. Check if it is being used by slots.')
  }
}
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
        <span>Vehicle Types</span>
        <Sparkles class="w-6 h-6 text-violet-500 animate-pulse" />
      </h1>
      <p class="text-slate-500 dark:text-slate-400 mt-1">Configure vehicle classification for spot distribution (e.g. cars, bikes, electric, truck)</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
      <!-- Left: Create Form -->
      <div class="border border-slate-200/80 bg-white rounded-3xl p-6 shadow-sm dark:border-slate-800/80 dark:bg-slate-900 lg:col-span-1">
        <h3 class="font-extrabold text-base text-slate-950 dark:text-white mb-4">Add New Type</h3>
        
        <form @submit.prevent="handleAddVehicleType" class="space-y-4">
          <div class="space-y-1">
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Type Name</label>
            <input
              type="text"
              v-model="newTypeName"
              placeholder="e.g. cars, bikes, trucks, ev"
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-800 dark:bg-slate-950 dark:text-white outline-none text-sm transition-all"
              required
            />
          </div>

          <div v-if="formError" class="p-3 border border-rose-200/50 bg-rose-50/50 text-rose-600 rounded-xl text-xs">
            {{ formError }}
          </div>

          <div v-if="successMsg" class="p-3 border border-emerald-200/50 bg-emerald-50/50 text-emerald-600 rounded-xl text-xs">
            {{ successMsg }}
          </div>

          <button
            type="submit"
            :disabled="submitLoading"
            class="w-full py-3 px-4 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-xl text-sm font-semibold shadow-md shadow-violet-500/10 cursor-pointer flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            <Plus class="w-4 h-4" />
            <span>Add Vehicle Type</span>
          </button>
        </form>

        <div class="mt-6 p-4 bg-slate-50 dark:bg-slate-950/40 rounded-2xl border border-slate-100 dark:border-slate-800/80 text-xs text-slate-500 dark:text-slate-400 leading-relaxed flex items-start gap-2.5">
          <Info class="w-4 h-4 shrink-0 text-violet-500 mt-0.5" />
          <span>These classification types will map directly to layout slot setups. Be careful when editing/removing active classes.</span>
        </div>
      </div>

      <!-- Right: Registered Types List -->
      <div class="lg:col-span-1 space-y-4">
        <div class="border border-slate-200/80 bg-white rounded-3xl p-6 shadow-sm dark:border-slate-800/80 dark:bg-slate-900">
          <h3 class="font-extrabold text-base text-slate-950 dark:text-white mb-6">Registered Vehicle Types</h3>

          <div v-if="loading" class="flex flex-col items-center justify-center min-h-[150px] gap-3">
            <div class="h-6 w-6 border-3 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
            <span class="text-xs font-semibold text-slate-400">Loading types...</span>
          </div>

          <div v-else-if="vehicleTypes.length === 0" class="flex flex-col items-center justify-center min-h-[150px] py-6 text-slate-400">
            <Car class="w-10 h-10 text-slate-350 dark:text-slate-800 mb-2" />
            <span class="text-sm font-semibold">No vehicle types registered.</span>
          </div>

          <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div
              v-for="type in vehicleTypes"
              :key="type.vehicle_id"
              class="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-950/40 border border-slate-100 dark:border-slate-800/50 rounded-2xl group hover:shadow-sm transition-shadow"
            >
              <div class="flex items-center gap-3">
                <div class="p-2.5 bg-violet-50 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400 rounded-xl">
                  <Car class="w-5 h-5" />
                </div>
                <div>
                  <span class="font-bold text-sm text-slate-800 dark:text-slate-200 capitalize">
                    {{ type.vehicle_type }}
                  </span>
                  <span class="block text-[10px] text-slate-400 font-semibold uppercase tracking-wider mt-0.5">
                    ID: {{ type.vehicle_id }}
                  </span>
                </div>
              </div>

              <button
                @click="handleDelete(type.vehicle_id, type.vehicle_type)"
                class="p-2 border border-slate-200 hover:bg-rose-50 hover:border-rose-200 hover:text-rose-600 dark:border-slate-800 dark:hover:bg-rose-950/20 dark:hover:border-rose-950 dark:hover:text-rose-400 text-slate-400 rounded-xl transition-all cursor-pointer opacity-0 group-hover:opacity-100 focus:opacity-100"
                title="Delete type"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Pricing Configuration -->
      <div class="lg:col-span-1 border border-slate-200/80 bg-white rounded-3xl p-6 shadow-sm dark:border-slate-800/80 dark:bg-slate-900">
        <div class="flex items-center justify-between gap-2 mb-5">
          <div>
            <h3 class="font-extrabold text-base text-slate-950 dark:text-white">Pricing Configuration</h3>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Set hourly and fixed pricing for a selected vehicle type</p>
          </div>
          <DollarSign class="w-6 h-6 text-violet-500" />
        </div>

        <div class="space-y-4">
          <div>
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Vehicle type</label>
            <select
              v-model.number="selectedVehicleTypeId"
              class="w-full mt-2 px-4 py-3 rounded-2xl border border-slate-200 bg-slate-50 text-slate-900 outline-none focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
            >
              <option value="" disabled>Select vehicle type</option>
              <option
                v-for="type in vehicleTypes"
                :key="type.vehicle_id"
                :value="type.vehicle_id"
              >
                {{ type.vehicle_type }}
              </option>
            </select>
          </div>

          <div v-if="pricingError" class="p-3 rounded-2xl border border-rose-200 bg-rose-50 text-rose-700 text-sm">
            {{ pricingError }}
          </div>
          <div v-if="pricingSuccess" class="p-3 rounded-2xl border border-emerald-200 bg-emerald-50 text-emerald-700 text-sm">
            {{ pricingSuccess }}
          </div>

          <div v-if="selectedVehicleType">
            <div class="grid grid-cols-1 gap-4">
              <div class="space-y-2">
                <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Hourly rate</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  v-model.number="hourlyRate"
                  class="w-full px-4 py-3 rounded-2xl border border-slate-200 bg-slate-50 text-slate-900 outline-none focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>

              <div class="space-y-2">
                <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Fixed rate cap</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  v-model.number="fixedRate"
                  class="w-full px-4 py-3 rounded-2xl border border-slate-200 bg-slate-50 text-slate-900 outline-none focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>

              <div class="space-y-2">
                <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Threshold (minutes)</label>
                <input
                  type="number"
                  min="1"
                  v-model.number="thresholdMinutes"
                  class="w-full px-4 py-3 rounded-2xl border border-slate-200 bg-slate-50 text-slate-900 outline-none focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>
            </div>

            <button
              @click="handleSavePricing"
              :disabled="pricingLoading"
              class="w-full mt-4 inline-flex items-center justify-center gap-2 py-3 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 font-semibold text-sm transition-all disabled:opacity-60"
            >
              <span v-if="pricingLoading">Saving...</span>
              <span v-else>Save Pricing</span>
            </button>
          </div>

          <div v-else class="rounded-3xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300">
            Select a vehicle type from above to load or create its pricing settings.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
