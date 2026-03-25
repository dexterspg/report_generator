<template>
  <div class="app-wrapper">
    <div class="topbar">
      <h1>CTR FX Remeasurement</h1>
      <span class="status">Desktop Mode</span>
    </div>
    <div class="shell">
      <nav class="sidebar">
        <div class="section-label">Process</div>
        <a :class="{ active: currentView === 'process' }" @click="navigate('process')">Process CTR</a>
        <div class="section-label">Config</div>
        <a :class="{ active: currentView === 'mapping' }" @click="navigate('mapping')">
          Account Mapping
          <span class="badge" v-if="mappingCount > 0">{{ mappingCount }}</span>
        </a>
        <a :class="{ active: currentView === 'rates' }" @click="navigate('rates')">
          Exchange Rates
          <span class="badge" v-if="ratesCount > 0">{{ ratesCount }}</span>
        </a>
        <div class="section-label">Audit</div>
        <a :class="{ active: currentView === 'history' }" @click="navigate('history')">History</a>
      </nav>
      <div style="overflow: hidden;">
        <ProcessCTR
          v-if="currentView === 'process'"
          :mapping-count="mappingCount"
          :rates-count="ratesCount"
          @start-processing="onStartProcessing"
          @error="onError"
        />
        <ProcessingView
          v-else-if="currentView === 'processing'"
          :job-id="currentJobId"
          :filename="processingFilename"
          @show-results="onShowResults"
          @error="onError"
        />
        <ResultsView
          v-else-if="currentView === 'results'"
          :job-id="currentJobId"
          :result="currentResult"
          @new-upload="navigate('process')"
        />
        <AccountMapping
          v-else-if="currentView === 'mapping'"
          @count-changed="onMappingCountChanged"
        />
        <ExchangeRates
          v-else-if="currentView === 'rates'"
          @count-changed="onRatesCountChanged"
        />
        <HistoryView
          v-else-if="currentView === 'history'"
        />
        <ErrorView
          v-else-if="currentView === 'error'"
          :message="errorMessage"
          @retry="navigate('process')"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import ProcessCTR from './components/ProcessCTR.vue'
import ProcessingView from './components/ProcessingView.vue'
import ResultsView from './components/ResultsView.vue'
import AccountMapping from './components/AccountMapping.vue'
import ExchangeRates from './components/ExchangeRates.vue'
import HistoryView from './components/HistoryView.vue'
import ErrorView from './components/ErrorView.vue'

export default {
  name: 'App',
  components: { ProcessCTR, ProcessingView, ResultsView, AccountMapping, ExchangeRates, HistoryView, ErrorView },
  setup() {
    const currentView = ref('process')
    const currentJobId = ref(null)
    const currentResult = ref(null)
    const processingFilename = ref('')
    const errorMessage = ref('')
    const mappingCount = ref(0)
    const ratesCount = ref(0)

    const fetchCounts = async () => {
      try {
        const [mRes, rRes] = await Promise.all([
          axios.get('/config/account-mapping'),
          axios.get('/config/exchange-rates'),
        ])
        mappingCount.value = mRes.data.count ?? 0
        ratesCount.value = rRes.data.count ?? 0
      } catch {}
    }

    onMounted(fetchCounts)

    const navigate = (view) => {
      currentView.value = view
    }

    const onStartProcessing = ({ jobId, filename }) => {
      currentJobId.value = jobId
      processingFilename.value = filename
      currentView.value = 'processing'
    }

    const onShowResults = (result) => {
      currentResult.value = result
      currentView.value = 'results'
    }

    const onError = (message) => {
      errorMessage.value = message
      currentView.value = 'error'
    }

    const onMappingCountChanged = (count) => { mappingCount.value = count }
    const onRatesCountChanged = (count) => { ratesCount.value = count }

    return {
      currentView, currentJobId, currentResult, processingFilename, errorMessage,
      mappingCount, ratesCount, navigate, onStartProcessing, onShowResults, onError,
      onMappingCountChanged, onRatesCountChanged,
    }
  }
}
</script>
