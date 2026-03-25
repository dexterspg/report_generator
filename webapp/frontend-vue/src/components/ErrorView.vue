<template>
  <div class="content" style="display:flex;align-items:center;justify-content:center;min-height:400px">
    <div style="max-width:440px">
      <div class="error-box">
        <h3>Processing Failed</h3>
        <div class="error-msg">{{ message }}</div>
        <p style="font-size:12px;color:#666;margin-bottom:8px">Check your file:</p>
        <ul class="checklist">
          <li>Valid Excel or CSV format</li>
          <li>Required CTR columns present</li>
          <li>Headers at expected row (default: 27)</li>
          <li>Not corrupted or password-protected</li>
        </ul>
        <div style="margin-top:16px">
          <button class="btn btn-blue" @click="$emit('retry')">Try Again</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ErrorView',
  props: { message: { type: String, default: 'An unexpected error occurred.' } },
  emits: ['retry'],
}
</script>
