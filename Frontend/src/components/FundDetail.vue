<template>
  <div class="fund-detail">
    <!-- 基金基础信息组件 -->
    <FundBasicInfo :fundCode="currentFundCode" />
    
    <!-- 主要内容区域 -->
    <div v-if="fundDetail" class="detail-content">
      
      <!-- 中心区域：图表展示 -->
      <div class="charts-section">
        <!-- 净值走势图 (含收益对比、回撤修复) -->
        <FundChart
          :netWorthTrend="processedNetWorthTrend"
          :acWorthTrend="processedAcWorthTrend"
          :grandTotal="fundDetail.grand_total"
        />
        
        <!-- 同类排名走势 -->
        <FundRankingTrend
          :rateInSimilarType="fundDetail.rate_in_similar_type"
          :rateInSimilarPercent="fundDetail.rate_in_similar_percent"
        />
      </div>
      
      <!-- 详细信息区域 -->
      <div class="detail-sections">
        <!-- 资产配置 -->
        <FundAssetAllocation
          :assetAllocation="fundDetail.asset_allocation"
        />
        
        <!-- 基金规模变动 -->
        <FundScaleChange
          :fluctuationScale="fundDetail.fluctuation_scale"
        />
      </div>
    </div>
    
    <!-- 加载状态 -->
    <div v-else-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>正在加载基金详情...</p>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="error">
      <div class="error-icon">⚠️</div>
      <p>{{ error }}</p>
      <button @click="retry" class="retry-btn">重试</button>
    </div>
    
    <!-- 空状态 -->
    <div v-else-if="!currentFundCode" class="empty-state">
      <div class="empty-icon">📊</div>
      <p>请输入基金代码或从搜索结果中选择基金</p>
    </div>
  </div>
</template>

<script>
import { ref, watch, computed } from 'vue'
import FundBasicInfo from './FundBasicInfo.vue'
import FundChart from './FundChart.vue'
import FundRankingTrend from './FundRankingTrend.vue'
import FundAssetAllocation from './FundAssetAllocation.vue'
import FundScaleChange from './FundScaleChange.vue'
import { fundAPI } from '../services/api'

export default {
  name: 'FundDetail',
  components: {
    FundBasicInfo,
    FundChart,
    FundRankingTrend,
    FundAssetAllocation,
    FundScaleChange
  },
  props: {
    fundCode: {
      type: String,
      default: ''
    }
  },
  setup(props) {
    const currentFundCode = ref(props.fundCode)
    const fundDetail = ref(null)
    const loading = ref(false)
    const error = ref('')

    // 处理净值走势数据格式
    const processedNetWorthTrend = computed(() => {
      if (!fundDetail.value?.net_worth_trend) return []
      
      try {
        // 处理不同的数据格式
        const trend = fundDetail.value.net_worth_trend
        if (Array.isArray(trend) && trend.length > 0) {
          // 格式1: [{x: timestamp, y: value}]
          if (trend[0].x && trend[0].y) {
            return trend.map(item => ({
              x: item.x,
              y: parseFloat(item.y) || 0
            }))
          }
          // 格式2: [timestamp, value]
          else if (Array.isArray(trend[0]) && trend[0].length >= 2) {
            return trend.map(item => ({
              x: item[0],
              y: parseFloat(item[1]) || 0
            }))
          }
        }
        return []
      } catch (e) {
        console.error('处理净值走势数据错误:', e)
        return []
      }
    })

    // 处理累计净值走势数据
    const processedAcWorthTrend = computed(() => {
      if (!fundDetail.value?.ac_worth_trend) return []
      
      try {
        const trend = fundDetail.value.ac_worth_trend
        if (Array.isArray(trend) && trend.length > 0) {
          return trend.map(item => {
            if (Array.isArray(item) && item.length >= 2) {
              return [item[0], parseFloat(item[1]) || 0]
            }
            return [0, 0]
          })
        }
        return []
      } catch (e) {
        console.error('处理累计净值数据错误:', e)
        return []
      }
    })

    // 获取基金详情
    const fetchFundDetail = async (fundCode) => {
      if (!fundCode) {
        fundDetail.value = null
        return
      }

      loading.value = true
      error.value = ''
      try {
        const response = await fundAPI.getFundDetail(fundCode)
        fundDetail.value = response.data
        console.log('基金详情数据:', response.data)
      } catch (err) {
        console.error('获取基金详情失败:', err)
        error.value = err.response?.data?.error || '获取基金详情失败，请检查基金代码是否正确'
        fundDetail.value = null
      } finally {
        loading.value = false
      }
    }

    // 重试函数
    const retry = () => {
      if (currentFundCode.value) {
        fetchFundDetail(currentFundCode.value)
      }
    }

    // 监听基金代码变化
    watch(() => props.fundCode, (newCode) => {
      currentFundCode.value = newCode
      if (newCode) {
        fetchFundDetail(newCode)
      } else {
        fundDetail.value = null
        loading.value = false
        error.value = ''
      }
    }, { immediate: true })

    return {
      currentFundCode,
      fundDetail,
      loading,
      error,
      processedNetWorthTrend,
      processedAcWorthTrend,
      retry
    }
  }
}
</script>

<style scoped>
.fund-detail {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* 图表区域 */
.charts-section {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-bottom: 0;
}

/* 详细信息区域 */
.detail-sections {
  display: flex;
  flex-direction: column;
  gap: 0;
  background: #f5f5f5;
  padding: 24px;
}

/* 加载状态 */
.loading {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading p {
  font-size: 16px;
  margin-top: 16px;
}

/* 错误状态 */
.error {
  text-align: center;
  padding: 60px 40px;
  color: #d32f2f;
  background: #ffebee;
  border-radius: 12px;
  margin: 20px 0;
}

.error-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.error p {
  font-size: 16px;
  margin-bottom: 20px;
}

.retry-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.retry-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.retry-btn:active {
  transform: translateY(0);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #666;
  background: white;
  border-radius: 12px;
  margin: 20px 0;
}

.empty-icon {
  font-size: 80px;
  margin-bottom: 24px;
  opacity: 0.6;
}

.empty-state p {
  font-size: 18px;
  color: #999;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .fund-detail {
    padding: 0;
  }
  
  .detail-sections {
    padding: 16px;
  }
}

@media (max-width: 768px) {
  .fund-detail {
    padding: 0;
  }
  
  .detail-sections {
    padding: 12px;
  }
  
  .empty-state {
    padding: 60px 20px;
  }
  
  .empty-icon {
    font-size: 64px;
  }
  
  .empty-state p {
    font-size: 16px;
  }
}
</style>