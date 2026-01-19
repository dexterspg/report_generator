# CTR Mapper Spring Boot - Vue.js Frontend Reference

## Project Structure

```
frontend-vue/
├── package.json              # NPM dependencies
├── vite.config.js            # Vite configuration with proxy
├── index.html                # HTML entry point
└── src/
    ├── main.js               # Vue app initialization
    ├── App.vue               # Root component
    ├── assets/
    │   └── styles.css        # Global styles
    ├── components/
    │   ├── AppHeader.vue     # Header with language selector
    │   ├── AppFooter.vue     # Footer
    │   ├── UploadSection.vue # File upload UI
    │   ├── ProgressSection.vue # Processing progress
    │   ├── ResultsSection.vue  # Download results
    │   ├── ErrorSection.vue    # Error display
    │   ├── HelpGuide.vue       # Help modal
    │   └── LanguageSelector.vue # EN/ES toggle
    └── i18n/
        ├── index.js          # vue-i18n configuration
        └── locales/
            ├── en.json       # English translations
            └── es.json       # Spanish translations
```

---

## 1. package.json

```json
{
  "name": "ctr-mapper-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.6.0",
    "vue": "^3.3.8",
    "vue-i18n": "^9.8.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.5.0",
    "vite": "^5.0.0"
  }
}
```

---

## 2. vite.config.js (Proxy Configuration)

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3001,  // Different from Python version (3000)
    proxy: {
      '/upload': 'http://localhost:8080',
      '/status': 'http://localhost:8080',
      '/download': 'http://localhost:8080',
      '/health': 'http://localhost:8080',
      '/cleanup': 'http://localhost:8080',
      '/extract-company-codes': 'http://localhost:8080',
      '/docs': 'http://localhost:8080'
    }
  },
  build: {
    outDir: '../frontend-dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        assetFileNames: 'assets/[name].[hash].[ext]',
        chunkFileNames: 'assets/[name].[hash].js',
        entryFileNames: 'assets/[name].[hash].js'
      }
    }
  }
})
```

---

## 3. main.js (Vue App Initialization)

```javascript
import { createApp } from 'vue'
import App from './App.vue'
import i18n from './i18n'
import './assets/styles.css'

const app = createApp(App)
app.use(i18n)
app.mount('#app')
```

---

## 4. i18n/index.js (Internationalization)

```javascript
import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import es from './locales/es.json'

const messages = {
  en,
  es
}

const i18n = createI18n({
  locale: localStorage.getItem('app-language') || 'en',
  fallbackLocale: 'en',
  messages,
  legacy: false,
  globalInjection: true
})

export default i18n
```

---

## 5. App.vue (Root Component - Key Parts)

```vue
<template>
  <div class="container">
    <AppHeader />

    <main>
      <!-- Upload Section -->
      <UploadSection
        v-if="currentView === 'upload'"
        @file-selected="handleFileSelected"
        @process-file="handleProcessFile"
        :selected-file="selectedFile"
        :company-codes="companyCodes"
        :selected-company-code="selectedCompanyCode"
        @company-code-selected="handleCompanyCodeSelected"
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
        @process-another="resetApp"
      />

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
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useI18n } from 'vue-i18n'

