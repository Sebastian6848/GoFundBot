<template>
  <div class="fund-detail">
    <!-- 基金基础信息组件 -->
    <FundBasicInfo :fundCode="currentFundCode" :fundData="fundDetail" :riskMetrics="riskMetrics" />
    
    <!-- 主要内容区域 - Dashboard 布局 -->
    <div v-if="fundDetail" class="dashboard">
      
      <!-- 左侧主区域 -->
      <div class="main-area">
        <!-- 净值走势图 -->
        <div class="card card-chart">
          <FundChart
            :netWorthTrend="processedNetWorthTrend"
            :acWorthTrend="processedAcWorthTrend"
            :grandTotal="fundDetail.total_return_trend"
          />
        </div>
        
        <!-- 中间两列区域 -->
        <div class="grid-2">
          <div class="card card-md clickable" @click="openModal('ranking')">
            <FundRankingTrend
              :rateInSimilarType="fundDetail.ranking_trend"
              :rateInSimilarPercent="fundDetail.ranking_percentage"
            />
          </div>
          <div class="card card-md clickable" @click="openModal('asset')">
            <FundAssetAllocation
              :assetAllocation="fundDetail.asset_allocation"
            />
          </div>
        </div>

        <!-- 底部两列区域 -->
        <div class="grid-2">
          <div class="card card-md clickable" @click="openModal('holder')">
            <FundHolderStructure
              :holderStructure="fundDetail.holder_structure"
            />
          </div>
          <div class="card card-md clickable" @click="openModal('scale')">
            <FundScaleChange
              :fluctuationScale="fundDetail.scale_fluctuation"
            />
          </div>
        </div>

        <!-- 申购赎回情况 - 全宽 -->
        <div class="card card-full clickable" @click="openModal('subscription')">
          <FundSubscription
            :subscriptionRedemption="fundDetail.subscription_redemption"
          />
        </div>
      </div>

      <!-- 右侧边栏 -->
      <div class="sidebar">
        <div class="card card-sidebar clickable" @click="openModal('portfolio')">
          <FundPortfolio
            :portfolio="fundDetail.portfolio"
          />
        </div>
        <div class="card card-sidebar clickable" @click="openModal('manager')">
          <FundManagerInfo
            :fundManagers="fundDetail.fund_managers"
          />
        </div>
        <div class="card card-sidebar clickable" @click="openModal('ability')">
          <FundAbilityEval
            :performanceEvaluation="fundDetail.performance_evaluation"
          />
        </div>
        <div class="card card-sidebar clickable" @click="openModal('sametype')">
          <FundSameType
            :sameTypeFunds="fundDetail.same_type_funds"
          />
        </div>
      </div>
    </div>
    
    <!-- 放大模态框 -->
    <div v-if="modalVisible" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <button class="modal-close" @click="closeModal">×</button>
        <div class="modal-body">
          <FundRankingTrend
            v-if="modalType === 'ranking'"
            :rateInSimilarType="fundDetail.ranking_trend"
            :rateInSimilarPercent="fundDetail.ranking_percentage"
            :isExpanded="true"
          />
          <FundAssetAllocation
            v-if="modalType === 'asset'"
            :assetAllocation="fundDetail.asset_allocation"
          />
          <FundHolderStructure
            v-if="modalType === 'holder'"
            :holderStructure="fundDetail.holder_structure"
          />
          <FundScaleChange
            v-if="modalType === 'scale'"
            :fluctuationScale="fundDetail.scale_fluctuation"
          />
          <FundPortfolio
            v-if="modalType === 'portfolio'"
            :portfolio="fundDetail.portfolio"
          />
          <FundManagerInfo
            v-if="modalType === 'manager'"
            :fundManagers="fundDetail.fund_managers"
          />
          <FundAbilityEval
            v-if="modalType === 'ability'"
            :performanceEvaluation="fundDetail.performance_evaluation"
          />
          <FundSubscription
            v-if="modalType === 'subscription'"
            :subscriptionRedemption="fundDetail.subscription_redemption"
          />
          <FundSameType
            v-if="modalType === 'sametype'"
            :sameTypeFunds="fundDetail.same_type_funds"
            :isExpanded="true"
          />
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
import FundRankingTrend from './FundRankingTrend.vue'
import FundAssetAllocation from './FundAssetAllocation.vue'
import FundScaleChange from './FundScaleChange.vue'
import FundManagerInfo from './FundManagerInfo.vue'
import FundHolderStructure from './FundHolderStructure.vue'
import FundPortfolio from './FundPortfolio.vue'
import FundAbilityEval from './FundAbilityEval.vue'
import FundSubscription from './FundSubscription.vue'
import FundSameType from './FundSameType.vue'
import { fundAPI } from '../services/api'

