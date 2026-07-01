<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import api from '../../../services/api'
import { useAuthStore } from '../../../stores/auth'
import { useTheme } from '../../../composables/useTheme'
import {
  Menu,
  Sun,
  Moon,
  LogOut,
  ShieldAlert,
  Check,
  AlertTriangle,
  Search,
  Lock,
  User,
  Phone,
  Car,
  Radio,
  Camera,
  CreditCard,
  Clock,
  CheckCircle2,
  UserPlus
} from '@lucide/vue'

const authStore = useAuthStore()
const { isDark, toggleTheme } = useTheme()

// UI state
const sidebarCollapsed = ref(false)
const mobileSidebarOpen = ref(false)
const activeTab = ref<'console' | 'register'>('console')
const isLocked = ref(false)
const showConfirmLogout = ref(false)
const cameraOffline = ref(false)  // driven by detector_status WS message
const isManualMode = ref(false)
const toasts = ref<{ id: number; message: string; type: 'success' | 'error' | 'info' | 'warning' }[]>([])

// ─── Detection state (replaces pendingEvents queue — one detection at a time) ───
// activeEvent holds the current detection pushed from server via WS.
// In manual mode it holds a guard-constructed object instead.
const activeEvent = ref<any | null>(null)
const plateInput = ref('')
const laneMode = ref<'ENTRY' | 'EXIT'>('ENTRY')
const activeEventImageUrl = ref('')   // built from image_b64 received via WS

// Entry workflow form fields
const ownerName = ref('')
const ownerPhone = ref('')
const selectedVehicleType = ref('')
const selectedVehicleTypeId = ref<number | null>(null)  // numeric id sent to server
const selectedSlotId = ref<number | null>(null)         // kept for UI display only (auto-assign on server)

// Exit workflow billing details — populated from exit_success WS message
const feeDetails = ref<any>(null)
const noSessionFound = ref(false)
const exitLookupQuery = ref('')

// Occupancy grid state
const occupancySearch = ref('')
const slots = ref<any[]>([])
const loadingSlots = ref(false)

// Registry tab state
const dailyUsers = ref<any[]>([])
const loadingUsers = ref(false)
const vehicleTypes = ref<any[]>([])

// Daily Register Form
const regName = ref('')
const regPhone = ref('')
const regPlate = ref('')
const regVehicleType = ref('Car')
const submittingRegister = ref(false)

// ─── Plate lookup debounce (manual mode) ────────────────────────────────────
let lookupDebounceTimer: ReturnType<typeof setTimeout> | null = null

// Toast Alert Engine
let toastId = 0
function addToast(message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') {
  const id = toastId++
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 4000)
}

// ─── Fetch helpers ───────────────────────────────────────────────────────────

async function fetchSlots() {
  loadingSlots.value = true
  try {
    const res = await api.get('/api/v1/guard/slots')
    slots.value = res.data
  } catch (err: any) {
    console.error('Failed to fetch slots:', err)
    addToast('Failed to load occupancy grid', 'error')
  } finally {
    loadingSlots.value = false
  }
}

async function fetchDailyUsers() {
  loadingUsers.value = true
  try {
    const res = await api.get('/api/v1/guard/daily-users')
    dailyUsers.value = res.data
  } catch (err: any) {
    console.error('Failed to fetch daily users:', err)
  } finally {
    loadingUsers.value = false
  }
}

async function fetchVehicleTypes() {
  try {
    const res = await api.get('/api/v1/guard/vehicles')
    vehicleTypes.value = res.data
  } catch (err: any) {
    console.error('Failed to fetch vehicle types:', err)
  }
}

// ─── Owner lookup (HTTP GET — used in both AI and manual modes) ──────────────

async function lookupOwnerByPlate(plate: string) {
  if (!plate.trim()) return
  try {
    const res = await api.get(`/api/v1/guard/lookup?plate=${plate.trim().toUpperCase()}`)
    if (res.data.found && res.data.owner) {
      const owner = res.data.owner
      ownerName.value = owner.name
      ownerPhone.value = owner.phone_number
      selectedVehicleTypeId.value = owner.vehicle_type_id

      // Map vehicle_type_id back to type string for the dropdown
      const vt = vehicleTypes.value.find(v => v.vehicle_id === owner.vehicle_type_id)
      selectedVehicleType.value = vt ? vt.vehicle_type : ''

      addToast(`Known owner found: ${owner.name}`, 'success')
    }
  } catch (err) {
    console.error('Owner lookup failed:', err)
  }
}

// ─── Watcher: when activeEvent changes, populate form fields ────────────────

watch(activeEvent, (newEvent) => {
  // Reset form
  ownerName.value = ''
  ownerPhone.value = ''
  selectedVehicleType.value = ''
  selectedVehicleTypeId.value = null
  selectedSlotId.value = null
  feeDetails.value = null
  noSessionFound.value = false

  if (!newEvent) {
    activeEventImageUrl.value = ''
    plateInput.value = ''
    return
  }

  plateInput.value = newEvent.plate || ''
  laneMode.value = (newEvent.direction?.toUpperCase() as 'ENTRY' | 'EXIT') || 'ENTRY'

  // Build image URL from base64 if present
  if (newEvent.image_b64) {
    activeEventImageUrl.value = `data:image/jpeg;base64,${newEvent.image_b64}`
  } else {
    activeEventImageUrl.value = ''
  }

  // Pre-fill owner if server already resolved it (AI mode)
  if (newEvent.owner) {
    const owner = newEvent.owner
    ownerName.value = owner.name || ''
    ownerPhone.value = owner.phone_number || ''
    selectedVehicleTypeId.value = owner.vehicle_type_id || null
    const vt = vehicleTypes.value.find(v => v.vehicle_id === owner.vehicle_type_id)
    selectedVehicleType.value = vt ? vt.vehicle_type : ''
  }
})

// ─── Watcher: sync selectedVehicleTypeId when dropdown changes ──────────────

watch(selectedVehicleType, (typeName) => {
  const vt = vehicleTypes.value.find(v => v.vehicle_type === typeName)
  selectedVehicleTypeId.value = vt ? vt.vehicle_id : null
})

// ─── Watcher: plate input debounce owner lookup ─────────────────

watch(plateInput, (newPlate) => {
  //if (!isManualMode.value || laneMode.value !== 'ENTRY') return
  if (lookupDebounceTimer) clearTimeout(lookupDebounceTimer)
  lookupDebounceTimer = setTimeout(() => {
    lookupOwnerByPlate(newPlate)
  }, 500)
})

// ─── Direction controls ──────────────────────────────────────────────────────

