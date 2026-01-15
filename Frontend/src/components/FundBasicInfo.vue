<template>
  <div v-if="fundInfo" class="fund-basic-info">
    <div class="info-header">
      <h2>{{ fundInfo.name || fundInfo.fund_name || '未知基金' }}</h2>
      <span class="fund-code">{{ fundCode }}</span>
    </div>
    
    <div class="info-grid">
      <div class="info-item">
        <label>基金类型:</label>
        <span>{{ fundInfo.fund_type || '--' }}</span>
      </div>
      <div class="info-item">
        <label>英文名称:</label>
        <span>{{ fundInfo.fund_name_en || '--' }}</span>
      </div>
    </div>
    
    <div v-if="loading" class="loading">加载中...</div>
  </div>
</template>

<script>
import { fundAPI } from '../services/api'

export default {
  name: 'FundBasicInfo',
  props: {
    fundCode: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      fundInfo: null,
      loading: false
    }
  },
  watch: {
    fundCode: {
      immediate: true,
      handler(newCode) {
        if (newCode) {
          this.fetchFundInfo()
        }
      }
    }
  },
  methods: {
    async fetchFundInfo() {
      this.loading = true
      try {
        const response = await fundAPI.getFundBasicInfo(this.fundCode)
        this.fundInfo = response.data
      } catch (error) {
        console.error('获取基金信息失败:', error)
        this.fundInfo = null
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.fund-basic-info {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}

.info-header {
  display: flex;
  justify-content: between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.info-header h2 {
  margin: 0;
  color: #333;
}

.fund-code {
  background: #007bff;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 14px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-item label {
  font-weight: bold;
  color: #666;
  margin-bottom: 5px;
}

.info-item span {
  color: #333;
}

.loading {
  text-align: center;
  padding: 20px;
  color: #666;
}
</style>