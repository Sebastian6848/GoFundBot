<template>
  <div class="fund-ranking-card">
    <div class="card-header" :class="{ 'header-expanded': isExpanded }">
      <h3>🏆 同类排名走势</h3>
      <div class="time-ranges">
        <span 
          v-for="range in timeRanges" 
          :key="range.value"
          class="range-btn"
          :class="{ active: selectedRange === range.value }"
          @click="setTimeRange(range.value)"
        >{{ range.label }}</span>
      </div>
    </div>
    <div class="card-body">
      <div v-if="hasRankingData" class="ranking-content">
        <div ref="rankingChartEl" class="ranking-chart"></div>
        <div class="ranking-table">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>排名</th>
                <th>同类总数</th>
                <th>击败同类</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in recentRankings" :key="index">
                <td>{{ item.dateFormatted }}</td>
                <td class="rank-value">{{ item.rank }}/{{ item.total_funds }}</td>
                <td>{{ item.total_funds }}</td>
                <td :class="getPercentClass((1 - item.rank / item.total_funds) * 100)">
                  {{ ((1 - item.rank / item.total_funds) * 100).toFixed(2) }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else class="no-data">
        <p>暂无同类排名数据</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'FundRankingTrend',
  props: {
    rateInSimilarType: {
      type: Array,
      default: () => []
    },
    rateInSimilarPercent: {
      type: Array,
      default: () => []
    },
    isExpanded: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const rankingChartEl = ref(null)
    let rankingChartInstance = null
    const selectedRange = ref('1y')

    const timeRanges = [
      { label: '近1年', value: '1y' },
      { label: '近3年', value: '3y' },
      { label: '近5年', value: '5y' },
      { label: '全部', value: 'all' }
    ]

    const hasRankingData = computed(() => 
      props.rateInSimilarType && props.rateInSimilarType.length > 0
    )

    // 合并排名和百分比数据
    const combinedData = computed(() => {
      if (!hasRankingData.value) return []
      
      const percentMap = new Map()
      props.rateInSimilarPercent?.forEach(item => {
        // 新格式: {date, position_percentage}
        if (item.date !== undefined) {
          percentMap.set(item.date, item.position_percentage)
        } else if (Array.isArray(item)) {
          // 旧格式: [timestamp, value]
          percentMap.set(item[0], item[1])
        }
      })

      return props.rateInSimilarType.map(item => {
        // 新格式: {date, rank, total_funds}
        if (item.date !== undefined) {
          const timestamp = new Date(item.date).getTime()
          return {
            x: timestamp,
            rank: item.rank,
            total_funds: item.total_funds,
            dateFormatted: item.date,
            percent: percentMap.get(item.date) || 0
          }
        }
        // 旧格式: {x, y, sc}
        return {
          x: item.x,
          rank: item.y,
          total_funds: item.sc,
          dateFormatted: formatDate(item.x),
          percent: percentMap.get(item.x) || 0
        }
      })
    })

    // 根据时间范围过滤数据
    const filteredData = computed(() => {
      if (!combinedData.value.length) return []
      
      const now = new Date()
      let startDate = new Date(0)
      
      if (selectedRange.value === '1y') {
        startDate = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate())
      } else if (selectedRange.value === '3y') {
        startDate = new Date(now.getFullYear() - 3, now.getMonth(), now.getDate())
      } else if (selectedRange.value === '5y') {
        startDate = new Date(now.getFullYear() - 5, now.getMonth(), now.getDate())
      }
      
      return combinedData.value.filter(item => item.x >= startDate.getTime())
    })

    // 最近5条记录用于表格显示
    const recentRankings = computed(() => {
      return filteredData.value.slice(-5).reverse()
    })

    const setTimeRange = (range) => {
      selectedRange.value = range
      nextTick(() => {
        initRankingChart()
      })
    }

    const formatDate = (timestamp) => {
      return new Date(timestamp).toLocaleDateString('zh-CN')
    }

    const getPercentClass = (defeatPercent) => {
      if (defeatPercent >= 80) return 'excellent'
      if (defeatPercent >= 50) return 'good'
      return 'normal'
    }

    const initRankingChart = () => {
      if (!rankingChartEl.value || !hasRankingData.value) return

      if (rankingChartInstance) {
        rankingChartInstance.dispose()
      }

      rankingChartInstance = echarts.init(rankingChartEl.value)

      // 准备排名百分比数据（Y轴反转，越小越好）- 使用过滤后的数据
      const percentData = filteredData.value.map(item => [item.x, item.percent])

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const dataIndex = params[0].dataIndex
            const item = combinedData.value[dataIndex]
            const defeated = ((1 - item.rank / item.total_funds) * 100).toFixed(2);
            return `
              <div style="font-weight: bold; margin-bottom: 8px;">${item.dateFormatted}</div>
              <div>排名: <strong>${item.rank}/${item.total_funds}</strong></div>
              <div>击败同类: <strong>${defeated}%</strong></div>
            `
          }
        },
        grid: {
          left: '11%',
          right: '13%',
          bottom: '12%',
          top: '4%',
          containLabel: false
        },
        xAxis: {
          type: 'time',
          boundaryGap: false
        },
        yAxis: {
          type: 'value',
          inverse: true, // 反转Y轴，越小越好
          axisLabel: {
            formatter: '{value}%'
          },
          min: 0,
          max: 100
        },
        visualMap: {
          show: false,
          dimension: 1,
          pieces: [
            { lte: 10, color: '#52c41a' },  // 前10%
            { gt: 10, lte: 25, color: '#91cc75' }, // 10-25%
            { gt: 25, lte: 50, color: '#fac858' }, // 25-50%
            { gt: 50, color: '#ff4d4f' }  // 50%以后
          ]
        },
        series: [{
          name: '同类排名',
          type: 'line',
          data: percentData,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 3
          },
          areaStyle: {
            opacity: 0.3
          },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              { yAxis: 10, label: { formatter: '后10%' }, lineStyle: { color: '#52c41a', type: 'dashed' } },
              { yAxis: 25, label: { formatter: '后25%' }, lineStyle: { color: '#91cc75', type: 'dashed' } },
              { yAxis: 50, label: { formatter: '中位数' }, lineStyle: { color: '#fac858', type: 'dashed' } }
            ]
          }
        }]
      }

      rankingChartInstance.setOption(option)
    }

    onMounted(() => {
      nextTick(() => {
        initRankingChart()
      })
    })

    watch(() => [props.rateInSimilarType, props.rateInSimilarPercent], () => {
      nextTick(() => {
        initRankingChart()
      })
    }, { deep: true })

    return {
      rankingChartEl,
      hasRankingData,
      recentRankings,
      formatDate,
      getPercentClass,
      timeRanges,
      selectedRange,
      setTimeRange
    }
  }
}
</script>

