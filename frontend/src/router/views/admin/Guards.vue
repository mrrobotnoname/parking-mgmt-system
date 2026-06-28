<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '../../../services/api'
import {
  UserPlus,
  Search,
  Edit2,
  Trash2,
  Phone,
  User,
  Key,
  X,
  AlertTriangle,
  UserCheck
} from '@lucide/vue'

interface Guard {
  user_id: number
  username: string
  name: string
  phone_number: string
}

const guards = ref<Guard[]>([])
const loading = ref(true)
const searchQuery = ref('')
const errorMsg = ref('')

// Modal state
const modalOpen = ref(false)
const modalMode = ref<'add' | 'edit'>('add')
const selectedGuardId = ref<number | null>(null)

// Form fields
const formUsername = ref('')
const formPassword = ref('')
const formName = ref('')
const formPhone = ref('')
const formError = ref('')
const formLoading = ref(false)

// Delete Confirm State
const deleteConfirmOpen = ref(false)
const guardToDelete = ref<Guard | null>(null)
const deleteLoading = ref(false)

const filteredGuards = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  if (!query) return guards.value
  return guards.value.filter(g =>
    g.name.toLowerCase().includes(query) ||
    g.username.toLowerCase().includes(query) ||
    g.phone_number.includes(query)
  )
})

async function fetchGuards() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await api.get('/api/v1/admin/guard')
    guards.value = res.data
  } catch (err: any) {
    console.error(err)
    errorMsg.value = 'Failed to load guards accounts.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchGuards()
})

function openAddModal() {
  modalMode.value = 'add'
  selectedGuardId.value = null
  formUsername.value = ''
  formPassword.value = ''
  formName.value = ''
  formPhone.value = ''
  formError.value = ''
  modalOpen.value = true
}

function openEditModal(guard: Guard) {
  modalMode.value = 'edit'
  selectedGuardId.value = guard.user_id
  formUsername.value = guard.username
  formPassword.value = '' // leave empty to not update unless specified
  formName.value = guard.name
  formPhone.value = guard.phone_number
  formError.value = ''
  modalOpen.value = true
}

async function submitForm() {
  if (!formUsername.value || !formName.value || !formPhone.value) {
    formError.value = 'All fields except password (for edit) are required.'
    return
  }

  if (modalMode.value === 'add' && !formPassword.value) {
    formError.value = 'Password is required for new accounts.'
    return
  }

  formError.value = ''
  formLoading.value = true

  const payload: any = {
    username: formUsername.value,
    name: formName.value,
    phone_number: formPhone.value,
  }
  
  if (formPassword.value) {
    payload.password = formPassword.value
  }

  try {
    if (modalMode.value === 'add') {
      await api.post('/api/v1/admin/guard', payload)
    } else {
      await api.patch(`/api/v1/admin/guard/${selectedGuardId.value}`, payload)
    }
    
    modalOpen.value = false
    await fetchGuards()
  } catch (err: any) {
    console.error(err)
    if (err.response?.status === 400 && err.response?.data?.detail) {
      formError.value = err.response.data.detail
    }else if(err.response?.status === 409  && err.response?.data?.detail) {
      formError.value = err.response.data.detail
    }else {
      formError.value = 'Failed to save account. Please verify data.'
    }
  } finally {
    formLoading.value = false
  }
}

function confirmDelete(guard: Guard) {
  guardToDelete.value = guard
  deleteConfirmOpen.value = true
}

