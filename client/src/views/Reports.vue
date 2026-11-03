<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.subtitle') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('reports.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="isEmpty" class="empty-state">{{ t('reports.noData') }}</div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterly.title') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.quarterly.quarter') }}</th>
                <th>{{ t('reports.quarterly.totalOrders') }}</th>
                <th>{{ t('reports.quarterly.totalRevenue') }}</th>
                <th>{{ t('reports.quarterly.avgOrderValue') }}</th>
                <th>{{ t('reports.quarterly.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td><strong>{{ q.quarter }}</strong></td>
                <td>{{ q.total_orders }}</td>
                <td>{{ formatCurrency(q.total_revenue, currentCurrency) }}</td>
                <td>{{ formatCurrency(q.avg_order_value, currentCurrency) }}</td>
                <td>
                  <span :class="getFulfillmentClass(q.fulfillment_rate)">
                    {{ q.fulfillment_rate }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.trend.title') }}</h3>
        </div>
        <div class="chart-container">
          <div class="bar-chart" role="group" :aria-label="t('reports.trend.ariaLabel')">
            <div v-for="month in monthlyData" :key="month.month" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  role="img"
                  :aria-label="formatMonth(month.month) + ': ' + formatCurrency(month.revenue, currentCurrency)"
                  :style="{ height: getBarHeight(month.revenue) + 'px' }"
                  :title="formatCurrency(month.revenue, currentCurrency)"
                ></div>
              </div>
              <div class="bar-label" aria-hidden="true">{{ formatMonth(month.month) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.mom.title') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.mom.month') }}</th>
                <th>{{ t('reports.mom.orders') }}</th>
                <th>{{ t('reports.mom.revenue') }}</th>
                <th>{{ t('reports.mom.change') }}</th>
                <th>{{ t('reports.mom.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in monthlyRows" :key="row.month">
                <td><strong>{{ formatMonth(row.month) }}</strong></td>
                <td>{{ row.order_count }}</td>
                <td>{{ formatCurrency(row.revenue, currentCurrency) }}</td>
                <td>
                  <span v-if="row.hasPrevious" :class="getChangeClass(row.change)">
                    {{ formatChange(row.change) }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="row.hasPrevious" :class="getChangeClass(row.change)">
                    {{ formatGrowthRate(row.growthRate) }}
                  </span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalRevenue') }}</div>
          <div class="stat-value">{{ formatCurrency(totalRevenue, currentCurrency) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ formatCurrency(avgMonthlyRevenue, currentCurrency) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalOrders') }}</div>
          <div class="stat-value">{{ totalOrders }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.bestQuarter') }}</div>
          <div class="stat-value">{{ bestQuarter }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

// Maps the 1-based month number from "YYYY-MM" to its locale key
const MONTH_KEYS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
const MONTH_PATTERN = /^(\d{4})-(0[1-9]|1[0-2])$/

// Max bar height in px; must match .bar-container height
const MAX_BAR_HEIGHT = 200

export default {
  name: 'Reports',
  setup() {
    const { t, currentCurrency } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const quarterlyData = ref([])
    const monthlyData = ref([])

    // Use shared filters
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    // Incremented per request so a slow response from an older filter
    // selection cannot overwrite the result of a newer one.
    let requestId = 0

    const loadData = async () => {
      const currentRequest = ++requestId
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()
        const [quarterly, monthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters)
        ])
        if (currentRequest !== requestId) return
        quarterlyData.value = quarterly
        monthlyData.value = monthly
      } catch (err) {
        if (currentRequest !== requestId) return
        console.error('Error loading reports:', err)
        error.value = t('reports.loadError') + ': ' + err.message
      } finally {
        if (currentRequest === requestId) loading.value = false
      }
    }

    // Watch for filter changes and reload data
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadData()
    })

    onMounted(() => {
      loadData()
    })

    const isEmpty = computed(() => {
      return quarterlyData.value.length === 0 && monthlyData.value.length === 0
    })

    const totalRevenue = computed(() => {
      return monthlyData.value.reduce((sum, m) => sum + m.revenue, 0)
    })

    const avgMonthlyRevenue = computed(() => {
      return monthlyData.value.length > 0 ? totalRevenue.value / monthlyData.value.length : 0
    })

    const totalOrders = computed(() => {
      return monthlyData.value.reduce((sum, m) => sum + m.order_count, 0)
    })

    const bestQuarter = computed(() => {
      let best = null
      for (const q of quarterlyData.value) {
        if (best === null || q.total_revenue > best.total_revenue) best = q
      }
      return best ? best.quarter : t('reports.notAvailable')
    })

    // Computed once per data change (not once per bar)
    const maxRevenue = computed(() => {
      return monthlyData.value.reduce((max, m) => Math.max(max, m.revenue), 0)
    })

    // Each row carries its change vs. the previous month so the template
    // never has to index into the array.
    const monthlyRows = computed(() => {
      return monthlyData.value.map((m, i) => {
        const prev = i > 0 ? monthlyData.value[i - 1] : null
        const change = prev ? m.revenue - prev.revenue : 0
        return {
          ...m,
          hasPrevious: prev !== null,
          change,
          // Growth from a zero base is undefined -> null (rendered as N/A)
          growthRate: prev && prev.revenue !== 0 ? (change / prev.revenue) * 100 : null
        }
      })
    })

    const formatMonth = (monthStr) => {
      // Convert YYYY-MM to a localized label; the locale's template sets the word order.
      // Falls back to the raw value if malformed
      const match = MONTH_PATTERN.exec(monthStr)
      if (!match) return String(monthStr)
      const [, year, month] = match
      return t('reports.monthLabel', { month: t('months.' + MONTH_KEYS[parseInt(month, 10) - 1]), year })
    }

    const getBarHeight = (revenue) => {
      if (maxRevenue.value === 0) return 0
      return (revenue / maxRevenue.value) * MAX_BAR_HEIGHT
    }

    const getFulfillmentClass = (rate) => {
      if (rate >= 90) return 'badge success'
      if (rate >= 75) return 'badge warning'
      return 'badge danger'
    }

    const formatChange = (change) => {
      // Explicit sign; formatCurrency gets the absolute value so the sign precedes the symbol
      const sign = change > 0 ? '+' : change < 0 ? '-' : ''
      return sign + formatCurrency(Math.abs(change), currentCurrency.value)
    }

    const getChangeClass = (change) => {
      if (change > 0) return 'positive-change'
      if (change < 0) return 'negative-change'
      return ''
    }

    const formatGrowthRate = (rate) => {
      if (rate === null) return t('reports.notAvailable')
      return (rate > 0 ? '+' : '') + rate.toFixed(1) + '%'
    }

    return {
      t,
      currentCurrency,
      formatCurrency,
      loading,
      error,
      quarterlyData,
      monthlyData,
      monthlyRows,
      isEmpty,
      totalRevenue,
      avgMonthlyRevenue,
      totalOrders,
      bestQuarter,
      formatMonth,
      getBarHeight,
      getFulfillmentClass,
      formatChange,
      getChangeClass,
      formatGrowthRate
    }
  }
}
</script>

<style scoped>
.reports {
  padding: 0;
}

.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  margin-bottom: var(--space-6);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-header {
  margin-bottom: var(--space-6);
}

.card-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th {
  background: var(--color-bg);
  padding: var(--space-3);
  text-align: left;
  font-weight: 600;
  color: var(--color-text-muted);
  border-bottom: 2px solid var(--color-border);
}

.reports-table td {
  padding: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.reports-table tr:hover {
  background: var(--color-bg);
}

.chart-container {
  padding: var(--space-8) var(--space-4);
  min-height: 300px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: var(--space-2);
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: linear-gradient(to top, #3b82f6, #60a5fa);
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: linear-gradient(to top, #2563eb, #3b82f6);
}

.bar-label {
  margin-top: var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: var(--space-6);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-4);
  margin-top: var(--space-6);
}

.stat-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-left: 4px solid var(--color-primary);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-text);
}

.badge {
  padding: var(--space-1) var(--space-3);
  border-radius: 9999px;
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.badge.success {
  background: #dcfce7;
  color: #166534;
}

.badge.warning {
  background: #fef3c7;
  color: var(--color-warning-text);
}

.badge.danger {
  background: #fee2e2;
  color: var(--color-danger-text);
}

.positive-change {
  color: #16a34a;
  font-weight: 600;
}

.negative-change {
  color: #dc2626;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-12);
}

.loading {
  text-align: center;
  padding: var(--space-12);
  color: var(--color-text-muted);
}

.error {
  background: #fee2e2;
  color: var(--color-danger-text);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
}

/* <= 1024px (same breakpoint as the app drawer): scroll the chart inside its card instead of widening the page */
@media (max-width: 1024px) {
  .chart-container {
    overflow-x: auto;
  }

  .bar-chart {
    min-width: 560px;
  }
}
</style>
