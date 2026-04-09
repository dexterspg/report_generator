<template>
  <div>
    <h2>Account Mapping</h2>
    <p class="desc">Maps Account Number to Account Type, Monetary classification, and Rate method.</p>

    <div class="card">
      <!-- Card header -->
      <div class="card-head">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          Upload Mapping
        </h3>
      </div>

      <!-- Card body: upload zone + mode toggle -->
      <div class="card-body">
        <!-- Upload zone -->
        <div
          class="upload-zone"
          :class="{ 'drag-active': isDragging }"
          @click="triggerBrowse"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
        >
          <div class="upload-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>

          <template v-if="!uploadFile">
            <h3>Drop mapping file here</h3>
            <div class="upload-hint">or <span>browse files</span> to upload</div>
            <div class="col-chips">
              <span class="col-chip">Account Number</span>
              <span class="col-chip">Account Type</span>
              <span class="col-chip">Monetary?</span>
              <span class="col-chip">Rate</span>
            </div>
            <div class="size-hint">Max 50 MB &middot; .xlsx, .xls, .csv</div>
          </template>

          <template v-else>
            <h3 style="color: var(--nakisa)">{{ uploadFile.name }}</h3>
            <div class="upload-hint">
              {{ formatFileSize(uploadFile.size) }} &middot;
              <span @click.stop="clearUpload" style="cursor: pointer">Remove</span>
            </div>
          </template>
        </div>

        <input
          ref="fileInput"
          type="file"
          accept=".xlsx,.xls,.csv"
          style="display: none"
          @change="onFileChange"
        />

        <!-- Mode toggle -->
        <div class="field-label">Upload Mode</div>
        <div class="modes">
          <button
            class="mode-btn"
            :class="{ active: uploadMode === 'replace' }"
            @click="uploadMode = 'replace'"
          >Replace</button>
          <button
            class="mode-btn"
            :class="{ active: uploadMode === 'merge' }"
            @click="uploadMode = 'merge'"
          >Merge</button>
        </div>

        <!-- Error banner -->
        <div v-if="uploadError" class="upload-error">
          {{ uploadError }}
        </div>

        <!-- Success banner -->
        <div v-if="successMessage" class="upload-success">
          {{ successMessage }}
        </div>
      </div>

      <!-- Card footer: Clear All + Download (left) | Upload (right) -->
      <div class="card-foot">
        <div class="button-row">
          <button
            class="btn btn-danger btn-sm"
            :disabled="count === 0 || uploading"
            @click="clearAll"
          >Clear All</button>
          <button
            class="btn btn-secondary btn-sm"
            :disabled="count === 0"
            @click="downloadMapping"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Download .xlsx
          </button>
          <span v-if="count > 0" class="mapping-count">{{ count }} account{{ count !== 1 ? 's' : '' }}</span>
        </div>
        <button
          class="btn btn-primary btn-sm"
          :disabled="!uploadFile || uploading"
          @click="doUpload"
        >
          <svg v-if="uploading" class="spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
          </svg>
          {{ uploading ? 'Uploading...' : 'Upload' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'AccountMapping',
  emits: ['count-changed'],
  setup(_, { emit }) {
    const count = ref(0)
    const uploadFile = ref(null)
    const uploadMode = ref('replace')
    const uploading = ref(false)
    const isDragging = ref(false)
    const uploadError = ref('')
    const successMessage = ref('')
    const fileInput = ref(null)

    // ------------------------------------------------------------------
    // Fetch current count from backend
    // ------------------------------------------------------------------
    const fetchCount = async () => {
      try {
        const res = await axios.get('/config/account-mapping')
        count.value = res.data.count ?? 0
        emit('count-changed', count.value)
      } catch {
        // Silently ignore — count stays 0 on error
      }
    }

    onMounted(fetchCount)

    // ------------------------------------------------------------------
    // File selection helpers
    // ------------------------------------------------------------------
    const triggerBrowse = () => {
      if (!uploadFile.value) {
        fileInput.value?.click()
      }
    }

    const clearUpload = () => {
      uploadFile.value = null
      uploadError.value = ''
      successMessage.value = ''
      if (fileInput.value) fileInput.value.value = ''
    }

    const onFileChange = (e) => {
      const file = e.target.files[0] || null
      uploadFile.value = file
      uploadError.value = ''
      successMessage.value = ''
    }

    const onDrop = (e) => {
      isDragging.value = false
      const file = e.dataTransfer.files[0] || null
      uploadFile.value = file
      uploadError.value = ''
      successMessage.value = ''
    }

    const formatFileSize = (bytes) => {
      if (bytes < 1024) return `${bytes} B`
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    // ------------------------------------------------------------------
    // Upload
    // ------------------------------------------------------------------
    const doUpload = async () => {
      if (!uploadFile.value) return
      uploading.value = true
      uploadError.value = ''
      successMessage.value = ''
      try {
        const form = new FormData()
        form.append('file', uploadFile.value)
        form.append('mode', uploadMode.value)
        const res = await axios.post('/config/account-mapping', form)
        const { rows_processed, total_count } = res.data
        successMessage.value = uploadMode.value === 'replace'
          ? `Replaced with ${rows_processed} account${rows_processed !== 1 ? 's' : ''}.`
          : `Merged ${rows_processed} account${rows_processed !== 1 ? 's' : ''}. Total: ${total_count}.`
        clearUpload()
        await fetchCount()
      } catch (err) {
        uploadError.value = err.response?.data?.detail || err.message || 'Upload failed.'
      } finally {
        uploading.value = false
      }
    }

    // ------------------------------------------------------------------
    // Clear All
    // ------------------------------------------------------------------
    const clearAll = async () => {
      if (!confirm('Clear all account mappings? This cannot be undone.')) return
      try {
        await axios.delete('/config/account-mapping')
        uploadError.value = ''
        successMessage.value = ''
        await fetchCount()
      } catch (err) {
        uploadError.value = err.response?.data?.detail || err.message || 'Clear failed.'
      }
    }

    // ------------------------------------------------------------------
    // Download
    // ------------------------------------------------------------------
    const downloadMapping = () => {
      window.location.href = '/config/account-mapping/download'
    }

    return {
      count,
      uploadFile,
      uploadMode,
      uploading,
      isDragging,
      uploadError,
      successMessage,
      fileInput,
      triggerBrowse,
      clearUpload,
      onFileChange,
      onDrop,
      formatFileSize,
      doUpload,
      clearAll,
      downloadMapping,
    }
  }
}
</script>

<style scoped>
.drag-active {
  border-color: var(--nakisa) !important;
  box-shadow: var(--shadow-blue) !important;
}
.drag-active::before {
  opacity: 1 !important;
}

.upload-error {
  margin-top: var(--sp-4);
  padding: var(--sp-3) var(--sp-4);
  background: var(--error-bg);
  border: 1px solid #fecaca;
  border-radius: var(--r-sm);
  font-size: 13px;
  color: var(--error);
  line-height: 1.5;
}

.upload-success {
  margin-top: var(--sp-4);
  padding: var(--sp-3) var(--sp-4);
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  border-radius: var(--r-sm);
  font-size: 13px;
  color: var(--success);
  font-weight: 500;
}

.mapping-count {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: var(--sp-2);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
.spin-icon {
  animation: spin 0.9s linear infinite;
}
</style>