export default {
  name: 'FundDetail',
  components: {
    FundBasicInfo,
    FundChart,
    FundRankingTrend,
    FundAssetAllocation,
    FundScaleChange,
    FundManagerInfo,
    FundHolderStructure,
    FundPortfolio,
    FundAbilityEval,
    FundSubscription,
    FundSameType
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
    const modalVisible = ref(false)
    const modalType = ref('')

    // 计算风险指标
    const riskMetrics = computed(() => {
      if (!fundDetail.value?.net_worth_trend || fundDetail.value.net_worth_trend.length < 30) {
        return null
      }
      
      try {
        const trend = fundDetail.value.net_worth_trend
        const sortedData = [...trend].sort((a, b) => {
          const dateA = new Date(a.date).getTime()
          const dateB = new Date(b.date).getTime()
          return dateA - dateB
        })
        
        // 转换为净值数组
        const values = sortedData.map(item => parseFloat(item.net_worth)).filter(v => !isNaN(v))
        const dates = sortedData.map(item => item.date)
        
        if (values.length < 30) return null
        
        const now = new Date()
        
        // 获取指定时间段的数据
        const getDataForPeriod = (months) => {
          const cutoffDate = new Date(now)
          cutoffDate.setMonth(cutoffDate.getMonth() - months)
          const cutoffStr = cutoffDate.toISOString().split('T')[0]
          
          const periodValues = []
          for (let i = 0; i < dates.length; i++) {
            if (dates[i] >= cutoffStr) {
              periodValues.push(values[i])
            }
          }
          return periodValues
        }
        
        // 计算最大回撤
        const calcMaxDrawdown = (periodValues) => {
          if (periodValues.length < 2) return null
          
          let peak = periodValues[0]
          let maxDrawdown = 0
          
          for (const value of periodValues) {
            if (value > peak) peak = value
            const drawdown = (peak - value) / peak * 100
            if (drawdown > maxDrawdown) maxDrawdown = drawdown
          }
          
          return maxDrawdown.toFixed(2)
        }
        
        // 计算日收益率
        const calcDailyReturns = (periodValues) => {
          if (periodValues.length < 2) return []
          const returns = []
          for (let i = 1; i < periodValues.length; i++) {
            if (periodValues[i-1] !== 0) {
              returns.push((periodValues[i] - periodValues[i-1]) / periodValues[i-1])
            }
          }
          return returns
        }
        
        // 计算年化收益率
        const calcAnnualReturn = (periodValues, tradingDays) => {
          if (periodValues.length < 2 || periodValues[0] === 0 || tradingDays <= 0) return null
          const totalReturn = (periodValues[periodValues.length - 1] - periodValues[0]) / periodValues[0]
          const annualReturn = (Math.pow(1 + totalReturn, 252 / tradingDays) - 1) * 100
          return annualReturn.toFixed(2)
        }
        
        // 计算年化波动率
        const calcVolatility = (dailyReturns) => {
          if (dailyReturns.length < 10) return null
          const mean = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length
          const variance = dailyReturns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / dailyReturns.length
          const dailyVol = Math.sqrt(variance)
          const annualVol = dailyVol * Math.sqrt(252) * 100
          return annualVol.toFixed(2)
        }
        
        // 计算夏普比率（无风险利率2%）
        const calcSharpeRatio = (annualReturn, volatility) => {
          if (!annualReturn || !volatility || parseFloat(volatility) === 0) return null
          const sharpe = (parseFloat(annualReturn) - 2.0) / parseFloat(volatility)
          return sharpe.toFixed(2)
        }
        
        // 计算近1年指标
        const values1y = getDataForPeriod(12)
        const dailyReturns1y = calcDailyReturns(values1y)
        const annualReturn1y = calcAnnualReturn(values1y, values1y.length)
        const volatility1y = calcVolatility(dailyReturns1y)
        const sharpe1y = calcSharpeRatio(annualReturn1y, volatility1y)
        const maxDrawdown1y = calcMaxDrawdown(values1y)
        
        // 计算近3年指标
        const values3y = getDataForPeriod(36)
        const dailyReturns3y = calcDailyReturns(values3y)
        const annualReturn3y = calcAnnualReturn(values3y, values3y.length)
        const volatility3y = calcVolatility(dailyReturns3y)
        const sharpe3y = calcSharpeRatio(annualReturn3y, volatility3y)
        const maxDrawdown3y = calcMaxDrawdown(values3y)
        
        return {
          sharpe_ratio_1y: sharpe1y,
          sharpe_ratio_3y: sharpe3y,
          max_drawdown_1y: maxDrawdown1y,
          max_drawdown_3y: maxDrawdown3y,
          volatility_1y: volatility1y,
          volatility_3y: volatility3y,
          annual_return_1y: annualReturn1y,
          annual_return_3y: annualReturn3y
        }
      } catch (e) {
        console.error('计算风险指标错误:', e)
        return null
      }
    })

    // 打开模态框
    const openModal = (type) => {
      modalType.value = type
      modalVisible.value = true
      document.body.style.overflow = 'hidden'
    }

    // 关闭模态框
    const closeModal = () => {
      modalVisible.value = false
      modalType.value = ''
      document.body.style.overflow = ''
    }

    // 处理净值走势数据格式
    const processedNetWorthTrend = computed(() => {
      if (!fundDetail.value?.net_worth_trend) return []
      
      try {
        // 处理不同的数据格式
        const trend = fundDetail.value.net_worth_trend
        if (Array.isArray(trend) && trend.length > 0) {
          // 新格式: [{date: '2024-01-01', net_worth: 1.23}]
          if (trend[0].date && trend[0].net_worth !== undefined) {
            return trend.map(item => ({
              x: new Date(item.date).getTime(),
              y: parseFloat(item.net_worth) || 0
            }))
          }
          // 旧格式1: [{x: timestamp, y: value}]
          if (trend[0].x && trend[0].y) {
            return trend.map(item => ({
              x: item.x,
              y: parseFloat(item.y) || 0
            }))
          }
          // 旧格式2: [timestamp, value]
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
      if (!fundDetail.value?.accumulated_net_worth) return []
      
      try {
        const trend = fundDetail.value.accumulated_net_worth
        if (Array.isArray(trend) && trend.length > 0) {
          // 新格式: [{date: '2024-01-01', position_percentage: 1.23}]
          if (trend[0].date !== undefined) {
            return trend.map(item => [
              new Date(item.date).getTime(),
              parseFloat(item.position_percentage) || 0
            ])
          }
          // 旧格式: [[timestamp, value]]
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
      riskMetrics,
      retry,
      modalVisible,
      modalType,
      openModal,
      closeModal
    }
  }
}
</script>

<style scoped>
.fund-detail {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 16px;
  background: #f0f2f5;
  min-height: 100vh;
}

/* Dashboard 主布局 */
.dashboard {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 16px;
  padding: 16px 0;
}

/* 左侧主区域 */
.main-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

/* 右侧边栏 */
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 两列网格 */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* 卡片基础样式 */
.card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  overflow: hidden;
}

/* 图表卡片 - 固定高度 */
.card-chart {
  height: 500px;
  display: flex;
  flex-direction: column;
}

/* 中等高度卡片 - 增加高度 */
.card-md {
  height: 450px;
  display: flex;
  flex-direction: column;
}

/* 大卡片 - 综合评价 */
.card-lg {
  height: 550px;
  display: flex;
  flex-direction: column;
}

/* 全宽卡片 - 申购赎回 */
.card-full {
  height: 480px;
  display: flex;
  flex-direction: column;
}

/* 侧边栏卡片 */
.card-sidebar {
  flex: 1;
  min-height: 300px;
  max-height: 480px;
  display: flex;
  flex-direction: column;
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
@media (max-width: 1400px) {
  .dashboard {
    grid-template-columns: 1fr 340px;
  }
}

@media (max-width: 1200px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
  
  .sidebar {
    flex-direction: row;
  }
  
  .card-sidebar {
    flex: 1;
    max-height: 400px;
  }
}

@media (max-width: 900px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }
  
  .card-md {
    height: auto;
    min-height: 320px;
  }
  
  .sidebar {
    flex-direction: column;
  }
  
  .card-sidebar {
    max-height: none;
  }
}

@media (max-width: 768px) {
  .fund-detail {
    padding: 0 8px;
  }
  
  .dashboard {
    gap: 12px;
    padding: 12px 0;
  }
  
  .main-area, .sidebar {
    gap: 12px;
  }
  
  .grid-2 {
    gap: 12px;
  }
}

/* 可点击卡片样式 */
.clickable {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 16px;
  width: 90vw;
  max-width: 900px;
  height: 80vh;
  max-height: 700px;
  position: relative;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  animation: modalIn 0.3s ease;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.modal-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  border: none;
  background: #f0f0f0;
  border-radius: 50%;
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  transition: background 0.2s;
}

.modal-close:hover {
  background: #e0e0e0;
}

.modal-body {
  flex: 1;
  overflow: hidden;
  border-radius: 16px;
}

.modal-body > * {
  height: 100%;
}
</style>