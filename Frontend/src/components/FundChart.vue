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
        <!-- Placeholder for standard/benchmark if data exists -->
    </div>
    
    <div class="summary-info drawdown-info" v-if="activeTab === 'drawdown'">
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
             <div class="value-row">{{ maxDrawdownInfo.days ? maxDrawdownInfo.days + '天' : '--' }}</div>
        </div>
    </div>

    <div class="chart-container">
      <div ref="chartEl" style="width: 100%; height: 350px;"></div>
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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
        updateChart()
    }

    const getColor = (val) => {
        if (!val) return ''
        return val >= 0 ? 'text-red' : 'text-green'
    }

    // Computed properties for summary
    const fundChange = ref('0.00')
    const maxDrawdownInfo = ref({ val: '0.00', days: 0 })

    const processData = () => {
      if (!props.netWorthTrend.length) return { netWorth: [], drawdownInfo: null }

      const now = new Date()
      let startDate = new Date(0)

      if (selectedRange.value === '3m') {
        startDate = new Date(now.setMonth(now.getMonth() - 3))
      } else if (selectedRange.value === '6m') {
        startDate = new Date(now.setMonth(now.getMonth() - 6))
      } else if (selectedRange.value === '1y') {
        startDate = new Date(now.setFullYear(now.getFullYear() - 1))
      } else if (selectedRange.value === '3y') {
        startDate = new Date(now.setFullYear(now.getFullYear() - 3))
      }

      // Filter Data
      const filtered = props.netWorthTrend.filter(item => item.x >= startDate.getTime())
      
      if (filtered.length === 0) return { netWorth: [], drawdownInfo: null }

      // Calculate Fund Change %
      const startVal = filtered[0].y
      const endVal = filtered[filtered.length - 1].y
      fundChange.value = ((endVal - startVal) / startVal * 100).toFixed(2)

      // Calculate Max Drawdown & Recovery
      // Logic: Iterate to find the (Peak -> Valley) that gives Max Drawdown
      // Then find recovery from that specific Peak
      
      let curMaxdd = 0;
      let globalPeakIndex = 0;
      let globalValleyIndex = 0;
      
      let runningPeakValue = -Infinity;
      let runningPeakIndex = 0;
      
      for (let i = 0; i < filtered.length; i++) {
          const val = filtered[i].y;
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
      const peakVal = filtered[globalPeakIndex].y;
      
      // Look for recovery AFTER the valley? Or AFTER the peak?
      // "Recovery Period" usually starts from Drawdown start (Peak).
      // Find first point > peakVal after peakIndex
      for (let i = globalPeakIndex + 1; i < filtered.length; i++) {
          if (filtered[i].y >= peakVal) {
              recoveryIndex = i;
              break;
          }
      }
      
      const peakDate = filtered[globalPeakIndex].x;
      const valleyDate = filtered[globalValleyIndex].x;
      const recoveryDate = recoveryIndex !== -1 ? filtered[recoveryIndex].x : null;
      
      const days = recoveryDate ? Math.ceil((recoveryDate - peakDate) / (1000 * 3600 * 24)) : null;

      const ddInfo = {
          val: (curMaxdd * 100).toFixed(2),
          peakDate,
          valleyDate,
          recoveryDate,
          days,
          peakValue: peakVal,
          valleyValue: filtered[globalValleyIndex].y,
          recoveryValue: recoveryIndex !== -1 ? filtered[recoveryIndex].y : null
      }
      
      maxDrawdownInfo.value = ddInfo
      
      return {
        netWorth: filtered.map(item => [item.x, item.y]),
        drawdownInfo: ddInfo
      }
    }

    const initChart = () => {
      if (!chartEl.value) return
      
      chartInstance = echarts.init(chartEl.value)
      updateChart()
    }

    const updateChart = () => {
      if (!chartInstance) return

      const { netWorth, drawdownInfo } = processData()
      
      // Common Options
      const option = {
        grid: { left: '3%', right: '5%', bottom: '3%', top: '10%', containLabel: true },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'time', boundaryGap: false, axisLine: { show: false }, axisTick: { show: false } },
        yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { type: 'dashed' } } },
        series: []
      }
      
      if (activeTab.value === 'performance') {
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
      } else {
          // Drawdown View
          const seriesData = {
              name: '本基金',
              type: 'line',
              data: netWorth,
              smooth: true,
              symbol: 'none',
              lineStyle: { width: 2, color: '#88aaff' }, // Lighter blue
              markArea: {
                  itemStyle: { color: 'rgba(255, 230, 230, 0.6)' }, // Light Pink
                  data: []
              },
              markPoint: {
                  symbol: 'circle',
                  symbolSize: 8,
                  label: {
                      show: true,
                      position: 'top',
                      color: '#fff',
                      padding: [4, 8],
                      borderRadius: 4
                  },
                  data: []
              }
          }
          
          if (drawdownInfo && drawdownInfo.peakDate) {
              const endDate = drawdownInfo.recoveryDate || netWorth[netWorth.length - 1][0];
              
              // Mark Area: Peak to Recovery (or End)
              seriesData.markArea.data.push([
                  { xAxis: drawdownInfo.peakDate },
                  { xAxis: endDate }
              ]);
              
              const points = [];
              
              // 1. Tag at Valley: "Max Drawdown X%"
               points.push({
                   xAxis: drawdownInfo.valleyDate,
                   yAxis: drawdownInfo.valleyValue,
                   itemStyle: { color: '#00bfa5' }, // Green dot
                   label: {
                       offset: [0, 15],
                       formatter: `最大回撤${drawdownInfo.val}%`,
                       backgroundColor: '#00bfa5',
                       position: 'bottom'
                   }
               });
               
               // 2. Tag at Recovery (or in middle if recovery): "X Days Recovery"
               if (drawdownInfo.recoveryDate) {
                   // Middle point for the label? Or at the red line?
                   // Screenshot has "36 Days Recovery" in a Red Box pointing to the area/line.
                   // We put it at the end (Recovery point).
                   points.push({
                       xAxis: drawdownInfo.recoveryDate,
                       yAxis: drawdownInfo.recoveryValue,
                       itemStyle: { color: '#ff5252' }, // Red dot
                       label: {
                           offset: [0, -15],
                           formatter: `${drawdownInfo.days}天修复`,
                           backgroundColor: '#ff5252',
                       }
                   });
               }
               
               seriesData.markPoint.data = points;
          }
          
          option.series.push(seriesData);
      }

      chartInstance.setOption(option, true) // true = not merge, replace
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

    watch(() => props.netWorthTrend, () => {
      updateChart()
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
      getColor
    }
  }
}
</script>

<style scoped>
.fund-chart-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  overflow: hidden;
  padding-bottom: 10px;
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