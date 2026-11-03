<template>
  <div class="app" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <aside
      id="app-sidebar"
      class="sidebar"
      :class="{ 'drawer-open': navOpen }"
      :aria-label="t('nav.companyName')"
    >
      <div class="sidebar-brand">
        <span class="brand-mark" aria-hidden="true">{{ t('nav.companyName').charAt(0) }}</span>
        <div class="brand-text">
          <span class="brand-name">{{ t('nav.companyName') }}</span>
          <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
        </div>
        <button
          type="button"
          class="drawer-close"
          :aria-label="t('nav.closeMenu')"
          @click="closeNav"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true" focusable="false"><g v-html="icons.close" /></svg>
        </button>
      </div>

      <nav class="sidebar-nav">
        <div v-for="group in navGroups" :key="group.key" class="nav-group">
          <div class="nav-group-label">{{ t(group.labelKey) }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="nav-link"
            exact-active-class="active"
            :title="isRail ? t(item.labelKey) : null"
            :aria-label="isRail ? t(item.labelKey) : null"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
                 aria-hidden="true" focusable="false"><g v-html="item.icon" /></svg>
            <span class="nav-label">{{ t(item.labelKey) }}</span>
          </router-link>
        </div>
      </nav>

      <button
        type="button"
        class="collapse-toggle"
        :title="isRail ? t('nav.expand') : t('nav.collapse')"
        :aria-label="isRail ? t('nav.expand') : t('nav.collapse')"
        :aria-expanded="isRail ? 'false' : 'true'"
        @click="onToggleClick"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false"><g v-html="isRail ? icons.expand : icons.collapse" /></svg>
        <span class="nav-label">{{ t('nav.collapse') }}</span>
      </button>
    </aside>

    <div v-if="navOpen" class="drawer-backdrop" @click="closeNav"></div>

    <div class="app-main">
      <header class="topbar">
        <button
          type="button"
          class="menu-btn"
          :aria-label="t('nav.openMenu')"
          aria-controls="app-sidebar"
          :aria-expanded="navOpen ? 'true' : 'false'"
          @click="navOpen = true"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true" focusable="false"><g v-html="icons.menu" /></svg>
        </button>
        <h1 class="topbar-title">{{ pageTitle }}</h1>
        <div class="topbar-actions">
          <LanguageSwitcher />
          <ProfileMenu
            @show-profile-details="showProfileDetails = true"
            @show-tasks="showTasks = true"
          />
        </div>
      </header>
      <FilterBar />
      <main class="main-content">
        <div class="main-inner">
          <router-view />
        </div>
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

// Static SVG inner markup (from the nav icon reference). These are source
// constants, never user input, so rendering them with v-html is safe.
const icons = {
  overview: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  inventory: '<path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>',
  orders: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1"/><path d="M9 10h6M9 14h6M9 18h4"/>',
  restocking: '<path d="M3 6h11v10H3z"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
  demand: '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  spending: '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/><path d="M16 15h2"/>',
  reports: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  collapse: '<path d="M11 17l-5-5 5-5M18 17l-5-5 5-5"/>',
  expand: '<path d="M13 17l5-5-5-5M6 17l5-5-5-5"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>'
}

// Sidebar groups. Adding a route to the nav is a one-line change here.
const navGroups = [
  {
    key: 'overview',
    labelKey: 'nav.groups.overview',
    items: [{ path: '/', labelKey: 'nav.overview', icon: icons.overview }]
  },
  {
    key: 'operations',
    labelKey: 'nav.groups.operations',
    items: [
      { path: '/inventory', labelKey: 'nav.inventory', icon: icons.inventory },
      { path: '/orders', labelKey: 'nav.orders', icon: icons.orders },
      { path: '/restocking', labelKey: 'nav.restocking', icon: icons.restocking },
      { path: '/demand', labelKey: 'nav.demandForecast', icon: icons.demand }
    ]
  },
  {
    key: 'finance',
    labelKey: 'nav.groups.finance',
    items: [
      { path: '/spending', labelKey: 'nav.finance', icon: icons.spending },
      { path: '/reports', labelKey: 'nav.reports', icon: icons.reports }
    ]
  }
]

// localStorage key for the desktop collapsed-rail preference.
const SIDEBAR_STORAGE_KEY = 'sidebar-collapsed'

// Responsive tiers. These MUST stay in sync with the @media rules in the style block:
//   desktop (> 1024px): expanded sidebar, persisted collapse toggle
//   tablet  (641px-1024px): always-visible 72px icon rail; the toggle expands it as a
//                           temporary overlay (not persisted, no scroll lock)
//   phone   (<= 640px): off-canvas drawer opened from the top-bar menu button (scroll locked)
const TABLET_QUERY = '(min-width: 641px) and (max-width: 1024px)'
const PHONE_QUERY = '(max-width: 640px)'

const readSidebarCollapsed = () => {
  // Storage can throw (private mode, blocked cookies); fall back to expanded.
  try {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true'
  } catch (err) {
    return false
  }
}

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const route = useRoute()
    const sidebarCollapsed = ref(readSidebarCollapsed())
    // Single transient flag: phone drawer open OR tablet overlay expanded. Never persisted.
    const navOpen = ref(false)
    const tabletMql = window.matchMedia(TABLET_QUERY)
    const phoneMql = window.matchMedia(PHONE_QUERY)
    const isTablet = ref(tabletMql.matches)
    const isPhone = ref(phoneMql.matches)
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    const pageTitle = computed(() => {
      for (const group of navGroups) {
        const item = group.items.find(i => i.path === route.path)
        if (item) return t(item.labelKey)
      }
      return ''
    })

    // Desktop only: toggle and persist the collapsed preference.
    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarCollapsed.value))
      } catch (err) {
        // Preference just won't persist; the toggle still works for this session.
      }
    }

    // The tablet rail ignores the desktop preference and is always collapsed unless
    // temporarily expanded; the phone drawer (toggle hidden) is never a rail.
    const isRail = computed(() => {
      if (isTablet.value) return !navOpen.value
      if (isPhone.value) return false
      return sidebarCollapsed.value
    })

    const onToggleClick = () => {
      if (isTablet.value) {
        // Temporary overlay expansion: deliberately not written to localStorage.
        navOpen.value = !navOpen.value
      } else {
        toggleSidebar()
      }
    }

    const closeNav = () => {
      navOpen.value = false
    }

    // Close the drawer / overlay after navigating.
    watch(() => route.fullPath, closeNav)

    // Lock page scroll behind the phone drawer only. The tablet overlay leaves the
    // page scrollable (the rail stays visible and the backdrop closes it).
    watch([navOpen, isPhone], ([open, phone]) => {
      document.body.style.overflow = open && phone ? 'hidden' : ''
    })

    const onKeydown = (e) => {
      if (e.key === 'Escape' && navOpen.value) closeNav()
    }

    // When the viewport crosses a tier boundary, update the tier and reset transient
    // state so a stale drawer/overlay (and its scroll lock) can't carry over.
    const onTabletChange = (e) => {
      isTablet.value = e.matches
      closeNav()
    }
    const onPhoneChange = (e) => {
      isPhone.value = e.matches
      closeNav()
    }

    onMounted(() => {
      loadTasks()
      window.addEventListener('keydown', onKeydown)
      tabletMql.addEventListener('change', onTabletChange)
      phoneMql.addEventListener('change', onPhoneChange)
    })

    onBeforeUnmount(() => {
      window.removeEventListener('keydown', onKeydown)
      tabletMql.removeEventListener('change', onTabletChange)
      phoneMql.removeEventListener('change', onPhoneChange)
      document.body.style.overflow = ''
    })

    return {
      icons,
      navGroups,
      sidebarCollapsed,
      navOpen,
      isRail,
      pageTitle,
      onToggleClick,
      closeNav,
      t,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
:root {
  /* Surfaces and text (slate) */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-surface-muted: #f1f5f9;
  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;
  --color-text: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #64748b;
  --color-text-subtle: #94a3b8;

  /* Accent (blue) */
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-primary-soft: #eff6ff;
  --color-focus-ring: rgba(37, 99, 235, 0.25);

  /* Status */
  --color-success: #10b981;
  --color-success-soft: #d1fae5;
  --color-success-text: #065f46;
  --color-warning: #f59e0b;
  --color-warning-soft: #fed7aa;
  --color-warning-text: #92400e;
  --color-danger: #ef4444;
  --color-danger-soft: #fecaca;
  --color-danger-text: #991b1b;
  --color-info-soft: #dbeafe;
  --color-info-text: #1e40af;

  /* Sidebar (dark slate) */
  --color-sidebar-bg: #0f172a;
  --color-sidebar-text: #cbd5e1;
  --color-sidebar-text-muted: #64748b;
  --color-sidebar-hover: #1e293b;
  --color-sidebar-active-bg: rgba(37, 99, 235, 0.16);
  --color-sidebar-active-text: #ffffff;
  --color-sidebar-accent: #3b82f6;

  /* Spacing: 4px scale */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;

  /* Type scale */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;

  /* Radius and elevation */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.04);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);
  --shadow-lg: 0 12px 32px rgba(15, 23, 42, 0.16);

  /* Layout */
  --sidebar-width: 248px;
  --sidebar-width-collapsed: 72px;
  --topbar-height: 64px;
  --content-max-width: 1440px;

  /* Layering. Dropdowns (1000) and modals (2000) keep their existing values,
     so a modal always covers the mobile drawer. */
  --z-filterbar: 80;
  --z-topbar: 90;
  --z-sidebar: 95;
  --z-drawer-backdrop: 1090;
  --z-drawer: 1100;

  --transition-base: 200ms ease;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  min-height: 100vh;
}