function setLaneMode(mode: 'ENTRY' | 'EXIT') {
  laneMode.value = mode
  // Reset billing state when switching
  feeDetails.value = null
  noSessionFound.value = false
}

function forceDirection(mode: 'ENTRY' | 'EXIT') {
  setLaneMode(mode)
  if (activeEvent.value) {
    activeEvent.value = { ...activeEvent.value, direction: mode }
  }
}

// ─── Manual mode toggle ──────────────────────────────────────────────────────

function toggleManualMode() {
  isManualMode.value = !isManualMode.value
  if (isManualMode.value) {
    activeEvent.value = null
    plateInput.value = ''
    ownerName.value = ''
    ownerPhone.value = ''
    selectedVehicleType.value = ''
    selectedVehicleTypeId.value = null
    selectedSlotId.value = null
    feeDetails.value = null
    noSessionFound.value = false
    addToast('Manual console mode active', 'info')
  } else {
    addToast('AI detector mode active', 'info')
  }
}

// ─── Plate verify button (manual correction in AI mode) ─────────────────────


// ─── Exit fee calculation (manual mode only) ─────────────────────────────────

async function calculateExitFee() {
  if (!plateInput.value.trim()) {
    addToast('Please enter a plate number', 'warning')
    return
  }
  const query = plateInput.value.trim().toUpperCase()
  try {
    const res = await api.post('/api/v1/guard/exit/calculate',{plate_text:query})
    
    feeDetails.value = res.data
    noSessionFound.value = false
    addToast('Parking fee calculated successfully', 'success')
  } catch (err: any) {
    feeDetails.value = null
    noSessionFound.value = true
    addToast(err.response?.data?.detail || 'No active check-in found for this vehicle', 'error')
  }
}

// ─── Confirm disabled logic ──────────────────────────────────────────────────

const isConfirmDisabled = computed(() => {
  if (!plateInput.value.trim()) return true
  if (laneMode.value === 'ENTRY' && !selectedVehicleTypeId.value) return true
  if (laneMode.value === 'EXIT' && isManualMode.value && (!feeDetails.value || noSessionFound.value)) return true
  if (!isManualMode.value && !activeEvent.value) return true
  return false
})

// ─── Reject / Drop (AI mode only — resumes detector without saving) ──────────

function rejectEvent() {
  if (!activeEvent.value || isManualMode.value) return
  sendWS({ type: 'confirm', direction: 'reject', plate: activeEvent.value.plate, vehicle_type_id: 0 })
  addToast(`Detection dropped for ${activeEvent.value.plate}`, 'warning')
  activeEvent.value = null
  plateInput.value = ''
  fetchSlots()
}

// ─── Main confirm handler ────────────────────────────────────────────────────

async function confirmEvent() {
  const plate = plateInput.value.trim().toUpperCase()

  if (!plate) {
    addToast('Please enter a valid plate number', 'warning')
    return
  }

  if (laneMode.value === 'ENTRY' && !selectedVehicleTypeId.value) {
    addToast('Vehicle classification type is required', 'warning')
    return
  }

  if (isManualMode.value) {
    if (laneMode.value === 'ENTRY') {
      try {
        await api.post('/api/v1/guard/entry', {
          plate:plateInput.value,
          name: ownerName.value,
          phone_number: ownerPhone.value,
          vehicle_type_id: selectedVehicleTypeId.value,
          slot_id: selectedSlotId.value
        })
        addToast(`Manual entry complete: ${plate}`, 'success')
        clearForm()
        fetchSlots()
        fetchDailyUsers()
        sendWS({ type: 'confirm', direction: 'reject', plate: activeEvent.value.plate, vehicle_type_id: 0 })
      } catch (err: any) {
        addToast(err.response?.data?.detail || 'Entry failed', 'error')
      }
    } else {
      try {
        await api.post('/api/v1/guard/exit', {
          
        })
        addToast(`Manual exit complete: ${plate}`, 'success')
        clearForm()
        fetchSlots()
        sendWS(
          { 
            type: 'confirm', direction: 'reject', plate: activeEvent.value.plate, vehicle_type_id: 0 

          })
      } catch (err: any) {
        addToast(err.response?.data?.detail || 'Exit failed', 'error')
      }
    }
    return
  }

  if (!activeEvent.value) return

  sendWS({
    type: 'confirm',
    direction: laneMode.value.toLowerCase(),
    plate,
    vehicle_type_id: selectedVehicleTypeId.value,
    owner_id: activeEvent.value.owner?.id ?? null
  })

  addToast(`Confirming ${laneMode.value.toLowerCase()} for ${plate}...`, 'info')
}

// ─── Form clear helper ───────────────────────────────────────────────────────

function clearForm() {
  activeEvent.value = null
  plateInput.value = ''
  ownerName.value = ''
  ownerPhone.value = ''
  selectedVehicleType.value = ''
  selectedVehicleTypeId.value = null
  selectedSlotId.value = null
  feeDetails.value = null
  noSessionFound.value = false
  activeEventImageUrl.value = ''
}

// ─── Exit backup registry lookup (manual fallback when no session found) ─────

async function handleExitLookup() {
  if (!exitLookupQuery.value.trim()) return
  const query = exitLookupQuery.value.trim().toUpperCase()
  const match = dailyUsers.value.find(u => u.plate_number.toUpperCase().includes(query))
  if (match) {
    plateInput.value = match.plate_number
    addToast(`Selected member: ${match.full_name} (${match.plate_number})`, 'success')
    await calculateExitFee()
  } else {
    plateInput.value = query
    addToast(`Manual plate set: ${query}`, 'info')
    await calculateExitFee()
  }
}

// ─── Occupancy Grid calculations ─────────────────────────────────────────────

const totalSlotsCount = computed(() => slots.value.length)
const occupiedSlotsCount = computed(() => slots.value.filter(s => s.is_occupied).length)

// Group slots safely by backend "floor" attribute
const floors = computed(() => {
  const grouped: Record<string, any[]> = {}
  slots.value.forEach(s => {
    const floorName = s.floor || 'F1'
    if (!grouped[floorName]) {
      grouped[floorName] = []
    }
    grouped[floorName].push(s)
  })

  return Object.keys(grouped)
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }))
    .map(name => ({
      name: name.startsWith('F') ? `Floor ${name.substring(1)}` : `Floor ${name}`,
      slots: grouped[name].sort((a, b) => {
        const numA = a.slot_number ?? 0
        const numB = b.slot_number ?? 0
        return numA - numB
      })
    }))
})

