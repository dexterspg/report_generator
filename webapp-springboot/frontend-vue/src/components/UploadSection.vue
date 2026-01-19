<template>
  <section class="card">
    <h2>{{ $t('upload.title') }}</h2>
    
    <div 
      class="upload-area"
      :class="{ 'dragover': isDragOver, 'file-selected': selectedFile }"
      @click="triggerFileInput"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <div class="upload-content">
        <div class="upload-icon">{{ selectedFile ? '📄' : '📁' }}</div>
        <p v-if="!selectedFile">
          {{ $t('upload.dragDrop') }} <span class="browse-link">{{ $t('upload.browse') }}</span>
        </p>
        <div v-else>
          <p><strong>{{ selectedFile.name }}</strong></p>
          <p class="file-types">{{ $t('upload.sizeLabel') }} {{ formatFileSize(selectedFile.size) }}</p>
          <p class="file-success">✓ {{ $t('upload.ready') }}</p>
        </div>
        <p v-if="!selectedFile" class="file-types">{{ $t('upload.fileTypes') }}</p>
      </div>
      <input 
        ref="fileInput"
        type="file" 
        accept=".xlsx,.xls" 
        hidden 
        @change="handleFileSelect"
      >
    </div>
    <br>

    <!-- Company Code Selection -->
    <div v-if="selectedFile" class="company-code-section">
      <h3>{{ $t('upload.companyCodeFilter') || 'Company Code Filter' }}</h3>
      
      <div v-if="loadingCompanyCodes" class="loading-section">
        <p>⏳ {{ $t('upload.extracting') || 'Loading company codes...' }}</p>
      </div>

      <div v-else-if="companyCodes.length" class="dropdown-section">
        <label for="company-code-select">
          {{ $t('upload.selectCompany') || 'Select Company Code:' }}
        </label>
        <select 
          id="company-code-select"
          :value="selectedCompanyCode"
          @change="handleCompanyCodeChange"
          class="company-code-select"
        >
          <option value="">{{ $t('upload.allCompanies') || 'All Companies' }}</option>
          <option 
            v-for="code in companyCodes" 
            :key="code" 
            :value="code"
          >
            {{ code }}
          </option>
        </select>
        <p class="code-info">
          {{ $t('upload.foundCodes') || 'Found' }} {{ companyCodes.length }} 
          {{ $t('upload.companyCodes') || 'company codes' }}
        </p>
      </div>

      <div v-else class="error-section">
        <p>❌ {{ $t('upload.noCompanyCodes') || 'No Company Code column found in the file' }}</p>
      </div>
    </div>

    <!-- Advanced Options -->
    <!-- <div class="options-section">
      <h3>Processing Options</h3>
      <div class="options-grid">
        <div class="option-group">
          <label for="header-start">Header Start Row:</label>
          <input 
            id="header-start"
            v-model.number="options.headerStart"
            type="number" 
            min="1"
          >
        </div>
        <div class="option-group">
          <label for="data-start">Data Start Row:</label>
          <input 
            id="data-start"
            v-model.number="options.dataStart"
            type="number" 
            min="1"
          >
        </div>
      </div>
    </div> -->

    <div class="button-group">
      <button 
        class="btn btn-primary" 
        :disabled="!selectedFile"
        @click="processFile"
      >
        {{ $t('upload.processFile') }}
      </button>
      
      <button 
        class="btn-help" 
        @click="showHelp"
        title="Show help guide"
        aria-label="Show help guide"
      >
        <span class="help-icon">❓</span>
        {{ $t('upload.help') }}
      </button>
    </div>
  </section>
</template>

