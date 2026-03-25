<template>
  <div class="content">
    <h2>Account Mapping</h2>
    <p class="desc">Maps GL accounts to type, monetary classification, and rate method.</p>

    <div class="card">
      <div class="card-head">Upload Mapping</div>
      <div class="card-body">
          <div
            class="upload-box"
            :class="{ 'has-file': uploadFile, 'drag-over': isDragging }"
            style="padding:20px"
            @click="triggerBrowse"
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @drop.prevent="onDrop"
          >
            <template v-if="!uploadFile">
              <h4>Drop file here</h4>
              <p>Cols: Account Number, Account Type, Monetary?, Rate</p>
            </template>
            <template v-else>
              <h4 style="color:#009cde">{{ uploadFile.name }}</h4>
              <p><a @click.stop="clearUpload" style="font-size:11px;cursor:pointer">Remove</a></p>
            </template>
          </div>
          <input ref="fileInput" type="file" accept=".xlsx,.xls,.csv" style="display:none" @change="onFileChange" />

          <div class="modes">
            <div class="mode" :class="{ active: uploadMode === 'replace' }" @click="uploadMode = 'replace'">Replace</div>
            <div class="mode" :class="{ active: uploadMode === 'merge' }" @click="uploadMode = 'merge'">Merge</div>
          </div>

          <div v-if="uploadError" style="margin-top:8px;color:#c1292e;font-size:11px">{{ uploadError }}</div>
        </div>
        <div class="card-foot">
          <div style="display:flex;gap:8px">
            <button class="btn-ghost btn-sm" style="color:#c1292e" @click="clearAll" :disabled="rows.length === 0">Clear All</button>
            <button class="btn btn-sm" @click="downloadMapping" :disabled="rows.length === 0">Download .xlsx</button>
          </div>
          <button class="btn btn-blue btn-sm" :disabled="!uploadFile || uploading" @click="doUpload">
            {{ uploading ? 'Uploading...' : 'Upload' }}
          </button>
        </div>
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
    const rows = ref([])
    const uploadFile = ref(null)
    const uploadMode = ref('replace')
    const uploading = ref(false)
    const isDragging = ref(false)
    const uploadError = ref('')
    const fileInput = ref(null)

    const fetchMapping = async () => {
      try {
        const res = await axios.get('/config/account-mapping')
        rows.value = res.data.mapping || []
        emit('count-changed', rows.value.length)
      } catch {}
    }

    onMounted(fetchMapping)

    const triggerBrowse = () => { if (!uploadFile.value) fileInput.value?.click() }
    const clearUpload = () => {
      uploadFile.value = null
      uploadError.value = ''
      if (fileInput.value) fileInput.value.value = ''
    }
    const onFileChange = (e) => {
      uploadFile.value = e.target.files[0] || null
      uploadError.value = ''
    }
    const onDrop = (e) => {
      isDragging.value = false
      uploadFile.value = e.dataTransfer.files[0] || null
      uploadError.value = ''
    }

    const doUpload = async () => {
      if (!uploadFile.value) return
      uploading.value = true
      uploadError.value = ''
      try {
        const form = new FormData()
        form.append('file', uploadFile.value)
        form.append('mode', uploadMode.value)
        await axios.post('/config/account-mapping', form)
        clearUpload()
        await fetchMapping()
      } catch (err) {
        uploadError.value = err.response?.data?.detail || err.message
      } finally {
        uploading.value = false
      }
    }

    const clearAll = async () => {
      if (!confirm('Clear all account mappings?')) return
      try {
        await axios.delete('/config/account-mapping')
        await fetchMapping()
      } catch {}
    }

    const downloadMapping = () => { window.location.href = '/config/account-mapping/download' }

    return { rows, uploadFile, uploadMode, uploading, isDragging, uploadError, fileInput, triggerBrowse, clearUpload, onFileChange, onDrop, doUpload, clearAll, downloadMapping }
  }
}
</script>