export default {
  name: 'App',
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

    // Handle file upload and start processing
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
        formData.append('input_header_start', options.headerStart)
        formData.append('input_data_start', options.dataStart)

        if (selectedCompanyCode.value) {
          formData.append('company_code', selectedCompanyCode.value)
        }

        // POST to /upload endpoint
        const response = await axios.post('/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        if (!response.data.success) {
          throw new Error(response.data.message || 'Upload failed')
        }

        // IMPORTANT: Backend returns job_id (snake_case)
        currentJobId.value = response.data.job_id
        updateProgress(30, t('progress.processing'))
        startStatusPolling()

      } catch (error) {
        showError(error.response?.data?.detail || error.message)
      }
    }

    // Poll status endpoint until complete
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
              updateProgress(30, t('progress.waiting'))
              break
            case 'processing':
              updateProgress(60, t('progress.processing'))
              break
            case 'completed':
              clearInterval(pollInterval.value)
              updateProgress(100, t('progress.complete'))
              setTimeout(() => showResults(status), 500)
              break
            case 'failed':
              clearInterval(pollInterval.value)
              throw new Error(status.error || 'Processing failed')
          }

        } catch (error) {
          clearInterval(pollInterval.value)
          showError(error.response?.data?.detail || error.message)
        }
      }, 1000)  // Poll every 1 second
    }

    // ... other methods

    return {
      currentView,
      selectedFile,
      currentJobId,
      progress,
      progressText,
      results,
      errorMessage,
      handleProcessFile,
      resetApp
    }
  }
}
</script>
```

---

## 6. ResultsSection.vue (Download Component)

```vue
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
    </div>

    <!-- Download link -->
    <div class="download-section">
      <a :href="downloadUrl" class="btn btn-download" download>
        {{ $t('results.downloadButton') }}
      </a>
    </div>

    <button class="btn btn-secondary" @click="$emit('process-another')">
      {{ $t('results.processAnother') }}
    </button>
  </section>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'ResultsSection',
  props: {
    results: { type: Object, default: null },
    jobId: { type: String, required: true }
  },
  emits: ['process-another'],
  setup(props) {
    const processingTime = computed(() => {
      const time = props.results?.processing_time
      return time ? `${time.toFixed(2)}s` : 'N/A'
    })

    // Download URL uses job_id
    const downloadUrl = computed(() => {
      return `/download/${props.jobId}`
    })

    return { processingTime, downloadUrl }
  }
}
</script>
```

---

## 7. en.json (Translations Sample)

```json
{
  "app": {
    "title": "CTR Mapper - Spring Boot",
    "subtitle": "Excel Consolidation Report Mapper",
    "language": "Language"
  },
  "upload": {
    "title": "Upload Excel File",
    "dragDrop": "Drag & drop your Excel file here or",
    "browse": "Browse Files",
    "fileTypes": "Supported formats: .xlsx, .xls (max 50MB)",
    "ready": "Ready to process",
    "processFile": "Process File"
  },
  "progress": {
    "title": "Processing File",
    "uploading": "Uploading file...",
    "waiting": "Waiting to process...",
    "processing": "Processing data...",
    "complete": "Complete!"
  },
  "results": {
    "title": "Processing Complete",
    "complete": "Your file has been processed successfully!",
    "inputRows": "Input Rows",
    "outputRows": "Output Rows",
    "processingTime": "Processing Time",
    "downloadButton": "Download Excel File",
    "processAnother": "Process Another File"
  },
  "error": {
    "title": "Processing Error",
    "retry": "Try Again"
  }
}
```

---

## Key Concepts Demonstrated

1. **Vue 3 Composition API** - `setup()` function with `ref()` and `reactive()`
2. **vue-i18n** - Internationalization with `useI18n()` and `$t()` template helper
3. **Axios** - HTTP client for API calls
4. **Vite Proxy** - Development proxy to backend API
5. **Component Communication** - Props down, events up (`emit`)
6. **Reactive State** - `ref()` for primitives, `reactive()` for objects
7. **Computed Properties** - `computed()` for derived values
8. **Lifecycle Hooks** - `onMounted()`, `onUnmounted()`
9. **Conditional Rendering** - `v-if` for view switching
10. **Event Handling** - `@click`, `@change`, `@file-selected`

---

## Frontend-Backend Communication Flow

```
1. User selects file → handleFileSelected()
   ↓
2. User clicks "Process" → handleProcessFile()
   ↓
3. POST /upload with FormData
   → Backend returns { success: true, job_id: "abc-123" }
   ↓
4. startStatusPolling() every 1 second
   GET /status/abc-123
   ↓
5. When status = "completed":
   → Show results view
   → Download link: /download/abc-123
```

---

## Critical Bug Fix: JSON Field Naming

**Problem:** Frontend expected `job_id` but Java returned `jobId`

```javascript
// Frontend code looking for job_id (snake_case)
currentJobId.value = response.data.job_id  // Was undefined!
```

**Solution:** Add `@JsonProperty` annotations in Java models:

```java
@JsonProperty("job_id")
private String jobId;
```

This ensures the JSON output uses snake_case to match what the frontend expects.
