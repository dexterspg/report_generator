<template>
  <div class="content">
    <h2>Config History</h2>
    <p class="desc">Audit trail of configuration changes. To rollback, navigate to the history folder and delete the most recent entry.</p>

    <div class="card">
      <div class="card-head">
        Recent Changes
        <span style="font-weight:400;color:#888">{{ entries.length }}</span>
      </div>
      <div class="card-body" style="padding:0">
        <div v-if="entries.length === 0" style="padding:16px;text-align:center;color:#aaa;font-size:12px">No history yet</div>
        <table v-else>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Config</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in entries" :key="entry.id">
              <td class="mono" style="white-space:nowrap">{{ formatTimestamp(entry.timestamp) }}</td>
              <td>{{ formatAction(entry) }}</td>
              <td>{{ formatConfigType(entry.config_type) }}</td>
              <td style="font-size:11px;color:#555">{{ formatDetails(entry) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'HistoryView',
  setup() {
    const entries = ref([])

    onMounted(async () => {
      try {
        const res = await axios.get('/history')
        entries.value = res.data.entries || []
      } catch {}
    })

    const formatTimestamp = (ts) => {
      if (!ts) return ''
      return ts.replace('T', ' ').slice(0, 16)
    }

    const formatAction = (entry) => {
      const mode = entry.details?.mode
      if (entry.action === 'upload' && mode) return `Upload (${mode.charAt(0).toUpperCase() + mode.slice(1)})`
      return entry.action.charAt(0).toUpperCase() + entry.action.slice(1)
    }

    const formatConfigType = (ct) => {
      if (ct === 'account_mapping') return 'Account Mapping'
      if (ct === 'exchange_rates') return 'Exchange Rates'
      return ct
    }

    const formatDetails = (entry) => {
      const d = entry.details || {}
      const parts = []
      if (entry.source_filename) parts.push(entry.source_filename)
      if (d.total_after !== undefined) parts.push(`${d.total_after} entries`)
      else if (d.entries_in_file !== undefined) parts.push(`${d.entries_in_file} in file`)
      if (d.warnings?.length) parts.push(`${d.warnings.length} warning(s)`)
      return parts.join(' · ')
    }

    return { entries, formatTimestamp, formatAction, formatConfigType, formatDetails }
  }
}
</script>
