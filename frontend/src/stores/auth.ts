import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'

interface UserPayload {
  sub: string
  role: string
  name?: string
}

function parseJwt(token: string) {
  const payloadBase64Url = token.split('.')[1] || ''
  const payloadBase64 = payloadBase64Url
    .replace(/-/g, '+')
    .replace(/_/g, '/')
  const padded = payloadBase64.padEnd(payloadBase64.length + (4 - (payloadBase64.length % 4)) % 4, '=')
  return JSON.parse(atob(padded))
}

function normalizeUserPayload(payload: any): UserPayload {
  return {
    ...payload,
    role: typeof payload.role === 'string'
      ? payload.role.toLowerCase().trim()
      : payload.role,
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<UserPayload | null>(null)

  // Parse user from token if available
  if (token.value) {
    try {
      user.value = normalizeUserPayload(parseJwt(token.value))
    } catch (e) {
      console.error('Invalid token found in local storage:', e)
      token.value = null
      localStorage.removeItem('token')
    }
  }

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isGuard = computed(() => user.value?.role === 'guard')

  async function login(username: string, password: string) {
    // OAuth2PasswordRequestForm expects x-www-form-urlencoded format
    const params = new URLSearchParams()
    params.append('username', username)
    params.append('password', password)

    try {
      const response = await api.post('/api/v1/auth/login', params, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      })
      
      const accessToken = response.data.access_token
      token.value = accessToken
      localStorage.setItem('token', accessToken)

      // Decode token
      const payloadBase64 = accessToken.split('.')[1]
      const decoded = JSON.parse(atob(payloadBase64))
      user.value = decoded

      return decoded
    } catch (error) {
      throw error
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    window.location.href = '/login'
  }

  return {
    token,
    user,
    isAuthenticated,
    isAdmin,
    isGuard,
    login,
    logout,
  }
})
