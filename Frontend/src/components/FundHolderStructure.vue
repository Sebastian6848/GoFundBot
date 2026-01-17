<template>
  <div class="holder-structure-card">
    <div class="card-header">
      <h3>👥 持有人结构</h3>
    </div>
    <div class="card-body">
      <div v-if="hasData" class="holder-content">
        <div class="chart-container">
          <div ref="chartEl" class="holder-chart"></div>
        </div>
        <div class="holder-table">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th v-for="serie in series" :key="serie.name">
                  <span class="legend-dot" :style="{ background: getColor(serie.name) }"></span>
                  {{ formatLegendName(serie.name) }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(date, dateIndex) in categories" :key="dateIndex">
                <td class="date-cell">{{ date }}</td>
                <td v-for="serie in series" :key="serie.name" class="value-cell">
                  {{ formatValue(serie.data[dateIndex]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else class="no-data">
        <p>暂无持有人结构数据</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'FundHolderStructure',
  props: {
    holderStructure: {
      type: Object,
      default: () => ({})
    }
  },
  setup(props) {
    const chartEl = ref(null)
    let chartInstance = null

    const categories = computed(() => props.holderStructure?.categories || [])
    const series = computed(() => props.holderStructure?.series || [])
    const hasData = computed(() => categories.value.length > 0 && series.value.length > 0)

    const colors = {
      '机构持有比例': '#5470c6', // 蓝色
      '个人持有比例': '#ee6666', // 红色
      '内部持有比例': '#91cc75', // 绿色
      '机构持有': '#5470c6',
      '个人持有': '#ee6666',
      '内部持有': '#91cc75'
    }

    const getColor = (name) => {
      return colors[name] || '#5470c6'
    }

    const formatLegendName = (name) => {
      if (!name) return ''
      return name.replace(/比例/g, '')
    }

    const formatValue = (value) => {
      if (value === null || value === undefined) return '--'
      return value.toFixed(2) + '%'
    }

    const initChart = () => {
      if (!chartEl.value || !hasData.value) return

      if (chartInstance) {
        chartInstance.dispose()
      }

      chartInstance = echarts.init(chartEl.value)

      // 准备堆叠柱状图数据
      const seriesData = series.value.map(serie => ({
        name: formatLegendName(serie.name),
        type: 'bar',
        stack: 'total',
        barWidth: '50%',
        data: serie.data,
        itemStyle: {
          color: getColor(serie.name)
        },
        label: {
          show: true,
          position: 'inside',
          formatter: (params) => params.value > 10 ? params.value.toFixed(1) + '%' : ''
        }
      }))

      const option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          },
          formatter: (params) => {
            let result = `<div style="font-weight: bold; margin-bottom: 8px;">${params[0].axisValue}</div>`
            params.forEach(param => {
              result += `<div style="margin: 4px 0;">
                <span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:${param.color};"></span>
                ${param.seriesName}: <strong>${param.value?.toFixed(2) || '--'}%</strong>
              </div>`
            })
            return result
          }
        },
        legend: {
          data: series.value.map(s => formatLegendName(s.name)),
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: categories.value,
          axisLabel: {
            rotate: 30
          }
        },
        yAxis: {
          type: 'value',
          name: '占比(%)',
          max: 100,
          axisLabel: {
            formatter: '{value}%'
          }
        },
        series: seriesData
      }

      chartInstance.setOption(option)
    }

    onMounted(() => {
      nextTick(() => {
        initChart()
      })
    })

    watch(() => props.holderStructure, () => {
      nextTick(() => {
        initChart()
      })
    }, { deep: true })

    return {
      chartEl,
      categories,
      series,
      hasData,
      getColor,
      formatLegendName,
      formatValue
    }
  }
}
</script>

<style scoped>
.holder-structure-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 12px 16px;
  flex-shrink: 0;
}

.card-header h3 {
  margin: 0;
  color: white;
  font-size: 15px;
  font-weight: 600;
}

.card-body {
  padding: 12px;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.holder-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.chart-container {
  flex-shrink: 0;
}

.holder-chart {
  width: 100%;
  height: 240px;
}

.holder-table {
  flex: 1;
  overflow: auto;
  font-size: 12px;
}

.holder-table table {
  width: 100%;
  border-collapse: collapse;
}

.holder-table th,
.holder-table td {
  padding: 6px 8px;
  text-align: center;
  border-bottom: 1px solid #eee;
}

.holder-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #666;
  position: sticky;
  top: 0;
}

.holder-table th .legend-dot {
  display: inline-block;
  width: 8px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
}

.date-cell {
  font-weight: 500;
  color: #333;
}

.value-cell {
  color: #666;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #999;
}

@media (max-width: 768px) {
  .holder-chart {
    height: 250px;
  }
  
  .holder-table th,
  .holder-table td {
    padding: 8px 12px;
    font-size: 13px;
  }
}
</style>
