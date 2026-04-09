<template>
  <div class="page">
    <!-- Header -->
    <div class="header">
      <h1>CTR FX Remeasurement</h1>
      <div class="subtitle">Consolidated Transaction Report &mdash; FX Gain/Loss Calculator</div>
    </div>

    <!-- Layout: sidebar + content -->
    <div class="layout">
      <div class="sidebar">
        <div class="sidebar-section">
          <div class="sidebar-label">Process</div>
          <div
            class="sidebar-item"
            :class="{ active: currentView === 'process' }"
            @click="navigate('process')"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            Process CTR
          </div>
        </div>
        <div class="sidebar-section">
          <div class="sidebar-label">Config</div>
          <div
            class="sidebar-item"
            :class="{ active: currentView === 'mapping' }"
            @click="navigate('mapping')"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
            Account Mapping
          </div>
          <div
            class="sidebar-item"
            :class="{ active: currentView === 'rates' }"
            @click="navigate('rates')"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            Exchange Rates
          </div>
        </div>
        <div class="sidebar-section">
          <div class="sidebar-label">Audit</div>
          <div
            class="sidebar-item"
            :class="{ active: currentView === 'history' }"
            @click="navigate('history')"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            History
          </div>
        </div>
        <div class="sidebar-footer">
          <div class="version">v1.0.0-phase1</div>
        </div>
      </div>

      <div class="content">
        <!-- Process CTR — placeholder (Slice 4) -->
        <div v-if="currentView === 'process'">
          <h2>Process CTR</h2>
          <p class="desc">Upload a CTR file to extract closing balances and calculate FX remeasurement.</p>
          <div class="card">
            <div class="card-body">
              <p style="color: var(--text-tertiary); text-align: center; padding: 40px 0;">
                Upload a CTR file to begin processing.
              </p>
            </div>
          </div>
        </div>

        <!-- Account Mapping — Slice 2 -->
        <AccountMapping
          v-else-if="currentView === 'mapping'"
          @count-changed="mappingCount = $event"
        />

        <!-- Exchange Rates — placeholder (Slice 3) -->
        <div v-else-if="currentView === 'rates'">
          <h2>Exchange Rates</h2>
          <p class="desc">Configure period-end exchange rates for currency remeasurement.</p>
          <div class="card">
            <div class="card-body">
              <p style="color: var(--text-tertiary); text-align: center; padding: 40px 0;">
                Upload and manage period-end exchange rates.
              </p>
            </div>
          </div>
        </div>

        <!-- Audit History — placeholder (Slice 5) -->
        <div v-else-if="currentView === 'history'">
          <h2>Audit History</h2>
          <p class="desc">Track all configuration changes for audit compliance.</p>
          <div class="card">
            <div class="card-body">
              <p style="color: var(--text-tertiary); text-align: center; padding: 40px 0;">
                View the audit trail of configuration changes.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import AccountMapping from './components/AccountMapping.vue'

export default {
  name: 'App',
  components: { AccountMapping },
  setup() {
    const currentView = ref('process')
    const mappingCount = ref(0)

    const navigate = (view) => {
      currentView.value = view
    }

    return { currentView, mappingCount, navigate }
  }
}
</script>
