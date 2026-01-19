<template>
  <div class="language-section">
    <LanguageSelector />
  </div>
  <div class="header-container">
    <header>
      <h1>📋 {{ $t('app.title') }}</h1>
      <p>{{ $t('app.subtitle') }}</p>
    </header>
  </div>
</template>

<script>
import LanguageSelector from './LanguageSelector.vue'

export default {
  name: 'AppHeader',
  components: {
    LanguageSelector
  }
}
</script>

<style scoped>
.language-section {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10;
}

/* Match the exact container structure as upload component */
.header-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

header {
  text-align: center;
  margin-bottom: 30px;
  color: white;
  /* Remove any margin/padding that might affect centering */
  margin-left: 0;
  margin-right: 0;
  padding-left: 0;
  padding-right: 0;
}

header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
  text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
  white-space: nowrap;
  text-align: center;
  line-height: 1.2;
  /* Ensure no extra margins */
  margin-left: 0;
  margin-right: 0;
  padding-left: 0;
  padding-right: 0;
}

header p {
  font-size: 1.1rem;
  opacity: 0.9;
  text-align: center;
  /* Ensure no extra margins */
  margin-left: 0;
  margin-right: 0;
  padding-left: 0;
  padding-right: 0;
}

@media (max-width: 768px) {
  .language-section {
    position: static;
    text-align: center;
    margin-bottom: 20px;
  }
  
  .header-container {
    padding: 15px;
  }
  
  header h1 {
    font-size: 1.6rem;
    white-space: normal;
    line-height: 1.3;
  }
}

@media (max-width: 480px) {
  header h1 {
    font-size: 1.4rem;
  }
}
</style>