<template>
  <section class="card">
    <h2>{{ $t('progress.title') }}</h2>
    <div class="progress-container">
      <div class="progress-bar">
        <div 
          class="progress-fill" 
          :style="{ width: `${progress}%` }"
        ></div>
      </div>
      <p class="progress-text">{{ progressText }}</p>
    </div>
    <div class="spinner">
      <div class="spinner-ring"></div>
    </div>
  </section>
</template>

<script>
export default {
  name: 'ProgressSection',
  props: {
    progress: {
      type: Number,
      default: 0
    },
    progressText: {
      type: String,
      default: 'Processing...'
    }
  }
}
</script>