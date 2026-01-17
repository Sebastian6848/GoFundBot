<template>
  <div class="fund-chart-card">
    <div class="top-tabs">
      <div 
        class="tab-item" 
        :class="{ active: activeTab === 'performance' }"
        @click="switchTab('performance')"
      >
        业绩走势
      </div>
      <div 
        class="tab-item" 
        :class="{ active: activeTab === 'comparison' }"
        @click="switchTab('comparison')"
      >
        收益对比
      </div>
      <div 
        class="tab-item" 
        :class="{ active: activeTab === 'drawdown' }"
        @click="switchTab('drawdown')"
      >
        回撤修复
      </div>
    </div>

    <div class="summary-info" v-if="activeTab === 'performance'">
        <div class="info-group">
            <span class="legend-dot blue"></span>
            <span class="label">本基金</span>
            <br>
            <span class="value" :class="getColor(fundChange)">{{ fundChange > 0 ? '+' : ''}}{{ fundChange }}%</span>
        </div>
    </div>
    
    <div class="summary-info drawdown-info" v-else-if="activeTab === 'drawdown'">
        <div class="info-group">
            <div class="legend-dot-row">
                <span class="legend-line green"></span>
                <span class="label">最大回撤</span>
            </div>
            <div class="value-row">{{ maxDrawdownInfo.val }}%</div>
        </div>
        <div class="info-group">
             <div class="legend-dot-row">
                <span class="legend-box pink"></span>
                <span class="label">最大回撤修复天数</span>
             </div>
             <div class="value-row">{{ maxDrawdownInfo.days ? maxDrawdownInfo.days + '天' : '正在修复中...' }}</div>
        </div>
    </div>

    <div class="summary-info comparison-info" v-else-if="activeTab === 'comparison'">
        <div class="info-group" v-for="item in comparisonInfo" :key="item.name">
             <div class="legend-dot-row">
                <span class="legend-dot" :style="{ background: item.color, width: '12px', height: '3px' }"></span>
                <span class="label" style="margin-left: 4px;">{{ item.name }}</span>
             </div>
             <!-- Optional: Add value at end of period? -->
        </div>
    </div>

    <div class="chart-container">
      <div ref="chartEl" class="chart-el"></div>
    </div>

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
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'FundChart',
  props: {
    netWorthTrend: {
      type: Array,
      default: () => []
    },
    acWorthTrend: {
      type: Array,
      default: () => []
    },
    grandTotal: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const chartEl = ref(null)
    const activeTab = ref('performance')
    const selectedRange = ref('1y')
    let chartInstance = null

    const timeRanges = [
      { label: '近3月', value: '3m' },
      { label: '近6月', value: '6m' },
      { label: '近1年', value: '1y' },
      { label: '近3年', value: '3y' },
      { label: '全部', value: 'all' }
    ]

    const setTimeRange = (range) => {
      selectedRange.value = range
      updateChart()
    }
    
    const switchTab = (tab) => {
        activeTab.value = tab
        nextTick(() => {
            if (chartInstance) {
                chartInstance.dispose();
                chartInstance = null;
            }
            initChart();
        })
    }

    const getColor = (val) => {
        if (!val) return ''
        return val >= 0 ? 'text-red' : 'text-green'
    }

    // Computed properties for summary
    const fundChange = ref('0.00')
    const maxDrawdownInfo = ref({ val: '0.00', days: 0 })
    const comparisonInfo = ref([])

    const filterByDate = (data, range) => {
        if (!data || data.length === 0) return []
        const now = new Date()
        let startDate = new Date(0)

        if (range === '3m') {
            startDate = new Date(now.setMonth(now.getMonth() - 3))
        } else if (range === '6m') {
            startDate = new Date(now.setMonth(now.getMonth() - 6))
        } else if (range === '1y') {
            startDate = new Date(now.setFullYear(now.getFullYear() - 1))
        } else if (range === '3y') {
            startDate = new Date(now.setFullYear(now.getFullYear() - 3))
        }
        
        // 支持新格式: [{date: '2024-01-01', value: 1.23}]
        if (data.length > 0 && data[0].date !== undefined) {
            return data
                .map(item => [new Date(item.date).getTime(), item.value])
                .filter(item => item[0] >= startDate.getTime())
        }
        // 旧格式: [[timestamp, value]]
        return data.filter(item => item[0] >= startDate.getTime())
    }

    const processData = () => {
        const rawData = (props.netWorthTrend || []).map(item => [item.x, item.y]);
        const filtered = filterByDate(rawData, selectedRange.value).slice().sort((a, b) => a[0] - b[0]);
        
        if (filtered.length === 0) return { netWorth: [], drawdownInfo: null }

        const startVal = filtered[0][1]
        const endVal = filtered[filtered.length - 1][1]
        fundChange.value = startVal !== 0 ? ((endVal - startVal) / startVal * 100).toFixed(2) : '0.00'

        // Prepare Percentage Data
        const toPercent = (val) => startVal !== 0 ? parseFloat(((val - startVal) / startVal * 100).toFixed(2)) : 0
        const percentTrend = filtered.map(item => [item[0], toPercent(item[1])])

        // Calculate Max Drawdown & Recovery
        let curMaxdd = 0;
        let globalPeakIndex = 0;
        let globalValleyIndex = 0;
        
        let runningPeakValue = -Infinity;
        let runningPeakIndex = 0;
        
        for (let i = 0; i < filtered.length; i++) {
            const val = filtered[i][1];
            if (val > runningPeakValue) {
                runningPeakValue = val;
                runningPeakIndex = i;
            }
            
            const dd = (runningPeakValue - val) / runningPeakValue;
            if (dd > curMaxdd) {
                curMaxdd = dd;
                globalPeakIndex = runningPeakIndex;
                globalValleyIndex = i;
            }
        }
        
        // Check Recovery
        let recoveryIndex = -1;
        const peakValRaw = filtered[globalPeakIndex][1];
        
        for (let i = globalPeakIndex + 1; i < filtered.length; i++) {
            if (filtered[i][1] >= peakValRaw) {
                recoveryIndex = i;
                break;
            }
        }
        
        const peakDate = filtered[globalPeakIndex][0];
        const valleyDate = filtered[globalValleyIndex][0];
        const recoveryDate = recoveryIndex !== -1 ? filtered[recoveryIndex][0] : null;
        
        const days = recoveryDate ? Math.ceil((recoveryDate - peakDate) / (1000 * 3600 * 24)) : null;

        const ddInfo = {
            val: (curMaxdd * 100).toFixed(2),
            peakDate,
            valleyDate,
            recoveryDate,
            days,
            peakValue: toPercent(peakValRaw),
            valleyValue: toPercent(filtered[globalValleyIndex][1]),
            recoveryValue: recoveryIndex !== -1 ? toPercent(filtered[recoveryIndex][1]) : null
        }

        
        maxDrawdownInfo.value = ddInfo
        
        // Also process Comparison Data just in case we need to filter for Comparison Tab?
        // Usually comparison tab shows "All" or follows the range selector if enabled. 
        // User requirements usually imply comparison follows standard range or all. 
        // But the range selector is hidden for comparison in template: v-if="activeTab !== 'comparison'"
        
        return {
            netWorth: percentTrend,
            drawdownInfo: ddInfo
        }
    }

    const initChart = () => {
      if (!chartEl.value) return
      if (!chartInstance) {
          chartInstance = echarts.init(chartEl.value)
      }
      updateChart()
    }

    const updateChart = () => {
      if (!chartInstance) return

      chartInstance.clear(); 

      const option = {
        grid: { left: '3%', right: '5%', bottom: '10%', top: '15%', containLabel: true },
        tooltip: { 
            trigger: 'axis',
            formatter: function (params) {
                let res = '<div>' + echarts.format.formatTime('yyyy-MM-dd', params[0].value[0]) + '</div>'
                params.forEach(item => {
                    let val = item.value[1];
                    // If comparison, values are usually percents.
                    // If net worth, values are currency.
                    res += `<div>${item.marker} ${item.seriesName}: ${val}${activeTab.value === 'comparison' ? '%' : ''}</div>`
                })
                return res;
            }
        },
        xAxis: { type: 'time', boundaryGap: false, axisLine: { show: false }, axisTick: { show: false } },
        yAxis: { 
            type: 'value', 
            scale: true, 
            splitLine: { lineStyle: { type: 'dashed' } },
            axisLabel: { formatter: '{value}%' }
        },
        series: []
      }

      if (activeTab.value === 'performance') {
          const { netWorth } = processData()
          option.series.push({
              name: '本基金',
              type: 'line',
              data: netWorth,
              smooth: true,
              symbol: 'none',
              lineStyle: { width: 2, color: '#007bff' },
              areaStyle: {
                  color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                      { offset: 0, color: 'rgba(0, 123, 255, 0.2)' },
                      { offset: 1, color: 'rgba(0, 123, 255, 0.0)' }
                  ])
              }
          })
          
          option.tooltip.formatter = function (params) {
              let res = '<div>' + echarts.format.formatTime('yyyy-MM-dd', params[0].value[0]) + '</div>'
              params.forEach(item => {
                  res += `<div>${item.marker} ${item.seriesName}: ${item.value[1]}%</div>`
              })
              return res;
          }
      } else if (activeTab.value === 'comparison') {
          const comparisonData = props.grandTotal || []
          
          if (comparisonData.length > 0) {
              const colors = ['#007bff', '#91cc75', '#fac858', '#ee6666', '#5470c6'];
              
              // Update Legend Info
              comparisonInfo.value = comparisonData.map((item, index) => ({
                  name: item.name,
                  color: colors[index % colors.length]
              }))

              const series = comparisonData.map((item, index) => {
                  const rawData = item.data || [];
                  const filteredData = filterByDate(rawData, selectedRange.value);
                  
                  return {
                    name: item.name,
                    type: 'line',
                    data: filteredData, 
                    smooth: true,
                    symbol: 'none',
                    lineStyle: { 
                        width: item.name.includes('本基金') ? 3 : 1.5
                    },
                    itemStyle: {
                        color: colors[index % colors.length]
                    },
                    z: item.name.includes('本基金') ? 3 : 2
                 }
              });
              
              option.series = series
              option.legend = { show: false } // Hide internal legend
              
              // Adjust tooltip for comparison to show %
              option.tooltip.formatter = function (params) {
                  let res = '<div>' + echarts.format.formatTime('yyyy-MM-dd', params[0].value[0]) + '</div>'
                  params.forEach(item => {
                      res += `<div>
                        <span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:${item.color};"></span>
                        ${item.seriesName}: ${item.value[1]}%
                      </div>`
                  })
                  return res;
              }
          }
      } else if (activeTab.value === 'drawdown') {
          const { netWorth, drawdownInfo } = processData()
          
          if (netWorth.length > 0) {
              const seriesData = {
                  name: '本基金',
                  type: 'line',
                  data: netWorth,
                  smooth: true,
                  symbol: 'none',
                  lineStyle: { width: 2, color: '#88aaff' },
                  markArea: {
                      itemStyle: { color: 'rgba(255, 230, 230, 0.6)' },
                      data: []
                  },
                  markPoint: {
                      symbol: 'circle',
                      symbolSize: 8,
                      label: {
                          show: true,
                          color: '#fff',
                          padding: [4, 8],
                          borderRadius: 4
                      },
                      data: []
                  }
              }
              
              if (drawdownInfo && drawdownInfo.peakDate) {
                  const endDate = drawdownInfo.recoveryDate || netWorth[netWorth.length - 1][0];
                  
                  seriesData.markArea.data.push([
                      { xAxis: drawdownInfo.peakDate },
                      { xAxis: endDate }
                  ]);
                  
                  const points = [];
                  points.push({
                      coord: [drawdownInfo.peakDate, drawdownInfo.peakValue],
                      itemStyle: { color: '#ff9800' }, 
                      label: { show: false } 
                  });
                   
                  points.push({
                       coord: [drawdownInfo.valleyDate, drawdownInfo.valleyValue],
                       itemStyle: { color: '#00bfa5' },
                       label: {
                           offset: [0, 15],
                           formatter: `最大回撤${drawdownInfo.val}%`,
                           backgroundColor: 'rgba(0, 191, 165, 0.7)',
                           position: 'top'
                       }
                  });
                   
                  if (drawdownInfo.recoveryDate) {
                       points.push({
                           coord: [drawdownInfo.recoveryDate, drawdownInfo.recoveryValue],
                           itemStyle: { color: '#ff5252' },
                           label: {
                               offset: [0, -15],
                               formatter: `${drawdownInfo.days}天修复`,
                               backgroundColor: 'rgba(255, 82, 82, 0.7)',
                               position: 'bottom'
                           }
                       });
                  }
                   
                  seriesData.markPoint.data = points;
              }
              option.series.push(seriesData)
          }
      }

      chartInstance.setOption(option)
    }

    onMounted(() => {
      initChart()
      window.addEventListener('resize', () => chartInstance?.resize())
    })

    onUnmounted(() => {
      if (chartInstance) {
        chartInstance.dispose()
      }
      window.removeEventListener('resize', () => chartInstance?.resize())
    })

    watch([() => props.netWorthTrend, () => props.grandTotal], () => {
      nextTick(() => updateChart()) 
    }, { deep: true })
    
    return {
      chartEl,
      timeRanges,
      selectedRange,
      setTimeRange,
      activeTab,
      switchTab,
      fundChange,
      maxDrawdownInfo,
      comparisonInfo,
      getColor
    }
  }
}
</script>

