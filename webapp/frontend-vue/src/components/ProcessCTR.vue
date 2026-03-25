<template>
  <div class="content">
    <h2>Process CTR</h2>
    <p class="desc">Upload a CTR file to extract closing balances and calculate FX remeasurement.</p>

    <div
      class="upload-box"
      :class="{ 'has-file': selectedFile, 'drag-over': isDragging }"
      @click="triggerBrowse"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <template v-if="!selectedFile">
        <h4>Drop your CTR file here</h4>
        <p>or browse files · .xlsx .xls .csv</p>
      </template>
      <template v-else>
        <h4 style="color:#009cde">File ready</h4>
        <p><strong>{{ selectedFile.name }}</strong> · {{ fileSizeKb }} KB</p>
        <p><a @click.stop="clearFile" style="font-size:11px;cursor:pointer">Choose different file</a></p>
      </template>
    </div>
    <input ref="fileInput" type="file" accept=".xlsx,.xls,.csv" style="display:none" @change="onFileChange" />

    <div class="readiness">
      <div class="readiness-item">
        <span class="dot" :class="mappingCount > 0 ? 'dot-ok' : 'dot-warn'"></span>
        Account Mapping
        <span style="margin-left:auto;font-size:10px;color:#888">{{ mappingCount > 0 ? mappingCount + ' accts' : 'Not set' }}</span>
      </div>
      <div class="readiness-item">
        <span class="dot" :class="ratesCount > 0 ? 'dot-ok' : 'dot-warn'"></span>
        Exchange Rates
        <span style="margin-left:auto;font-size:10px;" :style="{ color: ratesCount > 0 ? '#888' : '#d4a017' }">{{ ratesCount > 0 ? ratesCount + ' rate(s)' : 'Not set' }}</span>
      </div>
    </div>

    <div style="display:flex;justify-content:space-between;align-items:center">
      <button v-if="selectedFile" class="btn btn-sm" @click="clearFile">Clear</button>
      <span v-else></span>
      <button class="btn btn-blue" :disabled="!canProcess || uploading" @click="processFile">
        {{ uploading ? 'Uploading...' : 'Process CTR' }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import axios from 'axios'

export default {
  name: 'ProcessCTR',
  props: {
    mappingCount: { type: Number, default: 0 },
    ratesCount: { type: Number, default: 0 },
  },
  emits: ['start-processing', 'error'],
  setup(props, { emit }) {
    const selectedFile = ref(null)
    const isDragging = ref(false)
    const uploading = ref(false)
    const fileInput = ref(null)

    const fileSizeKb = computed(() =>
      selectedFile.value ? Math.round(selectedFile.value.size / 1024) : 0
    )
    const canProcess = computed(() =>
      !!selectedFile.value && props.mappingCount > 0 && props.ratesCount > 0
    )

    const triggerBrowse = () => { if (!selectedFile.value) fileInput.value?.click() }
    const clearFile = () => {
      selectedFile.value = null
      if (fileInput.value) fileInput.value.value = ''
    }
    const onFileChange = (e) => {
      const f = e.target.files[0]
      if (f) selectedFile.value = f
    }
    const onDrop = (e) => {
      isDragging.value = false
      const f = e.dataTransfer.files[0]
      if (f) selectedFile.value = f
    }

    const processFile = async () => {
      if (!selectedFile.value) return
      if (selectedFile.value.size > 50 * 1024 * 1024) {
        emit('error', 'File exceeds 50 MB limit.')
        return
      }
      uploading.value = true
      try {
        const form = new FormData()
        form.append('file', selectedFile.value)
        form.append('input_header_start', '27')
        const res = await axios.post('/upload', form)
        emit('start-processing', { jobId: res.data.job_id, filename: selectedFile.value.name })
      } catch (err) {
        emit('error', err.response?.data?.detail || err.message)
      } finally {
        uploading.value = false
      }
    }

    return { selectedFile, isDragging, uploading, fileSizeKb, canProcess, fileInput, triggerBrowse, clearFile, onFileChange, onDrop, processFile }
  }
}
</script>
