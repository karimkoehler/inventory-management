<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card budget-card">
      <label for="restock-budget" class="budget-label">{{ t('restocking.budget') }}</label>
      <div class="budget-value">{{ formatCurrency(budget, currentCurrency) }}</div>
      <input
        id="restock-budget"
        type="range"
        min="0"
        max="100000"
        step="1000"
        v-model.number="budget"
        class="budget-slider"
      />
      <div class="budget-ticks">
        <span>{{ formatCurrency(0, currentCurrency) }}</span>
        <span>{{ formatCurrency(100000, currentCurrency) }}</span>
      </div>
      <p class="budget-hint">{{ t('restocking.budgetHint') }}</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">{{ t('restocking.summary.budget') }}</div>
        <div class="stat-value">{{ formatCurrency(totals.budget, currentCurrency) }}</div>
      </div>
      <div class="stat-card info">
        <div class="stat-label">{{ t('restocking.summary.totalCost') }}</div>
        <div class="stat-value">{{ formatCurrency(totals.total_cost, currentCurrency) }}</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">{{ t('restocking.summary.remaining') }}</div>
        <div class="stat-value">{{ formatCurrency(totals.remaining_budget, currentCurrency) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">{{ t('restocking.summary.itemsRecommended') }}</div>
        <div class="stat-value">{{ items.length }}</div>
      </div>
      <div :class="['stat-card', { warning: totals.items_skipped > 0 }]">
        <div class="stat-label">{{ t('restocking.summary.itemsSkipped') }}</div>
        <div class="stat-value">{{ totals.items_skipped }}</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ items.length }})</h3>
      </div>

      <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <template v-else>
        <div v-if="items.length === 0 && totals.items_skipped === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else-if="items.length === 0" class="empty-state">
          {{ t('restocking.noItemsWithinBudget') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.category') }}</th>
                <th>{{ t('restocking.table.warehouse') }}</th>
                <th class="num">{{ t('restocking.table.onHand') }}</th>
                <th class="num">{{ t('restocking.table.reorderPoint') }}</th>
                <th class="num">{{ t('restocking.table.forecast') }}</th>
                <th class="num">{{ t('restocking.table.shortfall') }}</th>
                <th class="num">{{ t('restocking.table.recommendedQty') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                <th class="num">{{ t('restocking.table.priority') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>{{ translateCategory(item.category) }}</td>
                <td>{{ translateWarehouse(item.warehouse) }}</td>
                <td class="num">{{ item.quantity_on_hand }}</td>
                <td class="num">{{ item.reorder_point }}</td>
                <td class="num">{{ item.forecasted_demand }}</td>
                <td class="num">{{ item.shortfall }}</td>
                <td class="num">
                  {{ item.recommended_quantity }}
                  <!-- Budget could not cover the full shortfall for this line -->
                  <span v-if="item.recommended_quantity < item.shortfall" class="badge warning">
                    {{ t('restocking.partialFill') }}
                  </span>
                </td>
                <td class="num">{{ formatCurrency(item.unit_cost, currentCurrency) }}</td>
                <td class="num">{{ formatCurrency(item.line_total, currentCurrency) }}</td>
                <td class="num">
                  {{ item.priority_score }}
                  <span v-if="item.quantity_on_hand <= item.reorder_point" class="badge danger">
                    {{ t('restocking.belowReorder') }}
                  </span>
                </td>
                <td>
                  <span :class="['badge', item.trend]">{{ t('trends.' + item.trend) }}</span>
                </td>
                <td class="num">{{ t('restocking.days', { count: item.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <div class="card-footer">
        <button class="btn-primary" :disabled="!canPlaceOrder" @click="placeOrder">
          {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
        </button>
      </div>
      <div v-if="submitError" class="error submit-error">{{ submitError }}</div>
    </div>

    <div v-if="lastOrder" class="confirmation">
      <strong>{{ t('restocking.orderPlaced', { orderNumber: lastOrder.order_number }) }}</strong>
      <p>{{ t('restocking.expectedDelivery', { date: formatDate(lastOrder.expected_delivery) }) }}</p>
      <p>{{ t('restocking.stockNotUpdatedHint') }}</p>
      <router-link to="/orders">{{ t('restocking.viewOrders') }}</router-link>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentLocale, currentCurrency, translateProductName, translateWarehouse } = useI18n()
    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    const budget = ref(25000)
    const items = ref([])
    const totals = ref({ budget: 25000, total_cost: 0, remaining_budget: 25000, items_skipped: 0 })
    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const submitError = ref(null)
    const lastOrder = ref(null)

    const canPlaceOrder = computed(() => items.value.length > 0 && !submitting.value)

    const loadRecommendations = async () => {
      try {
        loading.value = true
        error.value = null
        const { warehouse, category } = getCurrentFilters()
        const result = await api.getRestockRecommendations(budget.value, { warehouse, category })
        items.value = result.items
        totals.value = result.totals
      } catch (err) {
        error.value = 'Failed to load recommendations: ' + err.message
        console.error('Load error:', err)
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (!canPlaceOrder.value) return
      submitting.value = true
      submitError.value = null
      try {
        const payload = {
          budget: budget.value,
          items: items.value.map(i => ({ sku: i.sku, quantity: i.recommended_quantity }))
        }
        lastOrder.value = await api.createRestockOrder(payload)
        // Stock is not decremented server-side, so this is a consistency
        // refresh and is not expected to change the recommendations.
        await loadRecommendations()
      } catch (err) {
        submitError.value = t('restocking.orderFailed')
        console.error('Order error:', err)
      } finally {
        submitting.value = false
      }
    }

    // The range input fires continuously while dragging, so debounce reloads
    let budgetTimer = null
    watch(budget, () => {
      lastOrder.value = null
      clearTimeout(budgetTimer)
      budgetTimer = setTimeout(loadRecommendations, 300)
    })
    onBeforeUnmount(() => clearTimeout(budgetTimer))

    // Period and status filters are deliberately not watched: restock
    // recommendations depend only on warehouse and category.
    watch([selectedLocation, selectedCategory], () => {
      lastOrder.value = null
      loadRecommendations()
    })

    const translateCategory = (category) => {
      const categoryMap = {
        'Circuit Boards': t('categories.circuitBoards'),
        'Sensors': t('categories.sensors'),
        'Actuators': t('categories.actuators'),
        'Controllers': t('categories.controllers'),
        'Power Supplies': t('categories.powerSupplies')
      }
      return categoryMap[category] || category
    }

    const formatDate = (iso) => {
      const date = new Date(iso)
      if (isNaN(date.getTime())) return ''
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
    }

    onMounted(loadRecommendations)

    return {
      t,
      currentCurrency,
      translateProductName,
      translateWarehouse,
      translateCategory,
      formatCurrency,
      budget,
      items,
      totals,
      loading,
      error,
      submitting,
      submitError,
      lastOrder,
      canPlaceOrder,
      placeOrder,
      formatDate
    }
  }
}
</script>

<style scoped>
.budget-label {
  display: block;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.budget-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-3);
}

.budget-slider {
  width: 100%;
  accent-color: var(--color-primary);
}

.budget-ticks {
  display: flex;
  justify-content: space-between;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.budget-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-top: var(--space-3);
}

.num {
  text-align: right;
}

td .badge {
  margin-left: var(--space-2);
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  padding: 0.6rem var(--space-5);
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-error {
  margin-top: var(--space-3);
}

.confirmation {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: var(--color-success-text);
  border-radius: var(--radius-md);
  padding: var(--space-4) var(--space-5);
  margin-top: var(--space-4);
}

.confirmation p {
  margin: var(--space-1) 0;
}

.confirmation a {
  color: var(--color-success-text);
  font-weight: 600;
  text-decoration: underline;
}

.empty-state {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-6);
}
</style>
