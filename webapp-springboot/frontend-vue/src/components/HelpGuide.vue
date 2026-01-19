<template>
  <div class="help-overlay" v-if="isVisible" @click="closeOnOverlayClick">
    <div class="help-modal" @click.stop>
      <div class="help-header">
        <h2>📖 {{ $t('help.title') }}</h2>
        <button class="close-btn" @click="closeHelp" aria-label="Close help">
          ✕
        </button>
      </div>
      
      <div class="help-content">
        <section class="help-section">
          <h3>🎯 {{ $t('help.whatItDoes') }}</h3>
          <p>{{ $t('help.whatItDoesText') }}</p>
        </section>

        <section class="help-section">
          <h3>📋 {{ $t('help.stepByStep') }}</h3>
          <ol class="help-steps">
            <li>
              <strong>{{ $t('help.selectFile') }}</strong>
              <p>{{ $t('help.selectFileText') }}</p>
            </li>
            <li>
              <strong>{{ $t('help.processFile') }}</strong>
              <p>{{ $t('help.processFileText') }}</p>
            </li>
            <li>
              <strong>{{ $t('help.downloadResults') }}</strong>
              <p>{{ $t('help.downloadResultsText') }}</p>
            </li>
          </ol>
        </section>

        <section class="help-section">
          <h3>📄 {{ $t('help.fileRequirements') }}</h3>
          <div class="requirements">
            <div class="requirement-item">
              <strong>✅ {{ $t('help.supportedFormats') }}</strong> {{ $t('help.supportedFormatsText') }}
            </div>
            <div class="requirement-item">
              <strong>📊 {{ $t('help.expectedStructure') }}</strong> {{ $t('help.expectedStructureText') }}
            </div>
            <div class="requirement-item">
              <strong>📐 {{ $t('help.sizeLimit') }}</strong> {{ $t('help.sizeLimitText') }}
            </div>
          </div>
        </section>

        <section class="help-section">
          <h3>📊 {{ $t('help.expectedFileStructure') }}</h3>
          <div class="tips">
            <div class="tip-item">
              <strong>📍 {{ $t('help.headerRow') }}</strong> {{ $t('help.headerRowText') }}
            </div>
            <div class="tip-item">
              <strong>📊 {{ $t('help.dataRows') }}</strong> {{ $t('help.dataRowsText') }}
            </div>
            <div class="tip-item">
              <strong>🔢 {{ $t('help.format') }}</strong> {{ $t('help.formatText') }}
            </div>
          </div>
        </section>

        <section class="help-section">
          <h3>🔧 {{ $t('help.commonIssues') }}</h3>
          <div class="troubleshooting">
            <div class="issue-item">
              <strong>❌ {{ $t('help.noData') }}</strong>
              <p>{{ $t('help.noDataText') }}</p>
            </div>
            <div class="issue-item">
              <strong>❌ {{ $t('help.invalidFormat') }}</strong>
              <p>{{ $t('help.invalidFormatText') }}</p>
            </div>
            <div class="issue-item">
              <strong>❌ {{ $t('help.processingFailedTitle') }}</strong>
              <p>{{ $t('help.processingFailedText') }}</p>
            </div>
          </div>
        </section>

        <section class="help-section">
          <h3>💡 {{ $t('help.example') }}</h3>
          <div class="example">
            <p><strong>{{ $t('help.exampleText') }}</strong></p>
            <div class="example-table">
              <div class="example-row header">{{ $t('help.exampleRow26') }}</div>
              <div class="example-row header">{{ $t('help.exampleRow27') }}</div>
              <div class="example-row">{{ $t('help.exampleRow28') }}</div>
              <div class="example-row">{{ $t('help.exampleRow29') }}</div>
            </div>
            <p><strong>{{ $t('help.structureRecognized') }}</strong> {{ $t('help.structureRecognizedText') }}</p>
          </div>
        </section>

        <section class="help-section">
          <h3>🆘 {{ $t('help.needMoreHelp') }}</h3>
          <p>{{ $t('help.needMoreHelpText') }}</p>
        </section>
      </div>
      
      <div class="help-footer">
        <button class="btn btn-primary" @click="closeHelp">{{ $t('help.gotIt') }}</button>
      </div>
    
    </div>
  </div>
</template>

<script>
export default {
  name: 'HelpGuide',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close'],
  methods: {
    closeHelp() {
      this.$emit('close')
    },
    closeOnOverlayClick(event) {
      if (event.target === event.currentTarget) {
        this.closeHelp()
      }
    }
  }
}
</script>

<style scoped>
.help-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 20px;
}

.help-modal {
  background: white;
  border-radius: 12px;
  max-width: 800px;
  max-height: 90vh;
  width: 100%;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: #009cde;
  color: white;
}

.help-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.help-content {
  padding: 0 30px 20px;
  max-height: calc(95vh - 140px);
  overflow-y: auto;
  overflow-x: visible;
}

.help-section {
  margin-bottom: 25px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.help-section:last-of-type {
  border-bottom: none;
}

.help-section h3 {
  color: #4a5568;
  margin-bottom: 12px;
  font-size: 1.2rem;
  font-weight: 600;
}

.help-section p {
  color: #666;
  line-height: 1.6;
  margin-bottom: 10px;
}

.help-steps {
  list-style: none;
  padding: 0;
  counter-reset: step-counter;
}

.help-steps li {
  counter-increment: step-counter;
  margin-bottom: 15px;
  padding-left: 40px;
  position: relative;
}

.help-steps li:before {
  content: counter(step-counter);
  position: absolute;
  left: 0;
  top: 0;
  background: #667eea;
  color: white;
  width: 25px;
  height: 25px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
}

.help-steps li ul {
  margin-top: 8px;
  padding-left: 20px;
}

.help-steps li ul li {
  counter-increment: none;
  margin-bottom: 5px;
}

.help-steps li ul li:before {
  content: "•";
  background: none;
  color: #667eea;
  width: auto;
  height: auto;
  border-radius: 0;
  left: -15px;
  top: 2px;
}

.requirements, .tips, .troubleshooting {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.requirement-item, .tip-item, .issue-item {
  padding: 12px 16px;
  background: #f7fafc;
  border-left: 4px solid #667eea;
  border-radius: 4px;
}

.issue-item {
  border-left-color: #e53e3e;
  background: #fed7d7;
}

.example {
  background: #f0f4f8;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #38b2ac;
}

.example-table {
  margin: 15px 0;
  font-family: monospace;
  font-size: 14px;
  width: 100%;
  display: block;
  clear: both;
}

.example-row {
  padding: 8px 12px;
  margin: 4px 0;
  background: white;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  display: block;
  width: 100%;
  min-height: 20px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
  text-overflow: clip;
  overflow: visible;
}

.example-row.header {
  background: #e2e8f0;
  font-weight: bold;
  color: #2d3748;
}

.help-footer {
  padding: 10px 30px 40px 30px;
  background: #f7fafc;
  text-align: center;
  border-top: 1px solid #eee;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

@media (max-width: 768px) {
  .help-modal {
    margin: 10px;
    max-height: 95vh;
  }
  
  .help-header, .help-content, .help-footer {
    padding-left: 20px;
    padding-right: 20px;
  }
  
  .help-header h2 {
    font-size: 1.3rem;
  }
  
  .help-steps li {
    padding-left: 35px;
  }
}
</style>