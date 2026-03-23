<template>
  <section class="card error-card">
    <h2>Error</h2>
    <div class="error-content">
      <p><strong>Error:</strong> {{ errorMessage }}</p>
      <p>Please check that your file:</p>
      <ul>
        <li>Is a valid Excel (.xlsx, .xls) or CSV (.csv) file</li>
        <li>Contains the required CTR columns (Account Number, Contract Currency, etc.)</li>
        <li>Has headers in the correct row position</li>
        <li>Is not corrupted or password-protected</li>
      </ul>
    </div>
    <button
      class="btn btn-secondary"
      @click="$emit('retry')"
    >
      Try Again
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
