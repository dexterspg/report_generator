<template>
  <div class="container">
    <AppHeader />

    <main>
      <!-- Upload Section (placeholder — FX Remeasurement UI to be implemented) -->
      <div v-if="currentView === 'upload'" class="card">
        <p>Upload section coming soon.</p>
      </div>

      <!-- Progress Section -->
      <ProgressSection
        v-if="currentView === 'progress'"
        :progress="progress"
        :progress-text="progressText"
      />

      <!-- Results Section (placeholder — FX Remeasurement UI to be implemented) -->
      <div v-if="currentView === 'results'" class="card">
        <p>Results section coming soon.</p>
      </div>

      <!-- Error Section -->
      <ErrorSection
        v-if="currentView === 'error'"
        :error-message="errorMessage"
        @retry="resetApp"
      />
    </main>

    <AppFooter />
  </div>
</template>

<script>
import { ref, onUnmounted } from 'vue'
import axios from 'axios'
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
import ProgressSection from './components/ProgressSection.vue'
import ErrorSection from './components/ErrorSection.vue'

export default {
  name: 'App',
  components: {
    AppHeader,
    AppFooter,
    ProgressSection,
    ErrorSection
  },
  setup() {
    const currentView = ref('upload')
    const currentJobId = ref(null)
    const pollInterval = ref(null)
    const progress = ref(0)
    const progressText = ref('')
    const results = ref(null)
    const errorMessage = ref('')

    const startStatusPolling = () => {
      if (pollInterval.value) {
        clearInterval(pollInterval.value)
      }

      pollInterval.value = setInterval(async () => {
        try {
          const response = await axios.get(`/status/${currentJobId.value}`)
          const status = response.data

          switch (status.status) {
            case 'pending':
              updateProgress(30, 'Waiting...')
              break
            case 'processing':
              updateProgress(60, 'Processing...')
              break
            case 'completed':
              clearInterval(pollInterval.value)
              updateProgress(100, 'Complete')
              setTimeout(() => showResults(status), 500)
              break
            case 'failed':
              clearInterval(pollInterval.value)
              throw new Error(status.error || 'Processing failed')
            default:
              updateProgress(40, 'Processing...')
          }
        } catch (error) {
          clearInterval(pollInterval.value)
          showError(error.response?.data?.detail || error.message)
        }
      }, 1000)
    }

    const updateProgress = (percentage, text) => {
      progress.value = percentage
      progressText.value = text
    }

    const showResults = (status) => {
      results.value = status.result
      currentView.value = 'results'
    }

    const showError = (message) => {
      errorMessage.value = message
      currentView.value = 'error'
      if (pollInterval.value) {
        clearInterval(pollInterval.value)
      }
    }

    const resetApp = () => {
      currentJobId.value = null
      results.value = null
      errorMessage.value = ''
      progress.value = 0
      progressText.value = ''
      currentView.value = 'upload'
      if (pollInterval.value) {
        clearInterval(pollInterval.value)
      }
    }

    onUnmounted(() => {
      if (pollInterval.value) {
        clearInterval(pollInterval.value)
      }
    })

    return {
      currentView,
      currentJobId,
      progress,
      progressText,
      results,
      errorMessage,
      startStatusPolling,
      showResults,
      showError,
      resetApp
    }
  }
}
</script>