<style scoped>
.fund-ranking-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 10px 16px;
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.header-expanded {
  padding-right: 50px; /* Space for close button */
}

.time-ranges {
  display: flex;
  gap: 4px;
}

.range-btn {
  padding: 3px 8px;
  font-size: 11px;
  border-radius: 10px;
  cursor: pointer;
  background: rgba(255,255,255,0.2);
  transition: all 0.2s;
}

.range-btn:hover {
  background: rgba(255,255,255,0.3);
}

.range-btn.active {
  background: white;
  color: #667eea;
  font-weight: 600;
}

.card-body {
  padding: 12px;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ranking-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 100%;
}

.ranking-chart {
  width: 100%;
  height: 220px;
  flex-shrink: 0;
}

.ranking-table {
  flex: 1;
  overflow: auto;
  font-size: 12px;
}

.ranking-table table {
  width: 100%;
  border-collapse: collapse;
}

.ranking-table th,
.ranking-table td {
  padding: 6px 8px;
  text-align: center;
  border-bottom: 1px solid #e8e8e8;
}

.ranking-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.rank-value {
  font-weight: 600;
  color: #333;
}

.excellent {
  color: #f81303;
  font-weight: 600;
}

.good {
  color: #f76b58;
  font-weight: 500;
}

.normal {
  color: #666;
}

.no-data {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.no-data p {
  font-size: 16px;
}
</style>