<script>
import { ref, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'

export default {
  name: 'UploadSection',
  props: {
    selectedFile: {
      type: File,
      default: null
    },
    processingOptions: {
      type: Object,
      default: () => ({ headerStart: 27, dataStart: 28 })
    },
    companyCodes: {
      type: Array,
      default: () => []
    },
    loadingCompanyCodes: {
      type: Boolean,
      default: false
    },
    selectedCompanyCode: {
      type: String,
      default: ''
    }
  },
  emits: ['file-selected', 'process-file', 'show-help', 'extract-company-codes', 'company-code-selected'],
  setup(props, { emit }) {
    const { t } = useI18n()
    const fileInput = ref(null)
    const isDragOver = ref(false)
    
    const options = reactive({
      headerStart: props.processingOptions.headerStart,
      dataStart: props.processingOptions.dataStart
    })

    // Watch for changes in processing options from parent
    watch(() => props.processingOptions, (newOptions) => {
      options.headerStart = newOptions.headerStart
      options.dataStart = newOptions.dataStart
    }, { deep: true })

    const triggerFileInput = () => {
      fileInput.value.click()
    }

    const handleDragOver = () => {
      isDragOver.value = true
    }

    const handleDragLeave = () => {
      isDragOver.value = false
    }

    const handleDrop = (e) => {
      isDragOver.value = false
      const files = e.dataTransfer.files
      if (files.length > 0) {
        handleFileSelection(files[0])
      }
    }

    const handleFileSelect = (e) => {
      const files = e.target.files
      if (files.length > 0) {
        handleFileSelection(files[0])
      }
    }

    const handleFileSelection = (file) => {
      // Validate file type
      const allowedTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
      ]
      
      if (!allowedTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls)$/i)) {
        alert(t('upload.invalidFile'))
        return
      }
      
      // Validate file size (max 50MB)
      if (file.size > 50 * 1024 * 1024) {
        alert(t('upload.fileTooLarge'))
        return
      }
      
      emit('file-selected', file)
    }

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const processFile = () => {
      emit('process-file', {
        headerStart: options.headerStart,
        dataStart: options.dataStart
      })
    }

    const showHelp = () => {
      emit('show-help')
    }

    const extractCompanyCodes = () => {
      emit('extract-company-codes')
    }

    const handleCompanyCodeChange = (event) => {
      emit('company-code-selected', event.target.value)
    }

    return {
      fileInput,
      isDragOver,
      options,
      triggerFileInput,
      handleDragOver,
      handleDragLeave,
      handleDrop,
      handleFileSelect,
      formatFileSize,
      processFile,
      showHelp,
      extractCompanyCodes,
      handleCompanyCodeChange
    }
  }
}
</script>

<style scoped>
.company-code-section {
  margin: 20px 0;
  padding: 20px;
  border: 2px dashed #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.company-code-section h3 {
  margin-top: 0;
  color: #333;
  font-size: 1.2em;
}

.extract-section {
  text-align: center;
  margin: 15px 0;
}

.extract-section p {
  margin-bottom: 10px;
  color: #666;
}

.loading-section {
  text-align: center;
  margin: 15px 0;
}

.loading-section p {
  color: #666;
  font-style: italic;
}

.dropdown-section {
  margin: 15px 0;
}

.dropdown-section label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #333;
}

.company-code-select {
  width: 100%;
  padding: 10px 12px;
  font-size: 16px;
  border: 2px solid #ddd;
  border-radius: 4px;
  background-color: white;
  box-sizing: border-box;
  margin-bottom: 10px;
}

.company-code-select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.code-info {
  font-size: 0.9em;
  color: #666;
  margin: 0;
  font-style: italic;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
  border: 2px solid #6c757d;
  padding: 12px 24px;
  font-size: 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #545b62;
  border-color: #545b62;
}

.btn-secondary:disabled {
  background-color: #ccc;
  border-color: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
}

.error-section {
  text-align: center;
  margin: 15px 0;
  padding: 15px;
  background-color: #fee;
  border: 1px solid #fcc;
  border-radius: 4px;
}

.error-section p {
  color: #c33;
  margin: 0;
  font-weight: 500;
}

.btn-link {
  background: none;
  border: none;
  color: #007bff;
  text-decoration: none;
  cursor: pointer;
  font-size: 0.9em;
  padding: 5px;
  margin-top: 10px;
  transition: color 0.2s ease;
}

.btn-link:hover:not(:disabled) {
  color: #0056b3;
  text-decoration: underline;
}

.btn-link:disabled {
  color: #ccc;
  cursor: not-allowed;
}
</style>