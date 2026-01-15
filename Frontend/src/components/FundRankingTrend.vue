<template>
  <div class="fund-ranking-card">
    <div class="card-header">
      <h3>🏆 同类排名走势</h3>
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
                <th>同类基金总数</th>
                <th>击败同类</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in recentRankings" :key="index">
                <td>{{ formatDate(item.x) }}</td>
                <td class="rank-value">{{ item.y }}/{{ item.sc }}</td>
                <td>{{ item.sc }}</td>
                <td :class="getPercentClass((1 - item.y / item.sc) * 100)">
                  {{ ((1 - item.y / item.sc) * 100).toFixed(2) }}%
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
    }
  },
  setup(props) {
    const rankingChartEl = ref(null)
    let rankingChartInstance = null

    const hasRankingData = computed(() => 
      props.rateInSimilarType && props.rateInSimilarType.length > 0
    )

    // 合并排名和百分比数据
    const combinedData = computed(() => {
      if (!hasRankingData.value) return []
      
      const percentMap = new Map()
      props.rateInSimilarPercent?.forEach(item => {
        percentMap.set(item[0], item[1])
      })

      return props.rateInSimilarType.map(item => ({
        ...item,
        percent: percentMap.get(item.x) || 0
      }))
    })

    // 最近10条记录用于表格显示
    const recentRankings = computed(() => {
      return combinedData.value.slice(-10).reverse()
    })

    const formatDate = (timestamp) => {
      return new Date(timestamp).toLocaleDateString('zh-CN')
    }

    const getPercentClass = (defeatPercent) => {
      // defeatPercent is 100 - rankPercent
      // higher is better
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

      // 准备排名百分比数据（Y轴反转，越小越好）
      const percentData = combinedData.value.map(item => [item.x, item.percent])

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const dataIndex = params[0].dataIndex
            const item = combinedData.value[dataIndex]
            const defeated = ((1 - item.y / item.sc) * 100).toFixed(2);
            return `
              <div style="font-weight: bold; margin-bottom: 8px;">${formatDate(item.x)}</div>
              <div>排名: <strong>${item.y}/${item.sc}</strong></div>
              <div>击败同类: <strong>${defeated}%</strong></div>
            `
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '10%',
          top: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'time',
          boundaryGap: false
        },
        yAxis: {
          type: 'value',
          name: '排名百分比(%)',
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
              { yAxis: 10, label: { formatter: '前10%' }, lineStyle: { color: '#52c41a', type: 'dashed' } },
              { yAxis: 25, label: { formatter: '前25%' }, lineStyle: { color: '#91cc75', type: 'dashed' } },
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
      getPercentClass
    }
  }
}
</script>

<style scoped>
.fund-ranking-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  margin-bottom: 24px;
}

.card-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 20px;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.card-body {
  padding: 24px;
}

.ranking-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.ranking-chart {
  width: 100%;
  height: 400px;
}

.ranking-table {
  overflow-x: auto;
}

.ranking-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.ranking-table th,
.ranking-table td {
  padding: 12px;
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
  color: #52c41a;
  font-weight: 600;
}

.good {
  color: #91cc75;
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
