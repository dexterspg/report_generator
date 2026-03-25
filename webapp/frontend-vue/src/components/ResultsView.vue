<template>
  <div class="content" style="display:flex;align-items:center;justify-content:center;min-height:400px">
    <div style="text-align:center;max-width:400px">
      <div style="font-size:48px;margin-bottom:8px">✓</div>
      <h2 style="margin-bottom:4px">Processing Complete</h2>
      <p class="desc" style="margin-bottom:20px">
        {{ result?.source_filename || 'file' }}
        <template v-if="result?.fiscal_year"> — FY {{ result.fiscal_year }} · Period {{ result.fiscal_period }}</template>
        · {{ result?.processing_time }}s
      </p>

      <div class="stats">
        <div class="stat">
          <div class="val">{{ (result?.input_rows || 0).toLocaleString() }}</div>
          <div class="lbl">Input Rows</div>
        </div>
        <div class="stat hl">
          <div class="val">{{ result?.output_rows || 0 }}</div>
          <div class="lbl">Output Rows</div>
        </div>
        <div class="stat">
          <div class="val">{{ (result?.sheets || []).length }}</div>
          <div class="lbl">Currencies</div>
        </div>
      </div>

      <div v-if="(result?.warnings || []).length > 0" style="text-align:left;margin-bottom:12px;font-size:11px;color:#d4a017;background:#fffbeb;border:1px solid #fde68a;border-radius:3px;padding:8px">
        <strong>Warnings:</strong>
        <ul style="margin-top:4px;padding-left:16px">
          <li v-for="w in result.warnings" :key="w">{{ w }}</li>
        </ul>
      </div>

      <div style="display:flex;gap:8px;justify-content:center;margin-top:16px">
        <button class="btn btn-sm" @click="$emit('new-upload')">New Upload</button>
        <button class="btn btn-blue" @click="downloadOutput">Download Output</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResultsView',
  props: {
    jobId: { type: String, required: true },
    result: { type: Object, default: () => ({}) },
  },
  emits: ['new-upload'],
  setup(props) {
    const downloadOutput = () => {
      window.location.href = `/download/${props.jobId}`
    }
    return { downloadOutput }
  }
}
</script>