/* ---- Sidebar ---- */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: var(--color-sidebar-bg);
  color: var(--color-sidebar-text);
  display: flex;
  flex-direction: column;
  z-index: var(--z-sidebar);
  transition: width var(--transition-base), transform var(--transition-base);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: var(--topbar-height);
  padding: 0 var(--space-5);
  flex-shrink: 0;
  border-bottom: 1px solid var(--color-sidebar-hover);
}

.brand-mark {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #ffffff;
  font-weight: 700;
  font-size: var(--font-size-base);
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  color: #ffffff;
  font-size: var(--font-size-base);
  font-weight: 700;
  letter-spacing: -0.025em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  color: var(--color-sidebar-text-muted);
  font-size: var(--font-size-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4) var(--space-3);
}

.nav-group + .nav-group {
  margin-top: var(--space-6);
}

.nav-group-label {
  padding: 0 var(--space-3);
  margin-bottom: var(--space-2);
  color: var(--color-sidebar-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.nav-link,
.collapse-toggle {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-1);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-sidebar-text);
  font: inherit;
  font-size: var(--font-size-sm);
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color var(--transition-base), color var(--transition-base);
}

.nav-link svg,
.collapse-toggle svg {
  flex-shrink: 0;
}

.nav-link:hover,
.collapse-toggle:hover {
  background: var(--color-sidebar-hover);
  color: #ffffff;
}

