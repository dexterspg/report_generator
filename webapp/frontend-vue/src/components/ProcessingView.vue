<template>
  <div class="content" style="display:flex;align-items:center;justify-content:center;min-height:400px">
    <div style="text-align:center;max-width:360px">
      <h3>Processing {{ filename }}</h3>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <p style="font-size:12px;color:#666;margin-bottom:16px">{{ progress }}% — {{ progressText }}</p>
      <ol class="steps">
        <li v-for="(step, i) in steps" :key="i" :class="stepClass(i)">
          <span v-if="i < currentStep">✓</span>
          <span v-else-if="i === currentStep">●</span>
          <span v-else>{{ i + 1 }}.</span>
          {{ step.label }}
          <span v-if="i === 1 && i < currentStep && fiscalInfo" style="color:#888;font-size:11px">({{ fiscalInfo }})</span>
        </li>
      </ol>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

export default {
  name: 'ProcessingView',
  props: {
    jobId: { type: String, required: true },
    filename: { type: String, default: '' },
  },
  emits: ['show-results', 'error'],
  setup(props, { emit }) {
    const progress = ref(20)
    const progressText = ref('Validating file...')
    const currentStep = ref(0)
    const fiscalInfo = ref('')
    let pollTimer = null

    const steps = [
      { label: 'File validated' },
      { label: 'Metadata extracted' },
      { label: 'Aggregating by GL account' },
      { label: 'Applying FX remeasurement' },
      { label: 'Writing output workbook' },
    ]

    const stepClass = (i) => {
      if (i < currentStep.value) return 'done'
      if (i === currentStep.value) return 'active'
      return 'pending'
    }

    const poll = async () => {
      try {
        const res = await axios.get(`/status/${props.jobId}`)
        const status = res.data
        switch (status.status) {
          case 'pending':
            progress.value = 30
            progressText.value = 'Waiting for processing...'
            currentStep.value = 1
            break
          case 'processing':
            progress.value = 70
            progressText.value = 'Aggregating balances...'
            currentStep.value = 3
            if (status.result?.fiscal_year) {
              fiscalInfo.value = `FY ${status.result.fiscal_year}, P${status.result.fiscal_period}`
            }
            break
          case 'completed':
            clearInterval(pollTimer)
            progress.value = 100
            progressText.value = 'Complete'
            currentStep.value = 5
            if (status.result?.fiscal_year) {
              fiscalInfo.value = `FY ${status.result.fiscal_year}, P${status.result.fiscal_period}`
            }
            setTimeout(() => emit('show-results', status.result), 500)
            break
          case 'failed':
            clearInterval(pollTimer)
            emit('error', status.error || 'Processing failed')
            break
        }
      } catch (err) {
        clearInterval(pollTimer)
        emit('error', err.response?.data?.detail || err.message)
      }
    }

    onMounted(() => {
      pollTimer = setInterval(poll, 1000)
    })
    onUnmounted(() => clearInterval(pollTimer))

    return { progress, progressText, currentStep, fiscalInfo, steps, stepClass }
  }
}
</script>
