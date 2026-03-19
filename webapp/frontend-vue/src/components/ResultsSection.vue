<template>
  <section class="card">
    <h2>{{ $t('results.title') }}</h2>
    
    <div class="results-grid">
      <div class="result-item">
        <h4>{{ $t('results.inputRows') }}</h4>
        <div class="value">{{ results?.input_rows || 0 }}</div>
      </div>
      <div class="result-item">
        <h4>{{ $t('results.outputRows') }}</h4>
        <div class="value">{{ results?.output_rows || 0 }}</div>
      </div>
      <div class="result-item">
        <h4>{{ $t('results.processingTime') }}</h4>
        <div class="value">{{ processingTime }}</div>
      </div>
      <div class="result-item">
        <h4>{{ $t('results.fileSize') }}</h4>
        <div class="value">{{ fileSize }}</div>
      </div>
    </div>
    
    <!-- Show company codes included in ZIP -->
    <div v-if="results?.company_codes && results.company_codes.length > 0" class="company-codes-info">
      <div class="codes-header">
        <span class="codes-label">{{ $t('results.companyCodes') || 'Company Codes in ZIP:' }}</span>
        <span class="codes-count">{{ results.file_count || results.company_codes.length }} {{ $t('results.files') || 'files' }}</span>
      </div>
      <div class="codes-list">
        <span v-for="code in results.company_codes" :key="code" class="code-badge">
          {{ code }}
        </span>
      </div>
    </div>

    <!-- Show company code filter information if applicable (kept for future use) -->
    <div v-if="results?.filtered_by_company_code" class="filter-info">
      <div class="filter-badge">
        <span class="filter-label">{{ $t('results.filteredBy') || 'Filtered by Company Code:' }}</span>
        <span class="filter-value">{{ results.filtered_by_company_code }}</span>
      </div>
      <p class="filter-details">
        {{ $t('results.filteredInfo') || 'Processed' }} {{ results.input_rows }} {{ $t('results.of') || 'of' }} {{ results.original_rows }} {{ $t('results.totalRows') || 'total rows' }}
      </p>
    </div>

    <div class="download-section">
      <h3>{{ $t('results.complete') }}</h3>
      <p>{{ results?.zip_file ? ($t('results.readyDownloadZip') || 'Your ZIP file is ready for download') : ($t('results.readyDownload') || 'Your file is ready for download') }}</p>
      <br>
      <a
        :href="downloadUrl"
        class="btn btn-download"
        download
      >
        {{ results?.zip_file ? ($t('results.downloadZip') || 'Download ZIP') : ($t('results.downloadButton') || 'Download') }}
      </a>
    </div>
    
    <div style="text-align: center; margin-top: 20px;">
      <button 
        class="btn btn-secondary" 
        @click="$emit('process-another')"
      >
        {{ $t('results.processAnother') }}
      </button>
    </div>
  </section>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'ResultsSection',
  props: {
    results: {
      type: Object,
      default: null
    },
    jobId: {
      type: String,
      required: true
    }
  },
  emits: ['process-another'],
  setup(props) {
    const processingTime = computed(() => {
      const time = props.results?.processing_time
      return time ? `${time.toFixed(2)}s` : 'N/A'
    })

    const fileSize = computed(() => {
      // Use zip_size if available, otherwise fall back to file_size
      const size = props.results?.zip_size || props.results?.file_size
      if (!size) return 'N/A'

      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(size) / Math.log(k))
      return parseFloat((size / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    })

    const downloadUrl = computed(() => {
      return `/download/${props.jobId}`
    })

    return {
      processingTime,
      fileSize,
      downloadUrl
    }
  }
}
</script>

<style scoped>
.filter-info {
  margin: 20px 0;
  padding: 15px;
  background-color: #e3f2fd;
  border-radius: 8px;
  border: 1px solid #90caf9;
}

.filter-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.filter-label {
  font-weight: 600;
  color: #1565c0;
}

.filter-value {
  background-color: #1976d2;
  color: white;
  padding: 4px 12px;
  border-radius: 16px;
  font-weight: 500;
}

.filter-details {
  margin: 0;
  color: #0d47a1;
  font-size: 0.95em;
}

.company-codes-info {
  margin: 20px 0;
  padding: 15px;
  background-color: #e8f5e9;
  border-radius: 8px;
  border: 1px solid #a5d6a7;
}

.codes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.codes-label {
  font-weight: 600;
  color: #2e7d32;
}

.codes-count {
  background-color: #43a047;
  color: white;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.9em;
  font-weight: 500;
}

.codes-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.code-badge {
  background-color: #81c784;
  color: #1b5e20;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: 500;
}
</style>