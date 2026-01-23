<template>
  <div class="container">
    <AppHeader />

    <main>
      <!-- Upload Section -->
      <UploadSection
        v-if="currentView === 'upload'"
        @file-selected="handleFileSelected"
        @extract-company-codes="handleExtractCompanyCodes"
        @show-help="showHelpGuide = true"
        :selected-file="selectedFile"
        :processing-options="processingOptions"
        :company-codes="companyCodes"
        :loading-company-codes="loadingCompanyCodes"
        :selected-company-code="selectedCompanyCode"
        :report-type="reportType"
        :maturity-options="maturityOptions"
        @company-code-selected="handleCompanyCodeSelected"
        @process-file="handleProcessFile"
        @report-type-changed="handleReportTypeChanged"
        @maturity-options-changed="handleMaturityOptionsChanged"
      />

      <!-- Progress Section -->
      <ProgressSection
        v-if="currentView === 'progress'"
        :progress="progress"
        :progress-text="progressText"
      />

      <!-- Results Section -->
      <ResultsSection
        v-if="currentView === 'results'"
        :results="results"
        :job-id="currentJobId"
        :report-type="reportType"
        @process-another="resetApp"
      />

      <!-- Error Section -->
      <ErrorSection
        v-if="currentView === 'error'"
        :error-message="errorMessage"
        @retry="resetApp"
      />
    </main>

    <!-- Help Guide Modal -->
    <HelpGuide
      :is-visible="showHelpGuide"
      @close="showHelpGuide = false"
    />

    <AppFooter />
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useI18n } from 'vue-i18n'
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
import UploadSection from './components/UploadSection.vue'
import ProgressSection from './components/ProgressSection.vue'
import ResultsSection from './components/ResultsSection.vue'
import ErrorSection from './components/ErrorSection.vue'
import HelpGuide from './components/HelpGuide.vue'

