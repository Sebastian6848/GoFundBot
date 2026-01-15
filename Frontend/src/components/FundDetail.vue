<template>
  <div class="fund-detail">
    <!-- 基金基础信息组件 -->
    <FundBasicInfo :fundCode="currentFundCode" />
    
    <!-- 主要内容区域 -->
    <div v-if="fundDetail" class="detail-content">
      <!-- 净值走势图 -->
      <FundChart
        :netWorthTrend="processedNetWorthTrend"
        :acWorthTrend="processedAcWorthTrend"
      />
      
      <!-- 详细信息展示 -->
      <div class="detail-sections">
        <!-- 持仓股票信息 -->
        <div class="section">
          <h3>持仓股票</h3>
          <div v-if="fundDetail.stock_codes && fundDetail.stock_codes.length > 0" class="stock-list">
            <span v-for="(stock, index) in fundDetail.stock_codes.slice(0, 10)" :key="index" class="stock-tag">
              {{ stock }}
            </span>
            <div v-if="fundDetail.stock_codes.length > 10" class="more-stocks">
              等 {{ fundDetail.stock_codes.length }} 只股票
            </div>
          </div>
          <div v-else class="no-data">暂无持仓数据</div>
        </div>
        
        <!-- 基础信息展示 -->
        <div class="section">
          <h3>基金基础信息</h3>
          <div v-if="fundDetail.basic_info" class="basic-info-grid">
            <template v-for="(value, key) in fundDetail.basic_info" :key="key">
              <div class="info-row" v-if="filterBasicInfo(key, value)">
                <span class="info-label">{{ formatKey(key) }}:</span>
                <span class="info-value">{{ value || '--' }}</span>
              </div>
            </template>
          </div>
          <div v-else class="no-data">暂无基础信息</div>
        </div>
        
        <!-- 原始数据展示（调试用） -->
        <div class="section" v-if="showRawData">
          <h3>原始数据</h3>
          <pre class="json-data">{{ JSON.stringify(fundDetail, null, 2) }}</pre>
        </div>
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
import { fundAPI } from '../services/api'

export default {
  name: 'FundDetail',
  components: {
    FundBasicInfo,
    FundChart
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
    const showRawData = ref(false) // 控制是否显示原始数据

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

    // 格式化键名显示
    const formatKey = (key) => {
      const keyMap = {
        'fund_code': '基金代码',
        'fund_name': '基金名称',
        'name': '基金名称',
        'fund_name_en': '英文名称',
        'fund_type': '基金类型',
        'purchase_rate': '申购费率',
        'redemption_rate': '赎回费率',
        'management_rate': '管理费率',
        'custodian_rate': '托管费率',
        'establishment_date': '成立日期',
        'issue_date': '发行日期',
        'issue_scale': '发行规模',
        'latest_scale': '最新规模',
        'investment_objective': '投资目标',
        'investment_scope': '投资范围',
        'investment_strategy': '投资策略',
        'fund_rate': '现费率',
        'fund_min_subscription': '最小申购金额',
        'fund_size': '基金规模',
        'hqdate': '行情日期',
        'dwjz': '单位净值',
        'gsz': '估算值',
        'gszzl': '估算增长率',
        'gztime': '估值时间'
      }
      return keyMap[key] || key
    }

    // 过滤不需要显示的基础信息字段
    const filterBasicInfo = (key, value) => {
      const ignoredKeys = ['stock_codes', 'managers', 'net_worth_trend', 'ac_worth_trend'];
      if (ignoredKeys.includes(key)) return false;
      if (typeof value === 'object' && value !== null) return false;
      return true;
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
      showRawData,
      processedNetWorthTrend,
      processedAcWorthTrend,
      retry,
      formatKey,
      filterBasicInfo
    }
  }
}
</script>

<style scoped>
.fund-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.detail-content {
  margin-top: 20px;
}

.detail-sections {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.section h3 {
  margin: 0 0 15px 0;
  color: #333;
  border-bottom: 2px solid #007bff;
  padding-bottom: 8px;
}

/* 持仓股票样式 */
.stock-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stock-tag {
  background: #e3f2fd;
  color: #1976d2;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  border: 1px solid #bbdefb;
}

.more-stocks {
  color: #666;
  font-size: 12px;
  margin-top: 8px;
}

/* 基础信息网格 */
.basic-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-label {
  font-weight: bold;
  color: #666;
  min-width: 120px;
}

.info-value {
  color: #333;
  text-align: right;
  flex: 1;
}

/* 加载状态 */
.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 错误状态 */
.error {
  text-align: center;
  padding: 40px;
  color: #d32f2f;
  background: #ffebee;
  border-radius: 8px;
  margin: 20px 0;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.retry-btn {
  background: #d32f2f;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 16px;
}

.retry-btn:hover {
  background: #b71c1c;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

/* 原始数据展示 */
.json-data {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.no-data {
  color: #999;
  font-style: italic;
  text-align: center;
  padding: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .fund-detail {
    padding: 10px;
  }
  
  .detail-sections {
    grid-template-columns: 1fr;
  }
  
  .basic-info-grid {
    grid-template-columns: 1fr;
  }
  
  .info-row {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .info-value {
    text-align: left;
    margin-top: 4px;
  }
}
</style>