// Search occupancy grid using backend attributes
const filteredFloors = computed(() => {
  const query = occupancySearch.value.toLowerCase().trim()
  return floors.value.map(floor => {
    return {
      ...floor,
      slots: floor.slots.map(s => {
        let matches = true
        if (query) {
          const slotLabel = (s.display_slot || '').toLowerCase()
          const vType = (s.vehicle_type || '').toLowerCase()
          const plateMatch = s.occupant_plate?.toLowerCase().includes(query) || false
          const nameMatch = s.occupant_name?.toLowerCase().includes(query) || false
          matches = slotLabel.includes(query) || vType.includes(query) || plateMatch || nameMatch
        }
        return {
          ...s,
          isMuted: !matches
        }
      })
    }
  })
})

function handleSlotClick(slot: any) {
  if (slot.is_occupied) {
    addToast(`Slot ${slot.display_slot} is occupied by ${slot.occupant_plate || 'a vehicle'}`, 'warning')
    return
  }
  selectedSlotId.value = slot.slot_id
  addToast(`Selected parking slot: ${slot.display_slot}`, 'success')
}

function getSlotColorClass(slot: any) {
  if (slot.is_occupied) {
    return 'bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 border-rose-300 dark:border-rose-900/60 shadow-rose-500/5'
  }
  if (slot.is_accessible) {
    return 'bg-sky-50 dark:bg-sky-950/20 text-sky-600 dark:text-sky-400 border-sky-300 dark:border-sky-900/60 shadow-sky-500/5'
  }
  return 'bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 border-emerald-300 dark:border-emerald-900/60 shadow-emerald-500/5'
}

// Registry Form submission
async function submitMember() {
  if (!regName.value.trim() || !regPhone.value.trim() || !regPlate.value.trim()) {
    addToast('Please fill out all member onboarding fields', 'warning')
    return
  }

  submittingRegister.value = true
  try {
    const res = await api.post('/api/v1/guard/daily-users', {
      name: regName.value.trim(),
      phone_number: regPhone.value.trim(),
      vehicle_type: regVehicleType.value,
      plate_number: regPlate.value.trim().toUpperCase()
    })

    dailyUsers.value.unshift(res.data)
    addToast(`Successfully registered ${regName.value}`, 'success')

    regName.value = ''
    regPhone.value = ''
    regPlate.value = ''
    regVehicleType.value = 'Car'
  } catch (err: any) {
    console.error('Member onboarding failed:', err)
    addToast('Failed to onboarding registry user', 'error')
  } finally {
    submittingRegister.value = false
  }
}

function isUserCheckedIn(plateNumber: string) {
  return slots.value.some(s => s.is_occupied && s.occupant_plate?.toUpperCase() === plateNumber?.toUpperCase())
}

function handleLock() {
  isLocked.value = true
  addToast('Terminal session locked', 'warning')
}

function unlockSession() {
  isLocked.value = false
  addToast('Session unlocked', 'success')
}

function handleLogout() {
  showConfirmLogout.value = true
}

function confirmLogout() {
  isLocked.value = true
  showConfirmLogout.value = false
}

function enterShift() {
  authStore.logout()
}

// ─── WebSocket setup ─────────────────────────────────────────────────────────

let ws: WebSocket | null = null
let wsReconnectTimeout: ReturnType<typeof setTimeout> | null = null

function sendWS(data: object) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data))
  } else {
    console.warn('WS not open — message dropped:', data)
  }
}

function connectWS() {
  if (ws) ws.close()

  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsHost = import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/^https?:\/\//, '')
    : 'localhost:8000'

  const token = authStore.token
  const wsUrl = `${wsProtocol}//${wsHost}/api/v1/guard/ws?token=${token}`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('Guard WS connected.')
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      if (data.type === 'detection') {
        if (isManualMode.value) return
        activeEvent.value = data
        addToast(`Vehicle detected: ${data.plate}`, 'info')
        fetchSlots()
      }
      else if (data.type === 'detector_status') {
        cameraOffline.value = !data.online
        addToast(
          data.online ? 'AI detector connected' : 'AI detector offline — use manual mode',
          data.online ? 'success' : 'warning'
        )
      }
      else if (data.type === 'entry_success') {
        addToast(`Entry complete: ${data.plate} → Slot ${data.slot}`, 'success')
        clearForm()
        fetchSlots()
        fetchDailyUsers()
      }
      else if (data.type === 'exit_success') {
        feeDetails.value = {
          plate: data.plate,
          duration_minutes: data.duration_minutes,
          fee: data.fee,
          check_in_time: null
        }
        addToast(`Exit complete: ${data.plate} — Fee: $${data.fee?.toFixed(2)}`, 'success')
        setTimeout(() => {
          clearForm()
          fetchSlots()
        }, 4000)
      }
      else if (data.type === 'error') {
        addToast(data.message || 'Server error', 'error')
        if (data.message?.includes('No active session')) {
          noSessionFound.value = true
        }
      }

    } catch (e) {
      console.error('Error handling WebSocket message:', e)
    }
  }

  ws.onclose = () => {
    console.log('Guard WS closed. Retrying in 5s...')
    wsReconnectTimeout = setTimeout(connectWS, 5000)
  }

  ws.onerror = (e) => {
    console.error('Guard WS error:', e)
  }
}

onMounted(() => {
  fetchSlots()
  fetchDailyUsers()
  fetchVehicleTypes()
  connectWS()
})

onUnmounted(() => {
  if (ws) ws.close()
  if (wsReconnectTimeout) clearTimeout(wsReconnectTimeout)
  if (lookupDebounceTimer) clearTimeout(lookupDebounceTimer)
})
</script>

