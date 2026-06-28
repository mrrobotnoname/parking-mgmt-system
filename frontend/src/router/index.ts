import { createRouter, createWebHistory } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

export const isRouteLoading = ref(false)

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('./views/Login.vue'),
    },
    {
      path: '/admin',
      component: () => import('./views/admin/AdminLayout.vue'),
      meta: { requiresAuth: true, role: 'admin' },
      children: [
        {
          path: '',
          redirect: '/admin/dashboard',
        },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('./views/admin/Dashboard.vue'),
        },
        {
          path: 'guards',
          name: 'Guards',
          component: () => import('./views/admin/Guards.vue'),
        },
        {
          path: 'parking-grid',
          name: 'ParkingGrid',
          component: () => import('./views/admin/ParkingGrid.vue'),
        },
        {
          path: 'vehicle-types',
          name: 'VehicleTypes',
          component: () => import('./views/admin/VehicleTypes.vue'),
        },
      ],
    },
    {
      path: '/guard',
      name: 'GuardDashboard',
      component: () => import('./views/guard/GuardDashboard.vue'),
      meta: { requiresAuth: true, role: 'guard' },
    },
  ],
})

router.beforeEach((to, from, next) => {
  isRouteLoading.value = true
  const authStore = useAuthStore()

  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      next('/login')
    } else if (to.meta.role && authStore.user?.role !== to.meta.role) {
      // Role mismatch
      if (authStore.user?.role === 'admin') {
        next('/admin/dashboard')
      } else if (authStore.user?.role === 'guard') {
        next('/guard')
      } else {
        next('/login')
      }
    } else {
      next()
    }
  } else {
    // If authenticated and tries to go to login, redirect to dashboard
    if (to.path === '/login' && authStore.isAuthenticated) {
      if (authStore.user?.role === 'admin') {
        next('/admin/dashboard')
      } else if (authStore.user?.role === 'guard') {
        next('/guard')
      } else {
        next()
      }
    } else {
      next()
    }
  }
})

router.afterEach(() => {
  isRouteLoading.value = false
})

export default router
