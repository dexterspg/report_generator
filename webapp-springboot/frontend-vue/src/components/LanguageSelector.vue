<template>
  <div class="language-selector">
    <label for="language-select">{{ $t('app.language') }}:</label>
    <select 
      id="language-select"
      v-model="currentLanguage" 
      @change="changeLanguage"
      class="language-select"
    >
      <option value="en">English</option>
      <option value="es">Español</option>
    </select>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

export default {
  name: 'LanguageSelector',
  setup() {
    const { locale } = useI18n()
    const currentLanguage = ref(locale.value)

    const changeLanguage = () => {
      locale.value = currentLanguage.value
      localStorage.setItem('app-language', currentLanguage.value)
    }

    onMounted(() => {
      currentLanguage.value = locale.value
    })

    return {
      currentLanguage,
      changeLanguage
    }
  }
}
</script>

<style scoped>
.language-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.language-selector label {
  color: #666;
  font-weight: 500;
}

.language-select {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  color: #333;
  cursor: pointer;
  transition: border-color 0.2s;
}

.language-select:hover {
  border-color: #009cde;
}

.language-select:focus {
  outline: none;
  border-color: #009cde;
  box-shadow: 0 0 0 2px rgba(0, 156, 222, 0.1);
}
</style>