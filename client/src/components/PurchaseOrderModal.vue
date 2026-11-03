<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" role="dialog" aria-modal="true" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'view' ? t('purchaseOrder.viewTitle') : t('purchaseOrder.createTitle') }}
            </h3>
            <button class="close-button" :aria-label="t('common.close')" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="item-summary">
              <div class="item-name">{{ translateProductName(backlogItem.item_name) }}</div>
              <div class="item-meta">
                <span>{{ t('purchaseOrder.sku') }}: <span class="mono">{{ backlogItem.item_sku }}</span></span>
                <span>{{ t('purchaseOrder.shortfall') }}: <strong>{{ shortfall }} {{ t('purchaseOrder.units') }}</strong></span>
              </div>
            </div>

            <!-- View mode -->
            <template v-if="mode === 'view'">
              <div v-if="loading" class="state-message">{{ t('common.loading') }}</div>
              <div v-else-if="error" class="error-message" role="alert">{{ error }}</div>
              <div v-else-if="purchaseOrder" class="info-grid">
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.poNumber') }}</div>
                  <div class="info-value mono">{{ purchaseOrder.id }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.status') }}</div>
                  <div class="info-value"><span class="badge">{{ purchaseOrder.status }}</span></div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.supplierName') }}</div>
                  <div class="info-value">{{ purchaseOrder.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                  <div class="info-value">{{ purchaseOrder.quantity }} {{ t('purchaseOrder.units') }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                  <div class="info-value">{{ formatCurrencyWithDecimals(purchaseOrder.unit_cost, currentCurrency, 2) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.totalCost') }}</div>
                  <div class="info-value">{{ formatCurrency(purchaseOrder.quantity * purchaseOrder.unit_cost, currentCurrency) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.expectedDelivery') }}</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.expected_delivery_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.createdDate') }}</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.created_date) }}</div>
                </div>
                <div v-if="purchaseOrder.notes" class="info-item full-width">
                  <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value notes-text">{{ purchaseOrder.notes }}</div>
                </div>
              </div>
            </template>

            <!-- Create mode -->
            <form v-else id="po-form" class="po-form" novalidate @submit.prevent="submit">
              <div class="form-field">
                <label for="po-supplier">{{ t('purchaseOrder.supplierName') }}</label>
                <input id="po-supplier" v-model="form.supplier_name" type="text" maxlength="200" />
                <div v-if="touched && fieldErrors.supplier" class="field-error">{{ fieldErrors.supplier }}</div>
              </div>

              <div class="form-row">
                <div class="form-field">
                  <label for="po-quantity">{{ t('purchaseOrder.quantity') }}</label>
                  <input id="po-quantity" v-model="form.quantity" type="number" min="1" step="1" />
                  <div v-if="touched && fieldErrors.quantity" class="field-error">{{ fieldErrors.quantity }}</div>
                </div>
                <div class="form-field">
                  <label for="po-unit-cost">{{ t('purchaseOrder.unitCost') }}</label>
                  <input id="po-unit-cost" v-model="form.unit_cost" type="number" min="0" step="0.01" />
                  <div v-if="touched && fieldErrors.unitCost" class="field-error">{{ fieldErrors.unitCost }}</div>
                </div>
              </div>

              <div class="form-field">
                <label for="po-date">{{ t('purchaseOrder.expectedDelivery') }}</label>
                <input id="po-date" v-model="form.expected_delivery_date" type="date" :min="todayString" />
                <div v-if="touched && fieldErrors.date" class="field-error">{{ fieldErrors.date }}</div>
              </div>

              <div class="form-field">
                <label for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                <textarea id="po-notes" v-model="form.notes" rows="3" maxlength="1000"></textarea>
              </div>

              <div class="total-row">
                <span class="info-label">{{ t('purchaseOrder.totalCost') }}</span>
                <span class="total-value">{{ formatCurrency(totalCost, currentCurrency) }}</span>
              </div>

              <div v-if="error" class="error-message" role="alert">{{ error }}</div>
            </form>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="close">{{ t('common.close') }}</button>
            <button
              v-if="mode !== 'view'"
              type="submit"
              form="po-form"
              class="btn-primary"
              :disabled="!isValid || submitting"
            >
              {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from '../composables/useI18n'
import { api } from '../api'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

// Local YYYY-MM-DD (not toISOString, which is UTC and can be off by a day)
const toDateString = (date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export default {
  name: 'PurchaseOrderModal',
  props: {
    isOpen: { type: Boolean, default: false },
    backlogItem: { type: Object, default: null },
    mode: { type: String, default: 'create', validator: (v) => ['create', 'view'].includes(v) }
  },
  emits: ['close', 'po-created'],
  setup(props, { emit }) {
    const { t, currentCurrency, translateProductName } = useI18n()

    const form = reactive({
      supplier_name: '',
      quantity: '',
      unit_cost: '',
      expected_delivery_date: '',
      notes: ''
    })
    const touched = ref(false)
    const submitting = ref(false)
    const loading = ref(false)
    const error = ref(null)
    const purchaseOrder = ref(null)
    // Guards against a stale response overwriting state after close/reopen
    let requestToken = 0

    const todayString = computed(() => toDateString(new Date()))

    const shortfall = computed(() => {
      if (!props.backlogItem) return 0
      return Math.max(props.backlogItem.quantity_needed - props.backlogItem.quantity_available, 0)
    })

    const fieldErrors = computed(() => {
      const errs = {}
      if (!form.supplier_name.trim()) errs.supplier = t('purchaseOrder.errors.supplierRequired')

      const qty = Number(form.quantity)
      if (form.quantity === '' || !Number.isInteger(qty) || qty < 1) {
        errs.quantity = t('purchaseOrder.errors.quantityInvalid')
      }

      const cost = Number(form.unit_cost)
      if (form.unit_cost === '' || !Number.isFinite(cost) || cost <= 0) {
        errs.unitCost = t('purchaseOrder.errors.unitCostInvalid')
      }

      if (!form.expected_delivery_date) {
        errs.date = t('purchaseOrder.errors.dateRequired')
      } else if (form.expected_delivery_date < todayString.value) {
        // ISO date strings compare correctly as plain strings
        errs.date = t('purchaseOrder.errors.datePast')
      }
      return errs
    })

    const isValid = computed(() => Object.keys(fieldErrors.value).length === 0)

    const totalCost = computed(() => {
      const qty = Number(form.quantity)
      const cost = Number(form.unit_cost)
      if (!Number.isFinite(qty) || !Number.isFinite(cost)) return 0
      return qty * cost
    })

    const formatDate = (value) => {
      if (!value) return 'N/A'
      const date = new Date(value)
      if (isNaN(date.getTime())) return value
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    }

    const errorMessage = (err, fallbackKey) => {
      const status = err?.response?.status
      if (status === 409) return t('purchaseOrder.alreadyExists')
      if (status === 404) return t('purchaseOrder.notFound')
      return t(fallbackKey)
    }

    const resetState = () => {
      form.supplier_name = ''
      form.quantity = shortfall.value > 0 ? shortfall.value : ''
      form.unit_cost = ''
      form.expected_delivery_date = ''
      form.notes = ''
      touched.value = false
      submitting.value = false
      loading.value = false
      error.value = null
      purchaseOrder.value = null
    }

    const loadPurchaseOrder = async () => {
      const token = ++requestToken
      loading.value = true
      try {
        const result = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
        if (token !== requestToken) return
        purchaseOrder.value = result
      } catch (err) {
        if (token !== requestToken) return
        error.value = errorMessage(err, 'purchaseOrder.loadFailed')
        console.error('Failed to load purchase order:', err)
      } finally {
        if (token === requestToken) loading.value = false
      }
    }

    const submit = async () => {
      touched.value = true
      if (!isValid.value || submitting.value) return
      const token = ++requestToken
      submitting.value = true
      error.value = null
      try {
        const notes = form.notes.trim()
        const created = await api.createPurchaseOrder({
          backlog_item_id: props.backlogItem.id,
          supplier_name: form.supplier_name.trim(),
          quantity: Number(form.quantity),
          unit_cost: Number(form.unit_cost),
          expected_delivery_date: form.expected_delivery_date,
          ...(notes ? { notes } : {})
        })
        if (token !== requestToken) return
        emit('po-created', created)
      } catch (err) {
        if (token !== requestToken) return
        error.value = errorMessage(err, 'purchaseOrder.createFailed')
        console.error('Failed to create purchase order:', err)
      } finally {
        if (token === requestToken) submitting.value = false
      }
    }

    const close = () => emit('close')

    const onKeydown = (event) => {
      if (event.key === 'Escape' && props.isOpen) close()
    }

    // Reset (and load in view mode) every time the modal opens
    watch(
      () => props.isOpen,
      (open) => {
        if (!open) {
          requestToken++ // invalidate any in-flight request
          return
        }
        resetState()
        if (props.mode === 'view' && props.backlogItem) loadPurchaseOrder()
      },
      { immediate: true }
    )

    onMounted(() => document.addEventListener('keydown', onKeydown))
    onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

    return {
      t,
      currentCurrency,
      translateProductName,
      formatCurrency,
      formatCurrencyWithDecimals,
      form,
      touched,
      submitting,
      loading,
      error,
      purchaseOrder,
      todayString,
      shortfall,
      fieldErrors,
      isValid,
      totalCost,
      formatDate,
      submit,
      close
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: var(--space-4);
}

.modal-container {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: var(--space-2);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.close-button:hover {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6) var(--space-8);
}

.item-summary {
  padding: var(--space-4);
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-6);
}

.item-name {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-5);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.item-meta strong {
  color: var(--color-danger-text);
}

.mono {
  font-family: 'Monaco', 'Courier New', monospace;
}

.po-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-field label,
.info-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.form-field input,
.form-field textarea {
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-family: inherit;
  color: var(--color-text);
  background: var(--color-surface);
  resize: vertical;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.field-error {
  font-size: var(--font-size-sm);
  color: var(--color-danger-text);
}

.total-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.total-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.error-message {
  padding: var(--space-3) var(--space-4);
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}

.state-message {
  padding: var(--space-6);
  text-align: center;
  color: var(--color-text-muted);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-6);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-value {
  font-size: var(--font-size-sm);
  color: var(--color-text);
  font-weight: 500;
}

.notes-text {
  white-space: pre-wrap;
}

.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-info-soft);
  color: var(--color-info-text);
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-transform: capitalize;
}

.modal-footer {
  padding: var(--space-6);
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.btn-secondary,
.btn-primary {
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-md);
  font-weight: 500;
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary {
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.btn-secondary:hover {
  background: var(--color-border);
  border-color: var(--color-border-strong);
}

.btn-primary {
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
