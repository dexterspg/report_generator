<template>
  <div class="header-container">
    <header>
      <h1>CTR FX Remeasurement</h1>
      <p>Consolidated Transaction Report — FX Gain/Loss Calculator</p>
    </header>
  </div>
</template>

<script>
export default {
  name: 'AppHeader'
}
</script>

<style scoped>
.header-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

header {
  text-align: center;
  margin-bottom: 30px;
  color: white;
}

header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
  text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
  white-space: nowrap;
  text-align: center;
  line-height: 1.2;
}

header p {
  font-size: 1.1rem;
  opacity: 0.9;
  text-align: center;
}

@media (max-width: 768px) {
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