export default {
  name: 'App',
  components: {
    AppHeader,
    AppFooter,
    UploadSection,
    ProgressSection,
    ResultsSection,
    ErrorSection,
    HelpGuide
  },
  setup() {
    const { t } = useI18n()
    const currentView = ref('upload')
    const selectedFile = ref(null)
    const currentJobId = ref(null)
    const pollInterval = ref(null)
    const progress = ref(0)
    const progressText = ref('')
    const results = ref(null)
    const errorMessage = ref('')
    const showHelpGuide = ref(false)

    // Report type: 'ctr' or 'maturity'
    const reportType = ref('maturity')

    // CTR Mapper options
    const processingOptions = reactive({
      headerStart: 27,
      dataStart: 28
    })

    // Maturity Analysis options
    const maturityOptions = reactive({
      reportYear: new Date().getFullYear(),
      reportMonth: new Date().getMonth() + 1,
      exchangeRate: 1.0,
      headerStart: 8,
      dataStart: 9
    })

    const companyCodes = ref([])
    const loadingCompanyCodes = ref(false)
    const selectedCompanyCode = ref('')

    const handleReportTypeChanged = (type) => {
      reportType.value = type
      // Reset company codes when switching report types
      companyCodes.value = []
      selectedCompanyCode.value = ''
    }

    const handleMaturityOptionsChanged = (options) => {
      Object.assign(maturityOptions, options)
    }

    const handleFileSelected = async (file) => {
      selectedFile.value = file
      // Reset company codes when new file is selected
      companyCodes.value = []
      selectedCompanyCode.value = ''

      // Only extract company codes for CTR report type
      if (reportType.value === 'ctr') {
        await handleExtractCompanyCodes()
      }
    }

    const handleExtractCompanyCodes = async () => {
      if (!selectedFile.value) {
        showError('Please select a file first')
        return
      }

      loadingCompanyCodes.value = true

      try {
        // Initialize XLSX library if needed
        const xlsxReady = await initializeXLSX()
        if (!xlsxReady) {
          throw new Error('Excel reading library not available')
        }

        // LOCAL DESKTOP APPROACH: Read Excel file directly in browser
        await extractCompanyCodesLocally()

      } catch (error) {
        console.error('Extract company codes error:', error)
        showError(error.response?.data?.detail || error.message || 'Failed to extract company codes')
      } finally {
        loadingCompanyCodes.value = false
      }
    }

    const extractCompanyCodesLocally = async () => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (e) => {
          try {
            const data = new Uint8Array(e.target.result)
            const workbook = XLSX.read(data, { type: 'array' })

            // Get first worksheet
            const firstSheetName = workbook.SheetNames[0]
            const worksheet = workbook.Sheets[firstSheetName]

            // Convert to JSON starting from header row (27 by default for CTR)
            const headerRow = processingOptions.headerStart - 1
            const jsonData = XLSX.utils.sheet_to_json(worksheet, {
              range: headerRow,
              header: 1
            })

            if (jsonData.length === 0) {
              throw new Error('No data found in Excel file')
            }

            // Get headers from first row
            const headers = jsonData[0]
            const companyCodeIndex = headers.findIndex(header =>
              header && header.toString().toLowerCase().includes('company code')
            )

            if (companyCodeIndex === -1) {
              throw new Error('Company Code column not found')
            }

            // Extract unique company codes from data rows
            const uniqueCodes = new Set()
            for (let i = 1; i < jsonData.length; i++) {
              const row = jsonData[i]
              const companyCode = row[companyCodeIndex]
              if (companyCode && companyCode.toString().trim()) {
                uniqueCodes.add(companyCode.toString().trim())
              }
            }

            const sortedCodes = Array.from(uniqueCodes).sort()
            companyCodes.value = sortedCodes

            if (sortedCodes.length === 1) {
              selectedCompanyCode.value = sortedCodes[0]
            }

            resolve()
          } catch (error) {
            reject(error)
          }
        }
        reader.onerror = () => reject(new Error('Failed to read Excel file'))
        reader.readAsArrayBuffer(selectedFile.value)
      })
    }

    // Add XLSX library dynamically for local Excel reading
    const loadXLSXLibrary = () => {
      if (window.XLSX) return Promise.resolve()

      return new Promise((resolve, reject) => {
        const script = document.createElement('script')
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js'
        script.onload = resolve
        script.onerror = reject
        document.head.appendChild(script)
      })
    }

    // Initialize XLSX library when needed
    const initializeXLSX = async () => {
      if (window.XLSX) return true

      try {
        await loadXLSXLibrary()
        return true
      } catch (error) {
        console.error('Failed to load XLSX library:', error)
        return false
      }
    }

    const handleCompanyCodeSelected = (companyCode) => {
      selectedCompanyCode.value = companyCode
    }

    const handleProcessFile = async (options) => {
      if (!selectedFile.value) {
        showError('Please select a file first')
        return
      }

      currentView.value = 'progress'
      updateProgress(0, t('progress.uploading'))

      try {
        const formData = new FormData()
        formData.append('file', selectedFile.value)

        let uploadEndpoint = '/upload'
        let downloadEndpoint = '/download'

        if (reportType.value === 'maturity') {
          // Maturity Analysis
          uploadEndpoint = '/upload-maturity-analysis'
          downloadEndpoint = '/download-maturity-analysis'

          formData.append('report_year', maturityOptions.reportYear)
          formData.append('report_month', maturityOptions.reportMonth)
          formData.append('exchange_rate', maturityOptions.exchangeRate)
          formData.append('input_header_start', maturityOptions.headerStart)
          formData.append('input_data_start', maturityOptions.dataStart)

        } else {
          // CTR Mapper
          processingOptions.headerStart = options.headerStart
          processingOptions.dataStart = options.dataStart

          formData.append('input_header_start', options.headerStart)
          formData.append('input_data_start', options.dataStart)
          formData.append('template_header_start', '1')
          formData.append('template_data_start', '2')

          // Add company code filter if selected
          if (selectedCompanyCode.value) {
            formData.append('company_code', selectedCompanyCode.value)
          }
        }

        updateProgress(10, t('progress.uploading'))

        const response = await axios.post(uploadEndpoint, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })

        if (!response.data.success) {
          throw new Error(response.data.message || 'Upload failed')
        }

        currentJobId.value = response.data.job_id
        updateProgress(30, t('progress.processing'))
        startStatusPolling(downloadEndpoint)

      } catch (error) {
        console.error('Process error:', error)
        showError(error.response?.data?.detail || error.message || 'Upload failed')
      }
    }

    const startStatusPolling = (downloadEndpoint) => {
      if (pollInterval.value) {
        clearInterval(pollInterval.value)
      }

      pollInterval.value = setInterval(async () => {
        try {
          const response = await axios.get(`/status/${currentJobId.value}`)
          const status = response.data

          switch (status.status) {
            case 'pending':
              updateProgress(30, t('progress.waiting'))
              break
            case 'processing':
              updateProgress(60, t('progress.processing'))
              break
            case 'completed':
              clearInterval(pollInterval.value)
              updateProgress(100, t('progress.complete'))
              // Add download endpoint to results
              status.result.downloadEndpoint = downloadEndpoint
              setTimeout(() => showResults(status), 500)
              break
            case 'failed':
              clearInterval(pollInterval.value)
              throw new Error(status.error || 'Processing failed')
            default:
              updateProgress(40, t('progress.processing'))
          }

        } catch (error) {
          clearInterval(pollInterval.value)
          console.error('Status polling error:', error)
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
      selectedFile.value = null
      currentJobId.value = null
      results.value = null
      errorMessage.value = ''
      progress.value = 0
      progressText.value = ''
      currentView.value = 'upload'
      companyCodes.value = []
      selectedCompanyCode.value = ''
      loadingCompanyCodes.value = false

      if (pollInterval.value) {
        clearInterval(pollInterval.value)
      }
    }

    // Auto-cleanup every 5 minutes
    const autoCleanup = () => {
      setInterval(async () => {
        try {
          await axios.delete('/cleanup')
        } catch (error) {
          console.log('Auto-cleanup failed:', error)
        }
      }, 5 * 60 * 1000)
    }

    onMounted(() => {
      autoCleanup()
    })

    onUnmounted(() => {
      if (pollInterval.value) {
        clearInterval(pollInterval.value)
      }
    })

    return {
      currentView,
      selectedFile,
      currentJobId,
      progress,
      progressText,
      results,
      errorMessage,
      showHelpGuide,
      reportType,
      processingOptions,
      maturityOptions,
      companyCodes,
      loadingCompanyCodes,
      selectedCompanyCode,
      handleFileSelected,
      handleExtractCompanyCodes,
      handleCompanyCodeSelected,
      handleProcessFile,
      handleReportTypeChanged,
      handleMaturityOptionsChanged,
      resetApp
    }
  }
}
</script>