<template>
  <div
    class="h-screen w-screen flex bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 overflow-hidden select-none font-sans relative">

    <div class="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 max-w-sm pointer-events-none">
      <transition-group name="toast">
        <div v-for="toast in toasts" :key="toast.id" :class="[
          toast.type === 'success' ? 'bg-emerald-500 border-emerald-400' : '',
          toast.type === 'error' ? 'bg-rose-500 border-rose-400' : '',
          toast.type === 'warning' ? 'bg-amber-500 border-amber-400' : '',
          toast.type === 'info' ? 'bg-violet-600 border-violet-500' : '',
          'flex items-start gap-3 p-4 rounded-2xl border text-white shadow-xl pointer-events-auto transition-all duration-300'
        ]">
          <component
            :is="toast.type === 'success' ? CheckCircle2 : toast.type === 'error' ? ShieldAlert : AlertTriangle"
            class="w-5 h-5 shrink-0 mt-0.5" />
          <div class="text-sm font-semibold">{{ toast.message }}</div>
        </div>
      </transition-group>
    </div>

    <div v-if="showConfirmLogout"
      class="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-950/60 backdrop-blur-sm">
      <div
        class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-3xl max-w-sm w-full mx-4 shadow-2xl animate-shake">
        <div class="flex items-center gap-3 text-rose-500 mb-4">
          <AlertTriangle class="w-8 h-8" />
          <h3 class="font-extrabold text-xl">Sign Out</h3>
        </div>
        <p class="text-sm text-slate-500 dark:text-slate-400">
          Are you sure you want to end your current terminal shift and log out?
        </p>
        <div class="flex justify-end gap-3 mt-6">
          <button @click="showConfirmLogout = false"
            class="px-4 py-2 text-sm font-bold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-xl transition-all">
            Cancel
          </button>
          <button @click="confirmLogout"
            class="px-4 py-2 text-sm font-bold bg-rose-600 hover:bg-rose-500 text-white rounded-xl shadow-lg shadow-rose-500/20 transition-all">
            End Shift
          </button>
        </div>
      </div>
    </div>

    <transition name="lock-fade">
      <div v-if="isLocked"
        class="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-gradient-to-br from-slate-900 via-slate-950 to-indigo-950 text-white p-6">
        <div
          class="flex flex-col items-center max-w-md w-full bg-slate-900/60 border border-slate-800/80 rounded-3xl p-8 shadow-2xl backdrop-blur-2xl text-center">
          <div
            class="h-20 w-20 flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-xl shadow-violet-500/25 mb-6">
            <Lock class="w-10 h-10 text-white" />
          </div>
          <h2 class="text-3xl font-extrabold tracking-tight">Shift Locked</h2>
          <p class="text-sm text-slate-400 mt-2 mb-8">
            Your guard console shift is closed or locked. To resume or swap sessions, please sign in.
          </p>
          <div class="flex flex-col w-full gap-3">
            <button @click="unlockSession" v-if="authStore.isAuthenticated"
              class="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-bold hover:from-violet-500 hover:to-indigo-500 transition-all shadow-lg shadow-violet-500/25 flex items-center justify-center gap-2">
              <Check class="w-5 h-5" />
              <span>Resume Current Shift</span>
            </button>
            <button @click="enterShift"
              class="w-full py-4 px-6 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold transition-all flex items-center justify-center gap-2">
              <LogOut class="w-5 h-5" />
              <span>Login / Enter Shift</span>
            </button>
          </div>
        </div>
      </div>
    </transition>

    <aside :class="[
      sidebarCollapsed ? 'w-20' : 'w-72',
      mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      'fixed lg:static inset-y-0 left-0 z-40 bg-white/95 dark:bg-slate-900/95 border-r border-slate-200 dark:border-slate-800 backdrop-blur-md flex flex-col transition-all duration-300 ease-in-out shrink-0'
    ]">
      <div class="h-20 flex items-center gap-3 px-6 border-b border-slate-200/60 dark:border-slate-800/60 shrink-0">
        <div
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-500/25">
          <Car class="w-5 h-5" />
        </div>
        <div v-if="!sidebarCollapsed" class="min-w-0 transition-opacity">
          <span
            class="font-bold text-lg bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">Easy Parking</span>
          <span class="block text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Guard
            Panel</span>
        </div>
      </div>

      <nav class="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto">
        <button @click="activeTab = 'console'; mobileSidebarOpen = false" :class="[
          activeTab === 'console'
            ? 'bg-gradient-to-r from-violet-600/10 to-indigo-600/10 text-violet-600 dark:text-violet-400 font-semibold border-l-4 border-violet-600 dark:border-violet-500 pl-2.5'
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white border-l-4 border-transparent pl-3',
          'flex items-center gap-3.5 py-3.5 w-full text-left rounded-xl transition-all duration-200 group text-sm'
        ]">
          <Radio :class="[
            activeTab === 'console' ? 'text-violet-600 dark:text-violet-400' : 'text-slate-400 dark:text-slate-500 group-hover:text-slate-600 dark:group-hover:text-slate-300',
            'w-5 h-5 shrink-0 transition-colors duration-200'
          ]" />
          <span v-if="!sidebarCollapsed">Gate Console</span>
        </button>

        <button @click="activeTab = 'register'; mobileSidebarOpen = false" :class="[
          activeTab === 'register'
            ? 'bg-gradient-to-r from-violet-600/10 to-indigo-600/10 text-violet-600 dark:text-violet-400 font-semibold border-l-4 border-violet-600 dark:border-violet-500 pl-2.5'
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white border-l-4 border-transparent pl-3',
          'flex items-center gap-3.5 py-3.5 w-full text-left rounded-xl transition-all duration-200 group text-sm'
        ]">
          <UserPlus :class="[
            activeTab === 'register' ? 'text-violet-600 dark:text-violet-400' : 'text-slate-400 dark:text-slate-500 group-hover:text-slate-600 dark:group-hover:text-slate-300',
            'w-5 h-5 shrink-0 transition-colors duration-200'
          ]" />
          <span v-if="!sidebarCollapsed">Daily Registry</span>
        </button>
      </nav>

      <div
        class="p-4 border-t border-slate-200/60 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-900/30 flex flex-col gap-3 shrink-0">
        <div
          class="flex items-center gap-3 p-2 rounded-2xl bg-white dark:bg-slate-950 border border-slate-200/60 dark:border-slate-800/60">
          <div
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-100 dark:bg-violet-950/50 text-violet-600 dark:text-violet-400">
            <User class="w-5 h-5" />
          </div>
          <div v-if="!sidebarCollapsed" class="flex-1 min-w-0 transition-opacity">
            <span class="block font-bold text-xs truncate text-slate-800 dark:text-slate-200">
              {{ authStore.user?.sub || 'Security Guard' }}
            </span>
            <span
              class="block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider truncate">
              {{ authStore.user?.role || 'Guard' }}
            </span>
          </div>
        </div>

        <div class="flex items-center justify-between gap-2">
          <button @click="handleLock"
            class="flex-1 flex items-center justify-center p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 dark:border-slate-800 dark:bg-slate-950 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-all cursor-pointer"
            title="Lock Session">
            <Lock class="w-4 h-4" />
          </button>
          <button @click="handleLogout"
            class="flex-1 flex items-center justify-center p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-rose-50 dark:hover:bg-rose-950/10 hover:border-rose-200 dark:hover:border-rose-950/40 text-slate-600 hover:text-rose-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400 dark:hover:text-rose-400 transition-all cursor-pointer"
            title="End Shift / Logout">
            <LogOut class="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>

    <main class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
      <header
        class="h-20 shrink-0 flex items-center justify-between px-6 border-b border-slate-200/60 dark:border-slate-800/60 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md z-30 transition-all duration-300">
        <div class="flex items-center gap-3">
          <button @click="mobileSidebarOpen = !mobileSidebarOpen"
            class="p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-900 hover:bg-slate-100 lg:hidden">
            <Menu class="w-5 h-5" />
          </button>

          <button @click="sidebarCollapsed = !sidebarCollapsed"
            class="hidden lg:flex p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-900 hover:bg-slate-100 transition-all">
            <Menu class="w-5 h-5" />
          </button>

          <h2 class="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {{ activeTab === 'console' ? 'Gate Control Station' : 'Daily User Register' }}
          </h2>
        </div>

        <div class="flex items-center gap-3">
          <button @click="toggleTheme"
            class="p-2.5 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 transition-all">
            <component :is="isDark ? Sun : Moon" class="w-5 h-5" />
          </button>

          <button @click="toggleManualMode" :class="[
            isManualMode
              ? 'bg-amber-500 hover:bg-amber-400 text-white shadow-lg shadow-amber-500/20 border-transparent'
              : 'bg-white hover:bg-slate-100 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 dark:hover:bg-slate-800',
            'flex items-center gap-2 py-2.5 px-4 rounded-xl border font-semibold text-sm transition-all cursor-pointer'
          ]">
            <Radio class="w-4 h-4" />
            <span>{{ isManualMode ? 'Manual Mode: ON' : 'Manual Mode: OFF' }}</span>
          </button>

          <button @click="handleLock"
            class="hidden sm:flex items-center gap-2 py-2.5 px-4 rounded-xl text-slate-600 border border-slate-200 bg-white hover:bg-slate-100 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 font-semibold text-sm transition-all">
            <Lock class="w-4 h-4" />
            <span>Lock Terminal</span>
          </button>
        </div>
      </header>

      <div class="flex-1 overflow-y-auto p-6 md:p-8 space-y-8">
        <div v-if="activeTab === 'console'" class="space-y-8">
          <div class="grid grid-cols-1 xl:grid-cols-2 gap-8">
            <div
              class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex flex-col">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div class="flex items-center gap-2.5">
                  <span class="relative flex h-3 w-3">
                    <span
                      class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                  </span>
                  <span
                    class="font-extrabold text-sm uppercase tracking-wider text-slate-500 dark:text-slate-400">Vision
                    System</span>
                </div>
              </div>

              <div v-if="activeEvent && !isManualMode"
                class="mb-5 flex items-center gap-3 px-4 py-2.5 rounded-2xl border border-violet-200 dark:border-violet-900/60 bg-violet-50 dark:bg-violet-950/20">
                <span class="relative flex h-2.5 w-2.5">
                  <span
                    class="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-violet-500"></span>
                </span>
                <span class="text-xs font-bold text-violet-600 dark:text-violet-400 uppercase tracking-wider">Detection
                  active — awaiting guard confirmation</span>
                <span :class="[
                  laneMode === 'ENTRY'
                    ? 'bg-violet-100 text-violet-600 dark:bg-violet-950 dark:text-violet-400'
                    : 'bg-amber-100 text-amber-600 dark:bg-amber-950 dark:text-amber-400',
                  'ml-auto px-2.5 py-1 rounded-lg text-xs font-bold uppercase tracking-wider'
                ]">
                  {{ laneMode }}
                </span>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
                <div
                  class="relative rounded-2xl overflow-hidden aspect-[4/3] bg-slate-900 border border-slate-950 flex flex-col items-center justify-center text-slate-500 shadow-inner group">
                  <div v-if="isManualMode" class="flex flex-col items-center gap-3">
                    <Radio class="w-12 h-12 text-amber-500 animate-pulse" />
                    <span class="text-xs font-semibold text-slate-400">Manual Console Mode Active</span>
                    <span class="text-[10px] text-slate-500">Camera radar feed bypassed</span>
                  </div>
                  <img v-else-if="activeEventImageUrl && !cameraOffline" :src="activeEventImageUrl" alt="Camera Capture"
                    class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
                  <div v-else-if="!cameraOffline" class="flex flex-col items-center gap-3">
                    <Camera class="w-12 h-12 text-slate-700 animate-pulse" />
                    <span class="text-xs font-semibold text-slate-600">Waiting for Vision Event</span>
                  </div>

                  <div
                    class="absolute top-3 left-3 bg-slate-950/80 backdrop-blur-md px-3 py-1 text-[10px] font-bold text-white rounded-lg uppercase tracking-wider flex items-center gap-1.5 border border-slate-800">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>CAM_01_MAIN</span>
                  </div>

                  <transition name="fade">
                    <div v-if="cameraOffline"
                      class="absolute inset-0 bg-slate-950/95 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center z-10 animate-pulse border-2 border-rose-600/30 rounded-2xl">
                      <ShieldAlert class="w-12 h-12 text-rose-500 mb-2" />
                      <h4 class="font-extrabold text-white text-base tracking-tight">VISION DISCONNECTED</h4>
                      <p class="text-xs text-slate-400 mt-1">
                        Simulated Vision hardware failure code: E_CAMERA_DOWN. Override manual control active.
                      </p>
                    </div>
                  </transition>
                </div>

                <div
                  class="flex flex-col justify-between p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/80">
                  <div class="space-y-4">
                    <span class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Vision
                      OCR Readout</span>

                    <div class="space-y-2">
                      <div
                        class="font-mono text-3xl font-extrabold tracking-wider uppercase text-slate-800 dark:text-white text-center py-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm">
                        {{ plateInput || '--------' }}
                      </div>

                      <div class="flex justify-between items-center px-1">
                        <span class="text-xs font-semibold text-slate-400">Direction Vector</span>
                        <span v-if="activeEvent || isManualMode" :class="[
                          laneMode === 'ENTRY'
                            ? 'bg-violet-100 text-violet-600 dark:bg-violet-950/40 dark:text-violet-400'
                            : 'bg-amber-100 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400',
                          'px-2.5 py-1 rounded-lg text-xs font-bold uppercase tracking-wider'
                        ]">
                          {{ laneMode }}
                        </span>
                        <span v-else class="text-xs font-semibold text-slate-500">N/A</span>
                      </div>
                    </div>
                  </div>

                  <div class="space-y-2 pt-4 border-t border-slate-200/50 dark:border-slate-800/50">
                    <span
                      class="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Manual
                      Vector Overrides:</span>
                    <div class="flex gap-2">
                      <button @click="forceDirection('ENTRY')" :disabled="!activeEvent || isManualMode" :class="[
                        laneMode === 'ENTRY'
                          ? 'bg-violet-600 hover:bg-violet-500 text-white shadow-md shadow-violet-600/20'
                          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800',
                        'flex-1 py-2 px-3 rounded-xl font-semibold text-xs transition-all cursor-pointer'
                      ]">
                        Force Entry
                      </button>
                      <button @click="forceDirection('EXIT')" :disabled="!activeEvent || isManualMode" :class="[
                        laneMode === 'EXIT'
                          ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-md shadow-amber-600/20'
                          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800',
                        'flex-1 py-2 px-3 rounded-xl font-semibold text-xs transition-all cursor-pointer'
                      ]">
                        Force Exit
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div
              class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex flex-col justify-between">
              <div class="space-y-6">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <span class="font-extrabold text-sm uppercase tracking-wider text-slate-500 dark:text-slate-400">Lane
                    Mode Controller</span>

                  <div
                    class="flex bg-slate-100 dark:bg-slate-950 p-1.5 rounded-2xl border border-slate-200/50 dark:border-slate-800/50">
                    <button @click="setLaneMode('ENTRY')" :class="[
                      laneMode === 'ENTRY'
                        ? 'bg-white dark:bg-slate-900 text-violet-600 dark:text-violet-400 shadow-md font-bold'
                        : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 font-semibold',
                      'px-4 py-2 rounded-xl text-xs uppercase tracking-wider transition-all'
                    ]">
                      Entry Mode
                    </button>
                    <button @click="setLaneMode('EXIT')" :class="[
                      laneMode === 'EXIT'
                        ? 'bg-white dark:bg-slate-900 text-amber-600 dark:text-amber-400 shadow-md font-bold'
                        : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 font-semibold',
                      'px-4 py-2 rounded-xl text-xs uppercase tracking-wider transition-all'
                    ]">
                      Exit Mode
                    </button>
                  </div>
                </div>

                <div class="space-y-2">
                  <label class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Plate
                    Number </label>
                  <div class="flex gap-2">
                    <div class="relative flex-1">
                      <span class="absolute inset-y-0 left-0 flex items-center pl-4 text-slate-400">
                        <Car class="w-5 h-5" />
                      </span>
                      <input type="text" v-model="plateInput" placeholder="Plate number"
                        class="w-full pl-11 pr-4 py-3.5 rounded-2xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white focus:ring-4 focus:ring-violet-500/10 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white dark:placeholder-slate-700 dark:focus:border-violet-400 dark:focus:bg-slate-950 dark:focus:ring-violet-400/10 outline-none transition-all duration-300 font-mono text-base font-bold uppercase tracking-wider" />
                    </div>

                    <button v-if="laneMode === 'EXIT'" @click="calculateExitFee" :disabled="!plateInput.trim()"
                      class="px-5 bg-slate-950 hover:bg-slate-800 text-white dark:bg-slate-800 dark:hover:bg-slate-700 font-bold rounded-2xl transition-all flex items-center gap-2 text-sm border border-transparent dark:border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed">
                      <span>Calculate</span>
                    </button>
                  </div>
                </div>

                <div class="pt-4 border-t border-slate-100 dark:border-slate-800/80 min-h-[160px]">
                  <div v-if="laneMode === 'ENTRY'" class="space-y-4">
                    <div class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                      Onboarding Check-In Metadata</div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div class="space-y-1.5">
                        <span class="text-xs font-semibold text-slate-500">Driver Full Name</span>
                        <input type="text" v-model="ownerName" placeholder="e.g. John Doe"
                          class="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white dark:focus:border-violet-400 outline-none text-sm transition-all" />
                      </div>
                      <div class="space-y-1.5">
                        <span class="text-xs font-semibold text-slate-500">Phone Contact</span>
                        <input type="text" v-model="ownerPhone" placeholder="e.g. +91 999999"
                          class="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white dark:focus:border-violet-400 outline-none text-sm transition-all" />
                      </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div class="space-y-1.5">
                        <span class="text-xs font-semibold text-slate-500">Vehicle Classification</span>
                        <select v-model="selectedVehicleType"
                          class="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white focus:border-violet-500 dark:focus:border-violet-400 outline-none text-sm transition-all">
                          <option value="">Select Type</option>
                          <option v-for="v in vehicleTypes" :key="v.vehicle_id" :value="v.vehicle_type">
                            {{ v.vehicle_type }}
                          </option>
                        </select>
                      </div>

                      <div class="space-y-1.5">
                        <span class="text-xs font-semibold text-slate-500">Selected Slot Allocation</span>
                        <div
                          class="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-950/50 font-mono text-sm font-bold flex items-center justify-between">
                          <span :class="selectedSlotId ? 'text-violet-600 dark:text-violet-400' : 'text-slate-400'">
                            {{selectedSlotId ? slots.find(s => s.slot_id === selectedSlotId)?.display_slot : 'None Selected' }}
                          </span>
                          <span class="text-[10px] text-slate-400 font-sans uppercase">Click slot below</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-else-if="laneMode === 'EXIT'" class="space-y-4">
                    <div v-if="feeDetails"
                      class="bg-gradient-to-br from-slate-900 to-indigo-950 text-white rounded-2xl p-5 border border-slate-800/80 shadow-md flex flex-col gap-4 animate-shake">
                      <div class="flex justify-between items-start border-b border-slate-800 pb-3 shrink-0">
                        <div>
                          <h4 class="font-extrabold text-sm uppercase tracking-wider text-slate-400">Exit Billing
                            Invoice</h4>
                          <span class="text-xs font-mono text-violet-400">{{ feeDetails.plate }}</span>
                        </div>
                        <CreditCard class="w-6 h-6 text-violet-400" />
                      </div>

                      <div class="grid grid-cols-2 gap-4 text-xs">
                        <div class="space-y-1">
                          <span class="text-slate-400 uppercase tracking-wider block text-[10px]">Check-In Time</span>
                          <div class="font-semibold flex items-center gap-1.5">
                            <Clock class="w-3.5 h-3.5 text-violet-400" />
                            <span>{{ feeDetails.check_in_time ? new Date(feeDetails.check_in_time).toLocaleTimeString()
                              : 'N/A' }}</span>
                          </div>
                        </div>
                        <div class="space-y-1">
                          <span class="text-slate-400 uppercase tracking-wider block text-[10px]">Total Duration</span>
                          <div class="font-semibold flex items-center gap-1.5">
                            <Clock class="w-3.5 h-3.5 text-violet-400" />
                            <span>{{ Math.round(feeDetails.duration_minutes) }} mins</span>
                          </div>
                        </div>
                      </div>

                      <div class="flex justify-between items-center pt-3 border-t border-slate-800 mt-1">
                        <span class="text-sm font-bold text-slate-400">Total Due Amount:</span>
                        <span class="text-2xl font-black text-emerald-400 font-mono">${{ feeDetails.fee?.toFixed(2)
                          }}</span>
                      </div>
                    </div>

                    <div v-else-if="noSessionFound"
                      class="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-950/50 text-rose-800 dark:text-rose-400 rounded-2xl p-5 flex flex-col gap-4">
                      <div class="flex items-start gap-3">
                        <AlertTriangle class="w-6 h-6 text-rose-500 shrink-0 mt-0.5" />
                        <div>
                          <h4 class="font-bold text-sm">No Active Check-In Session</h4>
                          <p class="text-xs text-rose-700/80 dark:text-rose-400/80 mt-1">
                            No check-in record matches the plate: <span class="font-mono font-bold">{{ plateInput ||
                              'N/A' }}</span>.
                          </p>
                        </div>
                      </div>

                      <div class="space-y-2 pt-2 border-t border-rose-200/50 dark:border-rose-950/20">
                        <label
                          class="text-[10px] font-bold text-rose-500 dark:text-rose-400 uppercase tracking-wider block">Backup
                          Registry Manual Search:</label>
                        <div class="flex gap-2">
                          <div class="relative flex-1">
                            <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-rose-400">
                              <Search class="w-4 h-4" />
                            </span>
                            <input type="text" v-model="exitLookupQuery" placeholder="Search registry plate / name"
                              class="w-full pl-9 pr-4 py-2.5 rounded-xl border border-rose-200 bg-white/70 dark:bg-slate-900 text-rose-900 placeholder-rose-400 focus:border-rose-500 dark:border-rose-800 dark:text-white outline-none text-xs" />
                          </div>
                          <button @click="handleExitLookup"
                            class="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-xl text-xs transition-all shadow-md shadow-rose-500/10 cursor-pointer">
                            Lookup
                          </button>
                        </div>
                      </div>
                    </div>

                    <div v-else
                      class="flex flex-col items-center justify-center p-6 text-slate-400 dark:text-slate-600 gap-2 text-center h-full">
                      <CreditCard class="w-10 h-10 animate-pulse" />
                      <span class="text-xs font-semibold">Please input or verify a license plate above</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="flex items-center gap-4 mt-6 pt-6 border-t border-slate-100 dark:border-slate-800/80">
                <button @click="rejectEvent" :disabled="!activeEvent || isManualMode"
                  class="flex-1 py-4 px-6 rounded-2xl bg-rose-50 border border-rose-200/80 text-rose-600 hover:bg-rose-100 dark:bg-rose-950/10 dark:border-rose-950/40 dark:text-rose-400 dark:hover:bg-rose-950/20 font-bold text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer">
                  Deny
                </button>
                <button @click="confirmEvent" :disabled="isConfirmDisabled"
                  class="flex-1 py-4 px-6 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold text-sm shadow-lg shadow-violet-500/25 hover:shadow-xl hover:shadow-violet-500/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer">
                  Confirm
                </button>
              </div>
            </div>
          </div>

          <div
            class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-6">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h3 class="text-lg font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                  <span>Occupancy Grid Map</span>
                  <span
                    class="text-xs font-medium text-slate-400 bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-2 py-0.5">
                    {{ occupiedSlotsCount }} / {{ totalSlotsCount }} In Use
                  </span>
                </h3>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Click an empty slot node to allocate
                  check-in slots</p>
              </div>

              <div class="relative w-full md:max-w-xs">
                <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                  <Search class="w-4 h-4" />
                </span>
                <input type="text" v-model="occupancySearch" placeholder="Search by plate, owner or slot..."
                  class="w-full pl-10 pr-4 py-2.5 rounded-2xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white outline-none text-xs transition-all" />
              </div>
            </div>

            <div class="space-y-8 max-h-[480px] overflow-y-auto pr-1">
              <div v-for="floor in filteredFloors" :key="floor.name" class="space-y-3">
                <div
                  class="text-xs font-extrabold uppercase tracking-wider text-slate-400 dark:text-slate-500 flex items-center gap-2">
                  <span>{{ floor.name }}</span>
                  <span class="h-0.5 bg-slate-200 dark:bg-slate-800 flex-1"></span>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 gap-4">
                  <div v-for="slot in floor.slots" :key="slot.slot_id" @click="handleSlotClick(slot)" :class="[
                    getSlotColorClass(slot),
                    selectedSlotId === slot.slot_id ? 'ring-4 ring-violet-500/80 border-violet-500 dark:border-violet-500' : 'border-slate-200 dark:border-slate-800/80',
                    slot.isMuted ? 'opacity-20 pointer-events-none' : 'opacity-100',
                    'relative group cursor-pointer p-3.5 rounded-2xl border shadow-sm flex flex-col items-center justify-between text-center select-none transition-all duration-300'
                  ]">
                    <span v-if="slot.is_accessible" class="absolute top-2 left-2 text-xs"
                      title="Accessible Space">♿</span>

                    <div v-if="slot.is_occupied"
                      class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3.5 hidden group-hover:block z-[999] w-64 bg-slate-950/95 dark:bg-black/95 text-white rounded-2xl p-4 shadow-2xl border border-slate-800 pointer-events-none transition-all duration-200">
                      <div
                        class="text-[10px] font-extrabold uppercase tracking-wider text-slate-500 mb-2.5 text-left flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                        <span>Occupant telemetries</span>
                      </div>
                      <div class="space-y-1.5 text-xs text-left">
                        <div class="flex justify-between items-center">
                          <span class="text-slate-400">Plate Number:</span>
                          <span
                            class="font-mono font-bold text-violet-400 bg-violet-950/40 px-2 py-0.5 rounded border border-violet-800/40">{{
                              slot.occupant_plate || 'N/A' }}</span>
                        </div>
                        <div class="flex justify-between items-center">
                          <span class="text-slate-400">Driver Name:</span>
                          <span class="font-semibold text-slate-220">{{ slot.occupant_name || 'Daily User' }}</span>
                        </div>
                        <div class="flex justify-between items-center">
                          <span class="text-slate-400">Phone Contact:</span>
                          <span class="text-slate-300 font-mono">{{ slot.occupant_phone || 'None' }}</span>
                        </div>
                        <div class="flex justify-between items-center">
                          <span class="text-slate-400">Vehicle Type:</span>
                          <span class="font-semibold text-slate-200 uppercase">{{ slot.vehicle_type }}</span>
                        </div>
                      </div>
                    </div>

                    <span class="text-xs font-bold tracking-tight text-slate-400 dark:text-slate-500">{{
                      slot.display_slot }}</span>
                    <span class="font-mono text-sm font-black mt-1 text-slate-800 dark:text-slate-200">
                      {{ slot.is_occupied ? (slot.occupant_plate || 'OCCUPIED') : 'VACANT' }}
                    </span>
                    <span class="text-[9px] font-semibold uppercase text-slate-400 mt-1">
                      {{ slot.vehicle_type }}
                    </span>
                    <span class="text-[9px] font-semibold uppercase text-slate-400">
                      {{ slot.is_accessible ? 'Accessible' : 'Standard' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="activeTab === 'register'" class="space-y-8">
          <div
            class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm">
            <h3 class="text-2xl font-extrabold text-slate-900 dark:text-white">Daily Member Registration</h3>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Onboard and manage pre-registered vehicles. Matched license plates dynamically auto-populate gate
              check-ins.
            </p>
          </div>

          <div class="grid grid-cols-1 xl:grid-cols-3 gap-8 items-start">
            <div
              class="xl:col-span-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-6">
              <h4 class="font-extrabold text-base text-slate-900 dark:text-white flex items-center gap-2">
                <UserPlus class="w-5 h-5 text-violet-500" />
                <span>Onboard Member</span>
              </h4>

              <form @submit.prevent="submitMember" class="space-y-4">
                <div class="space-y-1.5">
                  <label class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Driver
                    Full Name</label>
                  <div class="relative">
                    <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                      <User class="w-4 h-4" />
                    </span>
                    <input type="text" v-model="regName" required placeholder="e.g. Walter White"
                      class="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white dark:focus:border-violet-400 outline-none text-sm transition-all" />
                  </div>
                </div>

                <div class="space-y-1.5">
                  <label class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Phone
                    Contact</label>
                  <div class="relative">
                    <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                      <Phone class="w-4 h-4" />
                    </span>
                    <input type="text" v-model="regPhone" required placeholder="e.g. +91 9876543210"
                      class="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white dark:focus:border-violet-400 outline-none text-sm transition-all" />
                  </div>
                </div>

                <div class="space-y-1.5">
                  <label class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">License
                    Plate Number</label>
                  <div class="relative">
                    <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                      <Car class="w-4 h-4" />
                    </span>
                    <input type="text" v-model="regPlate" required placeholder="e.g. MH-12-AB-1234"
                      class="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white dark:focus:border-violet-400 outline-none text-sm transition-all font-mono font-bold uppercase tracking-wide" />
                  </div>
                </div>

                <div class="space-y-1.5">
                  <label class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Vehicle
                    Classification</label>
                  <select v-model="regVehicleType"
                    class="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 dark:border-slate-800 dark:bg-slate-950/50 dark:text-white focus:border-violet-500 dark:focus:border-violet-400 outline-none text-sm transition-all">
                    <option v-for="v in vehicleTypes" :key="v.vehicle_id" :value="v.vehicle_id">
                      {{ v.vehicle_type }}
                    </option>
                  </select>
                </div>

                <button type="submit" :disabled="submittingRegister"
                  class="w-full py-3.5 px-6 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold text-sm shadow-md shadow-violet-500/20 hover:shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer">
                  <span v-if="submittingRegister"
                    class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                  <span>Register</span>
                </button>
              </form>
            </div>

            <div
              class="xl:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-6">
              <div class="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-4">
                <div>
                  <h4 class="font-extrabold text-base text-slate-900 dark:text-white">Registered Members Database</h4>
                  <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">List of active daily users registered on
                    terminal</p>
                </div>

                <span
                  class="bg-violet-50 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400 font-extrabold text-sm px-3.5 py-1.5 rounded-xl border border-violet-100 dark:border-violet-900/60 shadow-sm">
                  {{ dailyUsers.length }} Members
                </span>
              </div>

              <div class="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800/80">
                <table class="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr
                      class="bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500 font-extrabold uppercase text-[10px] tracking-wider">
                      <th class="py-4 px-5">Member Name</th>
                      <th class="py-4 px-5">Phone Contact</th>
                      <th class="py-4 px-5">Vehicle Category</th>
                      <th class="py-4 px-5">License Plate</th>
                      <th class="py-4 px-5">Parking Status</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100 dark:divide-slate-800/60 font-medium">
                    <tr v-for="user in dailyUsers" :key="user.id"
                      class="hover:bg-slate-50/50 dark:hover:bg-slate-950/30 text-slate-700 dark:text-slate-300 transition-colors">
                      <td class="py-4 px-5 font-bold text-slate-900 dark:text-white">{{ user.name }}</td>
                      <td class="py-4 px-5 font-mono text-xs">{{ user.phone_number }}</td>
                      <td class="py-4 px-5">{{ user.vehicle }}</td>
                      <td class="py-4 px-5">
                        <span
                          class="font-mono font-bold bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded px-2.5 py-1 text-slate-900 dark:text-slate-100">
                          {{ user.plate_number }}
                        </span>
                      </td>
                      <td class="py-4 px-5">
                        <span :class="[
                          isUserCheckedIn(user.plate_number)
                            ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400'
                            : 'bg-slate-100 text-slate-500 dark:bg-slate-950/40 dark:text-slate-400',
                          'px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 w-max'
                        ]">
                          <span
                            :class="[isUserCheckedIn(user.plate_number) ? 'bg-emerald-500' : 'bg-slate-400', 'w-1.5 h-1.5 rounded-full']"></span>
                          <span>{{ isUserCheckedIn(user.plate_number) ? 'In Parking' : 'Outside' }}</span>
                        </span>
                      </td>
                    </tr>

                    <tr v-if="dailyUsers.length === 0">
                      <td colspan="5" class="py-8 text-center text-slate-400 dark:text-slate-600 font-semibold">
                        No registered members found. Create one using the form on the left.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Transiton transitions */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(24px) scale(0.9);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100px);
}

.lock-fade-enter-active,
.lock-fade-leave-active {
  transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.lock-fade-enter-from,
.lock-fade-leave-to {
  opacity: 0;
}

@keyframes shake {

  0%,
  100% {
    transform: translateX(0);
  }

  25% {
    transform: translateX(-4px);
  }

  75% {
    transform: translateX(4px);
  }
}

.animate-shake {
  animation: shake 0.35s ease-in-out;
}

/* Custom scrollbar adjustments */
.scrollbar-thin::-webkit-scrollbar {
  height: 5px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 99px;
}

.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}
</style>