async function handleDelete() {
  if (!guardToDelete.value) return
  deleteLoading.value = true
  try {
    await api.delete(`/api/v1/admin/guard/${guardToDelete.value.user_id}`)
    deleteConfirmOpen.value = false
    guardToDelete.value = null
    await fetchGuards()
  } catch (err: any) {
    console.error(err)
    alert('Failed to delete account. Please try again.')
  } finally {
    deleteLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">Guard Accounts</h1>
        <p class="text-slate-500 dark:text-slate-400 mt-1">Manage security operators and entry/exit personnel</p>
      </div>

      <button
        @click="openAddModal"
        class="inline-flex items-center gap-2 py-3 px-5 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 active:from-violet-700 active:to-indigo-700 text-white font-semibold text-sm shadow-md shadow-violet-500/20 hover:shadow-lg transition-all duration-300 cursor-pointer"
      >
        <UserPlus class="w-4 h-4" />
        Add Guard Account
      </button>
    </div>

    <!-- Toolbar: Search & Refresher -->
    <div class="flex flex-col md:flex-row gap-4 items-stretch md:items-center">
      <!-- Search Input -->
      <div class="relative flex-1">
        <span class="absolute inset-y-0 left-0 flex items-center pl-4 text-slate-400 dark:text-slate-500">
          <Search class="w-5 h-5" />
        </span>
        <input
          type="text"
          v-model="searchQuery"
          placeholder="Search by name, username or phone number..."
          class="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 bg-white text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:ring-4 focus:ring-violet-500/10 dark:border-slate-800 dark:bg-slate-900 dark:text-white dark:placeholder-slate-600 dark:focus:border-violet-400 outline-none transition-all duration-300"
        />
      </div>
    </div>

    <!-- Error state -->
    <div
      v-if="errorMsg"
      class="p-4 border border-rose-200/50 bg-rose-50/50 text-rose-600 rounded-2xl text-sm"
    >
      {{ errorMsg }}
    </div>

    <!-- Loading State -->
    <div v-else-if="loading && guards.length === 0" class="flex flex-col items-center justify-center min-h-[250px] gap-3">
      <div class="h-8 w-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
      <span class="text-sm font-semibold text-slate-400">Loading accounts...</span>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="filteredGuards.length === 0"
      class="flex flex-col items-center justify-center min-h-[250px] border border-slate-200 border-dashed rounded-3xl p-6 dark:border-slate-800"
    >
      <UserCheck class="w-12 h-12 text-slate-300 dark:text-slate-700 mb-3" />
      <h3 class="font-bold text-slate-800 dark:text-slate-200 text-base">No Guards Found</h3>
      <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
        {{ searchQuery ? 'No accounts matched your search query.' : 'Create a new guard account to get started.' }}
      </p>
    </div>

    <!-- Guards Card List Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="guard in filteredGuards"
        :key="guard.user_id"
        class="border border-slate-200/80 bg-white rounded-3xl p-6 shadow-sm dark:border-slate-800/80 dark:bg-slate-900 hover:shadow-md transition-shadow duration-300 flex flex-col justify-between relative overflow-hidden"
      >
        <div class="absolute top-0 right-0 w-24 h-24 bg-violet-600/5 rounded-full blur-xl"></div>
        
        <div>
          <div class="flex items-center gap-3 mb-4">
            <div class="h-10 w-10 bg-violet-50 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400 rounded-xl flex items-center justify-center font-bold">
              {{ guard.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) }}
            </div>
            <div>
              <h3 class="font-bold text-slate-900 dark:text-white">{{ guard.name }}</h3>
              <span class="text-xs text-slate-400">@{{ guard.username }}</span>
            </div>
          </div>

          <div class="space-y-2 mt-4 text-sm text-slate-600 dark:text-slate-400">
            <div class="flex items-center gap-2">
              <Phone class="w-4 h-4 text-slate-400" />
              <span>{{ guard.phone_number }}</span>
            </div>
          </div>
        </div>

        <div class="flex gap-2.5 mt-6 border-t border-slate-100 dark:border-slate-800 pt-4">
          <button
            @click="openEditModal(guard)"
            class="flex-1 py-2 px-3 border border-slate-200 hover:border-violet-500/50 hover:text-violet-600 dark:border-slate-800 dark:hover:border-violet-500/50 dark:hover:text-violet-400 text-slate-500 text-xs font-semibold rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1.5"
          >
            <Edit2 class="w-3.5 h-3.5" />
            Edit
          </button>
          
          <button
            @click="confirmDelete(guard)"
            class="py-2 px-3.5 border border-slate-200 hover:bg-rose-50 hover:border-rose-200/50 hover:text-rose-600 dark:border-slate-800 dark:hover:bg-rose-950/20 dark:hover:border-rose-950/50 dark:hover:text-rose-400 text-slate-500 rounded-xl transition-all cursor-pointer flex items-center justify-center"
            title="Delete account"
          >
            <Trash2 class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>

    <!-- Edit/Add Modal -->
    <div
      v-if="modalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm"
    >
      <div
        class="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-2xl relative overflow-hidden animate-in fade-in zoom-in-95 duration-200"
      >
        <button
          @click="modalOpen = false"
          class="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
        >
          <X class="w-5 h-5" />
        </button>

        <h3 class="text-xl font-bold text-slate-900 dark:text-white mb-1">
          {{ modalMode === 'add' ? 'Add Guard Account' : 'Edit Guard Account' }}
        </h3>
        <p class="text-xs text-slate-400 mb-6">Fill in guard credentials and basic details</p>

        <div v-if="formError" class="p-3 border border-rose-200/50 bg-rose-50/50 text-rose-600 rounded-2xl text-xs mb-4">
          {{ formError }}
        </div>

        <form @submit.prevent="submitForm" class="space-y-4">
          <!-- Name -->
          <div class="space-y-1">
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Full Name</label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                <User class="w-4 h-4" />
              </span>
              <input
                type="text"
                v-model="formName"
                placeholder="John Doe"
                class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-800 dark:bg-slate-950 dark:text-white outline-none text-sm transition-all"
                required
              />
            </div>
          </div>

          <!-- Username -->
          <div class="space-y-1">
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Username</label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                <User class="w-4 h-4" />
              </span>
              <input
                type="text"
                v-model="formUsername"
                placeholder="johndoe"
                class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-800 dark:bg-slate-950 dark:text-white outline-none text-sm transition-all"
                required
              />
            </div>
          </div>

          <!-- Password -->
          <div class="space-y-1">
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Password {{ modalMode === 'edit' ? '(Leave empty to keep current)' : '' }}
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                <Key class="w-4 h-4" />
              </span>
              <input
                type="password"
                v-model="formPassword"
                placeholder="••••••••"
                class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-800 dark:bg-slate-950 dark:text-white outline-none text-sm transition-all"
                :required="modalMode === 'add'"
              />
            </div>
          </div>

          <!-- Phone Number -->
          <div class="space-y-1">
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Phone Number</label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                <Phone class="w-4 h-4" />
              </span>
              <input
                type="tel"
                v-model="formPhone"
                placeholder="+1234567890"
                class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder-slate-400 focus:border-violet-500 focus:bg-white dark:border-slate-800 dark:bg-slate-950 dark:text-white outline-none text-sm transition-all"
                required
              />
            </div>
          </div>

          <!-- Buttons -->
          <div class="flex gap-3 mt-6">
            <button
              type="button"
              @click="modalOpen = false"
              class="flex-1 py-3 px-4 border border-slate-200 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-50 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="formLoading"
              class="flex-1 py-3 px-4 bg-gradient-to-r from-violet-600 to-indigo-600 text-white rounded-xl text-sm font-semibold hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
            >
              <svg v-if="formLoading" class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Save Account
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Confirm Delete Modal -->
    <div
      v-if="deleteConfirmOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm"
    >
      <div
        class="w-full max-w-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-2xl relative overflow-hidden animate-in fade-in zoom-in-95 duration-200"
      >
        <div class="flex items-center gap-3.5 mb-4 text-rose-600">
          <div class="p-2 bg-rose-50 dark:bg-rose-950/40 rounded-xl">
            <AlertTriangle class="w-6 h-6" />
          </div>
          <h3 class="text-lg font-bold text-slate-900 dark:text-white">Delete Account?</h3>
        </div>
        
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-6 leading-relaxed">
          Are you sure you want to permanently delete the account for <strong class="text-slate-800 dark:text-slate-200">{{ guardToDelete?.name }}</strong>? This action cannot be undone.
        </p>

        <div class="flex gap-3">
          <button
            @click="deleteConfirmOpen = false"
            :disabled="deleteLoading"
            class="flex-1 py-3 px-4 border border-slate-200 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-50 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 cursor-pointer"
          >
            Cancel
          </button>
          <button
            @click="handleDelete"
            :disabled="deleteLoading"
            class="flex-1 py-3 px-4 bg-rose-600 text-white rounded-xl text-sm font-semibold hover:bg-rose-500 disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2 shadow-md shadow-rose-500/10"
          >
            <svg v-if="deleteLoading" class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
