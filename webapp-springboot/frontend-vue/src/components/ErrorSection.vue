<template>
  <section class="card error-card">
    <h2>{{ $t('error.title') }}</h2>
    <div class="error-content">
      <p><strong>{{ $t('error.errorLabel') }}</strong> {{ errorMessage }}</p>
      <p>{{ $t('error.checkFile') }}</p>
      <ul>
        <li>{{ $t('error.validExcel') }}</li>
        <li>{{ $t('error.requiredColumns') }}</li>
        <li>{{ $t('error.correctRows') }}</li>
        <li>{{ $t('error.notCorrupted') }}</li>
      </ul>
    </div>
    <button 
      class="btn btn-secondary" 
      @click="$emit('retry')"
    >
      {{ $t('error.retry') }}
    </button>
  </section>
</template>

<script>
export default {
  name: 'ErrorSection',
  props: {
    errorMessage: {
      type: String,
      required: true
    }
  },
  emits: ['retry']
}
</script>