.nav-link:focus-visible,
.collapse-toggle:focus-visible,
.menu-btn:focus-visible,
.drawer-close:focus-visible {
  outline: 2px solid var(--color-sidebar-accent);
  outline-offset: 2px;
}

.nav-link.active {
  background: var(--color-sidebar-active-bg);
  color: var(--color-sidebar-active-text);
}

/* 3px accent bar on the left edge of the active item */
.nav-link.active::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--space-3));
  top: var(--space-2);
  bottom: var(--space-2);
  width: 3px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--color-sidebar-accent);
}

.collapse-toggle {
  width: calc(100% - var(--space-6));
  margin: 0 var(--space-3) var(--space-4);
  flex-shrink: 0;
}

.drawer-close {
  display: none;
  margin-left: auto;
  padding: var(--space-1);
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-sidebar-text);
  cursor: pointer;
}

.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  z-index: var(--z-drawer-backdrop);
}

/* ---- Content column ---- */
.app-main {
  margin-left: var(--sidebar-width);
  /* min-width: 0 lets flex/grid children shrink instead of widening the column past the viewport */
  min-width: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  transition: margin-left var(--transition-base);
}

.topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-topbar);
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: 0 var(--space-8);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.topbar-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.topbar-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.menu-btn {
  display: none;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.main-content {
  flex: 1;
  width: 100%;
  padding: var(--space-8);
}

.main-inner {
  max-width: var(--content-max-width);
  margin: 0 auto;
}

/* Icon rail look. Desktop: when the persisted preference is collapsed. */
@media (min-width: 1025px) {
  .sidebar-collapsed .sidebar {
    width: var(--sidebar-width-collapsed);
  }

  .sidebar-collapsed .app-main {
    margin-left: var(--sidebar-width-collapsed);
  }

  .sidebar-collapsed .brand-text,
  .sidebar-collapsed .nav-group-label,
  .sidebar-collapsed .nav-label {
    display: none;
  }

  .sidebar-collapsed .sidebar-brand {
    justify-content: center;
    padding: 0;
  }

  .sidebar-collapsed .nav-link,
  .sidebar-collapsed .collapse-toggle {
    justify-content: center;
    padding: var(--space-3) 0;
  }

  .sidebar-collapsed .nav-group + .nav-group {
    margin-top: var(--space-4);
  }
}

/* Tablet (641px-1024px): the rail is always visible and ignores the desktop collapsed
   preference. Keep these bounds in sync with TABLET_QUERY in the script.
   The content column reserves only the rail width; the expanded sidebar (.drawer-open)
   overlays the content instead of pushing it. */
@media (min-width: 641px) and (max-width: 1024px) {
  .sidebar {
    width: var(--sidebar-width-collapsed);
  }

  .app-main {
    margin-left: var(--sidebar-width-collapsed);
  }

  .sidebar:not(.drawer-open) .brand-text,
  .sidebar:not(.drawer-open) .nav-group-label,
  .sidebar:not(.drawer-open) .nav-label {
    display: none;
  }

  .sidebar:not(.drawer-open) .sidebar-brand {
    justify-content: center;
    padding: 0;
  }

  .sidebar:not(.drawer-open) .nav-link,
  .sidebar:not(.drawer-open) .collapse-toggle {
    justify-content: center;
    padding: var(--space-3) 0;
  }

  .sidebar:not(.drawer-open) .nav-group + .nav-group {
    margin-top: var(--space-4);
  }

  /* Expanded overlay: drawer layers put it above dropdowns (1000) but below modals (2000);
     the backdrop (1090) covers the content and the rail's slot. */
  .sidebar.drawer-open {
    width: var(--sidebar-width);
    z-index: var(--z-drawer);
    box-shadow: var(--shadow-lg);
  }
}

/* Tablet and phone share the compact top bar and content padding. */
@media (max-width: 1024px) {
  .topbar {
    padding: 0 var(--space-4);
    gap: var(--space-3);
  }

  .topbar-actions {
    flex-shrink: 0;
    gap: var(--space-2);
  }

  .main-content {
    padding: var(--space-4);
  }
}

/* Phone (<= 640px): off-canvas drawer. Keep in sync with PHONE_QUERY in the script.
   Layering: drawer 1100 and backdrop 1090 sit above dropdowns (1000) but below modals (2000). */
@media (max-width: 640px) {
  .sidebar {
    width: var(--sidebar-width);
    transform: translateX(-100%);
    z-index: var(--z-drawer);
    box-shadow: none;
  }

  .sidebar.drawer-open {
    transform: translateX(0);
    box-shadow: var(--shadow-lg);
  }

  .app-main {
    margin-left: 0;
  }

  .menu-btn,
  .drawer-close {
    display: inline-flex;
  }

  .collapse-toggle {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .app-main,
  .nav-link,
  .collapse-toggle {
    transition: none;
  }
}

/* ---- Shared page styles ---- */
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-2);
  letter-spacing: -0.025em;
}

.page-header p {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-surface);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
}

.stat-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--space-3);
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: var(--color-primary);
}

.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

th {
  text-align: left;
  padding: var(--space-2) var(--space-3);
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: var(--space-2) var(--space-3);
  border-top: 1px solid var(--color-surface-muted);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--color-bg);
}

.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success,
.badge.increasing {
  background: var(--color-success-soft);
  color: var(--color-success-text);
}

.badge.warning,
.badge.medium {
  background: var(--color-warning-soft);
  color: var(--color-warning-text);
}

.badge.danger,
.badge.decreasing,
.badge.high {
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
}

.badge.info,
.badge.low {
  background: var(--color-info-soft);
  color: var(--color-info-text);
}

.badge.submitted {
  background: #ede9fe;
  color: #5b21b6;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.loading {
  text-align: center;
  padding: var(--space-12);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.error {
  background: #fef2f2;
  border: 1px solid var(--color-danger-soft);
  color: var(--color-danger-text);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
  font-size: var(--font-size-sm);
}
</style>
