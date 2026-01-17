<template>
  <div class="fund-comparison" v-if="selectedFunds.length > 0 || compareFunds.length > 0">
    <div class="comparison-header">
      <h2>
        <span class="header-icon">📈</span>
        基金对比
        <span class="count-badge" v-if="selectedFunds.length">{{ selectedFunds.length }}/{{ maxFunds }}</span>
      </h2>
      <div class="header-actions">
        <button 
          class="btn btn-clear" 
          @click="clearSelection" 
          :disabled="selectedFunds.length === 0"
        >
          清空对比
        </button>
      </div>
    </div>

    <!-- 基金选择区域 -->
    <div class="selection-area">
      <div class="selection-tags">
        <div 
          v-for="fund in selectedFunds" 
          :key="fund.code" 
          class="fund-tag"
          :style="{ borderColor: fund.color }"
        >
          <span class="tag-color" :style="{ background: fund.color }"></span>
          <span class="tag-name">{{ fund.name }}</span>
          <span class="tag-code">({{ fund.code }})</span>
          <button class="tag-remove" @click="removeFund(fund.code)">×</button>
        </div>
        <div v-if="selectedFunds.length < maxFunds && selectedFunds.length > 0" class="add-fund-hint">
          <span>👈 继续从左侧添加基金 (还可添加{{ maxFunds - selectedFunds.length }}只)</span>
        </div>
      </div>
    </div>

    <!-- 对比内容区域 -->
    <div class="comparison-content" v-if="selectedFunds.length >= 2">
      <!-- 净值走势图表 -->
      <div class="chart-section">
        <div class="section-header">
          <h3>📊 净值走势对比</h3>
          <div class="time-ranges">
            <div 
              v-for="range in timeRanges" 
              :key="range.value" 
              class="range-item"
              :class="{ active: selectedRange === range.value }"
              @click="setTimeRange(range.value)"
            >
              {{ range.label }}
            </div>
          </div>
        </div>
        <div class="chart-container">
          <div v-if="loading" class="chart-loading">
            <div class="spinner"></div>
            <span>加载数据中...</span>
          </div>
          <div ref="chartEl" class="chart-el"></div>
        </div>
      </div>

      <!-- 多维度数据对比表格 -->
      <div class="data-table-section">
        <h3>📋 多维度对比</h3>
        <div class="table-wrapper">
          <table class="comparison-table">
            <thead>
              <tr>
                <th class="sticky-col">指标</th>
                <th v-for="fund in selectedFunds" :key="fund.code">
                  <div class="fund-header">
                    <span class="color-dot" :style="{ background: fund.color }"></span>
                    <span class="fund-name-th">{{ fund.name }}</span>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <!-- 收益率指标 -->
              <tr class="section-row">
                <td colspan="100%" class="section-title">📈 收益率</td>
              </tr>
              <tr>
                <td class="sticky-col">近3月</td>
                <td v-for="fund in selectedFunds" :key="fund.code" :class="getValueClass(fund.returns?.m3)">
                  {{ formatReturn(fund.returns?.m3) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">近6月</td>
                <td v-for="fund in selectedFunds" :key="fund.code" :class="getValueClass(fund.returns?.m6)">
                  {{ formatReturn(fund.returns?.m6) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">近1年</td>
                <td v-for="fund in selectedFunds" :key="fund.code" :class="getValueClass(fund.returns?.y1)">
                  {{ formatReturn(fund.returns?.y1) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">近3年</td>
                <td v-for="fund in selectedFunds" :key="fund.code" :class="getValueClass(fund.returns?.y3)">
                  {{ formatReturn(fund.returns?.y3) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">成立来</td>
                <td v-for="fund in selectedFunds" :key="fund.code" :class="getValueClass(fund.returns?.all)">
                  {{ formatReturn(fund.returns?.all) }}
                </td>
              </tr>
              
              <!-- 基金基本信息 -->
              <tr class="section-row">
                <td colspan="100%" class="section-title">💼 基金信息</td>
              </tr>
              <tr>
                <td class="sticky-col">基金规模</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ fund.scale || '--' }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">基金类型</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ fund.fundType || '--' }}
                </td>
              </tr>
              
              <!-- 风险指标 -->
              <tr class="section-row">
                <td colspan="100%" class="section-title">⚠️ 风险指标</td>
              </tr>
              <tr>
                <td class="sticky-col">最大回撤(近1年)</td>
                <td v-for="fund in selectedFunds" :key="fund.code" class="negative">
                  {{ formatDrawdown(fund.riskMetrics?.max_drawdown_1y) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">最大回撤(近3年)</td>
                <td v-for="fund in selectedFunds" :key="fund.code" class="negative">
                  {{ formatDrawdown(fund.riskMetrics?.max_drawdown_3y) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">夏普比率(近1年)</td>
                <td v-for="fund in selectedFunds" :key="fund.code" :class="getSharpeClass(fund.riskMetrics?.sharpe_ratio_1y)">
                  {{ formatSharpe(fund.riskMetrics?.sharpe_ratio_1y) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">夏普比率(近3年)</td>
                <td v-for="fund in selectedFunds" :key="fund.code" :class="getSharpeClass(fund.riskMetrics?.sharpe_ratio_3y)">
                  {{ formatSharpe(fund.riskMetrics?.sharpe_ratio_3y) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">年化波动率(近1年)</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ formatVolatility(fund.riskMetrics?.volatility_1y) }}
                </td>
              </tr>
              
              <!-- 评分指标 -->
              <tr class="section-row">
                <td colspan="100%" class="section-title">⭐ 评分指标</td>
              </tr>
              <tr>
                <td class="sticky-col">综合评分</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  <span class="score-badge" :class="getScoreClass(fund.evaluation?.avgScore)">
                    {{ fund.evaluation?.avgScore ?? '--' }}
                  </span>
                </td>
              </tr>
              <tr>
                <td class="sticky-col">选证能力</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ getEvalScore(fund, 0) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">收益率</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ getEvalScore(fund, 1) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">抗风险</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ getEvalScore(fund, 2) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">稳定性</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ getEvalScore(fund, 3) }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">择时能力</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ getEvalScore(fund, 4) }}
                </td>
              </tr>
              
              <!-- 基金经理 -->
              <tr class="section-row">
                <td colspan="100%" class="section-title">👤 基金经理</td>
              </tr>
              <tr>
                <td class="sticky-col">基金经理</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ fund.manager?.name || '--' }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">从业经验</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ fund.manager?.experience || '--' }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">管理规模</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  {{ fund.manager?.managedSize || '--' }}
                </td>
              </tr>
              <tr>
                <td class="sticky-col">经理评分</td>
                <td v-for="fund in selectedFunds" :key="fund.code">
                  <span v-if="fund.manager?.avgScore" class="score-badge" :class="getScoreClass(fund.manager.avgScore)">
                    {{ fund.manager.avgScore }}
                  </span>
                  <span v-else>--</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 单只基金提示 -->
    <div v-else-if="selectedFunds.length === 1" class="single-fund-hint">
      <p>👈 请再选择至少1只基金进行对比</p>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { fundAPI } from '../services/api'

export default {
  name: 'FundComparison',
  props: {
    compareFunds: {
      type: Array,
      default: () => []
    }
  },
  emits: ['remove-fund', 'clear-funds'],
  setup(props, { emit }) {
    const chartEl = ref(null)
    const selectedRange = ref('1y')
    const loading = ref(false)
    const maxFunds = 5
    let chartInstance = null

    const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4']

    const timeRanges = [
      { label: '近3月', value: '3m' },
      { label: '近6月', value: '6m' },
      { label: '近1年', value: '1y' },
      { label: '近3年', value: '3y' },
      { label: '成立来', value: 'all' }
    ]

    const selectedFunds = ref([])

    // 获取基金对比数据（使用缓存API）
    const fetchFundCompareData = async (fundCode) => {
      try {
        const response = await fundAPI.getFundCompareData(fundCode)
        return response.data
      } catch (error) {
        console.error(`获取基金 ${fundCode} 对比数据失败:`, error)
        return null
      }
    }

    // 将后端数据转换为统一格式 {x: timestamp, y: value}
    const normalizeData = (data) => {
      if (!data || data.length === 0) return []
      return data.map(item => ({
        x: new Date(item.date).getTime(),
        y: item.net_worth
      })).filter(item => !isNaN(item.x) && item.y !== null && item.y !== undefined)
    }

    // 计算收益率
    const calculateReturns = (trendData) => {
      if (!trendData || trendData.length === 0) return {}
      
      const sortedData = [...trendData].sort((a, b) => a.x - b.x)
      const latestValue = sortedData[sortedData.length - 1].y
      const now = Date.now()

      const getReturnForPeriod = (months) => {
        let targetTime
        if (months === 'all') {
          targetTime = sortedData[0].x
        } else {
          const date = new Date(now)
          date.setMonth(date.getMonth() - months)
          targetTime = date.getTime()
        }
        
        let closest = sortedData[0]
        for (const item of sortedData) {
          if (item.x >= targetTime) {
            closest = item
            break
          }
        }
        
        if (closest.y === 0) return null
        return ((latestValue - closest.y) / closest.y * 100).toFixed(2)
      }

      return {
        m3: getReturnForPeriod(3),
        m6: getReturnForPeriod(6),
        y1: getReturnForPeriod(12),
        y3: getReturnForPeriod(36),
        all: getReturnForPeriod('all')
      }
    }

    // 加载基金完整数据（使用缓存API）
    const loadFundData = async (fund) => {
      // 获取对比数据（包含走势、详情、风险指标）
      const data = await fetchFundCompareData(fund.code)
      
      if (!data) return fund
      
      // 处理走势数据
      if (data.net_worth_trend && data.net_worth_trend.length > 0) {
        fund.trendData = normalizeData(data.net_worth_trend)
        fund.returns = calculateReturns(fund.trendData)
      }
      
      // 基本信息
      const basicInfo = data.basic_info || {}
      fund.fundType = basicInfo.fund_type || '--'
      
      // 规模波动数据 - 结构是 series: [{y: value, mom: "..."}, ...]
      const scaleData = data.scale_fluctuation || {}
      if (scaleData.series && scaleData.series.length > 0) {
        const latestItem = scaleData.series[scaleData.series.length - 1]
        if (latestItem && latestItem.y !== undefined && latestItem.y !== null) {
          fund.scale = latestItem.y.toFixed(2) + '亿'
        } else {
          fund.scale = '--'
        }
      }

      // 风险指标
      fund.riskMetrics = data.risk_metrics || {}
      
      // 数据来源标记
      fund.dataSource = data.data_source || 'unknown'
      fund.cacheTime = data.cache_time

      // 基金评价数据 - categories: ["选证能力","收益率","抗风险","稳定性","择时能力"]
      const evalData = data.performance_evaluation || {}
      fund.evaluation = {
        avgScore: evalData.avr || null,
        data: evalData.data || [],
        categories: evalData.categories || []
      }

      // 基金经理信息
      const managers = data.fund_managers || []
      if (managers.length > 0) {
        const manager = managers[0]
        fund.manager = {
          name: manager.name || '--',
          experience: manager.work_experience || '--',
          managedSize: manager.managed_fund_size || '--',
          avgScore: manager.ability_assessment?.average_score || null
        }
      }

      return fund
    }

    // 过滤数据按时间范围
    const filterByDate = (data, range) => {
      if (!data || data.length === 0) return []
      
      const now = new Date()
      let startDate = new Date(0)

      if (range === '3m') {
        startDate = new Date(now.getTime())
        startDate.setMonth(startDate.getMonth() - 3)
      } else if (range === '6m') {
        startDate = new Date(now.getTime())
        startDate.setMonth(startDate.getMonth() - 6)
      } else if (range === '1y') {
        startDate = new Date(now.getTime())
        startDate.setFullYear(startDate.getFullYear() - 1)
      } else if (range === '3y') {
        startDate = new Date(now.getTime())
        startDate.setFullYear(startDate.getFullYear() - 3)
      }

      return data.filter(item => item.x >= startDate.getTime())
    }

    // 转换为百分比变化
    const toPercentChange = (data) => {
      if (!data || data.length === 0) return []
      const sortedData = [...data].sort((a, b) => a.x - b.x)
      const startVal = sortedData[0].y
      if (startVal === 0) return []
      
      return sortedData.map(item => [
        item.x,
        parseFloat(((item.y - startVal) / startVal * 100).toFixed(2))
      ])
    }

    // 初始化图表
    const initChart = () => {
      if (!chartEl.value) return
      
      const rect = chartEl.value.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) {
        setTimeout(initChart, 100)
        return
      }
      
      if (chartInstance) {
        chartInstance.dispose()
      }
      chartInstance = echarts.init(chartEl.value)
      updateChart()
    }

    // 更新图表
    const updateChart = () => {
      if (!chartInstance || selectedFunds.value.length < 2) return

      const series = []
      
      selectedFunds.value.forEach((fund) => {
        if (!fund.trendData || fund.trendData.length === 0) return
        
        const filteredData = filterByDate(fund.trendData, selectedRange.value)
        const percentData = toPercentChange(filteredData)
        
        if (percentData.length > 0) {
          series.push({
            name: fund.name,
            type: 'line',
            data: percentData,
            smooth: true,
            symbol: 'none',
            lineStyle: { width: 2, color: fund.color },
            itemStyle: { color: fund.color }
          })
        }
      })

      if (series.length === 0) return

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: function (params) {
            let res = '<div style="font-weight:bold;margin-bottom:5px;">' + 
                      echarts.format.formatTime('yyyy-MM-dd', params[0].value[0]) + '</div>'
            params.forEach(item => {
              const val = item.value[1]
              const color = val >= 0 ? '#f5222d' : '#52c41a'
              res += `<div style="display:flex;align-items:center;margin:3px 0;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${item.color};margin-right:8px;"></span>
                <span style="flex:1;">${item.seriesName}</span>
                <span style="font-weight:bold;color:${color};margin-left:10px;">${val >= 0 ? '+' : ''}${val}%</span>
              </div>`
            })
            return res
          }
        },
        legend: {
          show: true,
          top: 5,
          data: selectedFunds.value.map(f => f.name),
          textStyle: { fontSize: 12 }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          top: 40,
          containLabel: true
        },
        xAxis: {
          type: 'time',
          boundaryGap: false,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { formatter: '{MM}-{dd}' }
        },
        yAxis: {
          type: 'value',
          scale: true,
          splitLine: { lineStyle: { type: 'dashed' } },
          axisLabel: { formatter: '{value}%' }
        },
        series: series
      }

      chartInstance.setOption(option, true)
    }

    const setTimeRange = (range) => {
      selectedRange.value = range
      updateChart()
    }

    const removeFund = (fundCode) => {
      emit('remove-fund', fundCode)
    }

    const clearSelection = () => {
      emit('clear-funds')
    }

    const getValueClass = (value) => {
      if (value === null || value === undefined || value === '--') return ''
      const num = parseFloat(value)
      if (num > 0) return 'positive'
      if (num < 0) return 'negative'
      return ''
    }

    const getSharpClass = (value) => {
      if (value === null || value === undefined) return ''
      const num = parseFloat(value)
      if (num >= 1) return 'positive'
      if (num < 0) return 'negative'
      return ''
    }

    const getScoreClass = (score) => {
      if (!score) return ''
      if (score >= 80) return 'score-high'
      if (score >= 60) return 'score-mid'
      return 'score-low'
    }

    const formatReturn = (value) => {
      if (value === null || value === undefined) return '--'
      const num = parseFloat(value)
      return (num >= 0 ? '+' : '') + value + '%'
    }

    // 格式化最大回撤
    const formatDrawdown = (value) => {
      if (value === null || value === undefined) return '--'
      return '-' + value.toFixed(2) + '%'
    }

    // 格式化夏普比率
    const formatSharpe = (value) => {
      if (value === null || value === undefined) return '--'
      return value.toFixed(2)
    }

    // 格式化波动率
    const formatVolatility = (value) => {
      if (value === null || value === undefined) return '--'
      return value.toFixed(2) + '%'
    }

    // 夏普比率样式类
    const getSharpeClass = (value) => {
      if (value === null || value === undefined) return ''
      if (value >= 1) return 'positive'
      if (value >= 0) return ''
      return 'negative'
    }

    const getEvalScore = (fund, index) => {
      if (!fund.evaluation?.data || !fund.evaluation.data[index]) return '--'
      return fund.evaluation.data[index].toFixed(1)
    }

    // 监听比较基金列表变化
    watch(() => props.compareFunds, async (newFunds) => {
      if (!newFunds || newFunds.length === 0) {
        selectedFunds.value = []
        return
      }
      
      loading.value = true
      
      const updatedFunds = []
      for (let i = 0; i < newFunds.length; i++) {
        const fund = newFunds[i]
        const existing = selectedFunds.value.find(f => f.code === fund.code)
        
        if (existing) {
          existing.color = colors[i % colors.length]
          updatedFunds.push(existing)
        } else {
          const newFund = {
            code: fund.code,
            name: fund.name,
            color: colors[i % colors.length],
            trendData: null,
            returns: {},
            evaluation: {},
            manager: null,
            scale: '--',
            fundType: '--',
            riskMetrics: {},
            dataSource: null,
            cacheTime: null
          }
          await loadFundData(newFund)
          updatedFunds.push(newFund)
        }
      }
      
      selectedFunds.value = updatedFunds
      loading.value = false
      
      await nextTick()
      
      if (selectedFunds.value.length >= 2) {
        setTimeout(() => initChart(), 50)
      }
    }, { immediate: true, deep: true })

    watch(selectedRange, () => updateChart())

    onMounted(() => {
      window.addEventListener('resize', () => chartInstance?.resize())
    })

    onUnmounted(() => {
      if (chartInstance) chartInstance.dispose()
      window.removeEventListener('resize', () => chartInstance?.resize())
    })

    return {
      chartEl,
      selectedFunds,
      selectedRange,
      timeRanges,
      loading,
      maxFunds,
      setTimeRange,
      removeFund,
      clearSelection,
      getValueClass,
      getSharpClass,
      getScoreClass,
      formatReturn,
      formatDrawdown,
      formatSharpe,
      formatVolatility,
      getSharpeClass,
      getEvalScore
    }
  }
}
</script>

<style scoped>
.fund-comparison {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 20px;
  overflow: hidden;
}

.comparison-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid #f0f0f0;
  background: linear-gradient(135deg, #f8f9ff 0%, #fff 100%);
}

.comparison-header h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.header-icon { font-size: 18px; }

.count-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.btn {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-clear {
  background: #f5f5f5;
  color: #666;
}

.btn-clear:hover:not(:disabled) { background: #e8e8e8; }

.selection-area {
  padding: 12px 20px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.selection-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  min-height: 32px;
}

.fund-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: white;
  border: 2px solid;
  border-radius: 20px;
  font-size: 13px;
}

.tag-color {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.tag-name {
  color: #333;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag-code { color: #999; font-size: 12px; }

.tag-remove {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0 2px;
}

.tag-remove:hover { color: #f5222d; }

.add-fund-hint { color: #999; font-size: 13px; }

.single-fund-hint {
  padding: 20px;
  text-align: center;
  color: #999;
}

.comparison-content { padding: 0; }

.chart-section {
  padding: 15px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.section-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.time-ranges {
  display: flex;
  gap: 6px;
}

.range-item {
  padding: 4px 12px;
  color: #666;
  cursor: pointer;
  font-size: 12px;
  border-radius: 12px;
  transition: all 0.2s;
}

.range-item:hover { background: #f5f5f5; }

.range-item.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 500;
}

.chart-container {
  position: relative;
  height: 240px;
}

.chart-el { width: 100%; height: 100%; }

.chart-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #999;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #f0f0f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.data-table-section {
  padding: 15px 20px 20px;
}

.data-table-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 12px 0;
}

.table-wrapper {
  overflow-x: auto;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 600px;
}

.comparison-table th,
.comparison-table td {
  padding: 10px 12px;
  text-align: center;
  border-bottom: 1px solid #f0f0f0;
}

.comparison-table th {
  background: #fafafa;
  color: #666;
  font-weight: 500;
  position: sticky;
  top: 0;
  z-index: 1;
}

.sticky-col {
  position: sticky;
  left: 0;
  background: white;
  text-align: left !important;
  font-weight: 500;
  color: #333;
  min-width: 90px;
  z-index: 1;
}

.section-row td {
  background: #f8f9ff !important;
  font-weight: 600;
  color: #667eea;
  text-align: left !important;
  padding: 8px 12px;
}

.section-title { font-size: 12px; }

.fund-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.fund-name-th {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.positive { color: #f5222d; font-weight: 500; }
.negative { color: #52c41a; font-weight: 500; }

.score-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.score-high { background: #fff1f0; color: #f5222d; }
.score-mid { background: #fff7e6; color: #fa8c16; }
.score-low { background: #f6ffed; color: #52c41a; }

/* 响应式 */
@media (max-width: 768px) {
  .comparison-table { font-size: 12px; }
  .comparison-table th, .comparison-table td { padding: 8px 8px; }
  .tag-name { max-width: 60px; }
  .section-header { flex-direction: column; gap: 10px; align-items: flex-start; }
}
</style>