<style scoped>
.fund-chart-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  overflow: hidden;
}

.top-tabs {
  display: flex;
  border-bottom: 1px solid #f0f0f0;
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 15px 0;
  font-size: 16px;
  color: #666;
  cursor: pointer;
  position: relative;
  font-weight: 500;
}

.tab-item.active {
  color: #333;
  font-weight: bold;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 3px;
  background: #333;
  border-radius: 2px;
}

.summary-info {
  display: flex;
  justify-content: space-around;
  padding: 15px 20px 5px;
}

.info-group {
    text-align: center;
}

.legend-dot {
    display: inline-block;
    width: 8px;
    height: 3px;
    vertical-align: middle;
    margin-right: 5px;
    background: #007bff;
    border-radius: 2px;
}

.legend-dot-row {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 4px;
}

.legend-line.green {
    width: 12px;
    height: 3px;
    background: #00bfa5;
    margin-right: 5px;
}

.legend-box.pink {
    width: 12px;
    height: 12px;
    background: rgba(255, 230, 230, 1);
    margin-right: 5px;
}

.label {
    font-size: 13px;
    color: #999;
}

.value {
    font-size: 18px;
    font-weight: bold;
    display: block;
    margin-top: 4px;
}

.value-row {
    font-size: 18px;
    font-weight: bold;
    color: #333;
}

.text-red { color: #f5222d; }
.text-green { color: #52c41a; }

.chart-container {
  padding: 0 10px;
  flex: 1;
  min-height: 0;
}

.chart-el {
  width: 100%;
  height: 100%;
  min-height: 280px;
}

.time-ranges {
  display: flex;
  justify-content: space-between;
  padding: 10px 20px;
}

.range-item {
  padding: 4px 12px;
  color: #999;
  cursor: pointer;
  font-size: 13px;
  border-radius: 12px;
}

.range-item.active {
  background: #e6f7ff;
  color: #007bff;
  font-weight: 500;
}
</style>