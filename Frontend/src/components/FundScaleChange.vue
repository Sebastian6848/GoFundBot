<template>
  <div class="fund-scale-card">
    <div class="card-header">
      <h3>📈 基金规模变动</h3>
    </div>
    <div class="card-body">
      <div v-if="hasData" class="scale-content">
        <div ref="chartEl" class="scale-chart"></div>
        <div class="scale-table">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>规模(亿元)</th>
                <th>环比变化</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in tableData" :key="index">
                <td>{{ categories[index] }}</td>
                <td class="scale-value">{{ item.y }}</td>
                <td class="mom-value" :class="getMomClass(item.mom)">
                  {{ item.mom }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else class="no-data">
        <p>暂无规模变动数据</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'FundScaleChange',
  props: {
    fluctuationScale: {
      type: Object,
      default: () => ({})
    }
  },
  setup(props) {
    const chartEl = ref(null)
    let chartInstance = null

    const categories = computed(() => props.fluctuationScale?.categories || [])
    const tableData = computed(() => props.fluctuationScale?.series || [])
    const hasData = computed(() => categories.value.length > 0 && tableData.value.length > 0)

    const getMomClass = (mom) => {
      if (!mom || mom === '--') return ''
      const value = parseFloat(mom)
      return value > 0 ? 'positive' : value < 0 ? 'negative' : ''
    }

    const initChart = () => {
      if (!chartEl.value || !hasData.value) return

      if (chartInstance) {
        chartInstance.dispose()
      }

      chartInstance = echarts.init(chartEl.value)

      const scaleData = tableData.value.map(item => item.y)

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const index = params[0].dataIndex
            const mom = tableData.value[index]?.mom || '--'
            return `
              <div style="font-weight: bold; margin-bottom: 8px;">${params[0].axisValue}</div>
              <div>规模: <strong>${params[0].value}亿元</strong></div>
              <div>环比: <strong>${mom}</strong></div>
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
          type: 'category',
          data: categories.value,
          axisLabel: {
            rotate: 30
          }
        },
        yAxis: {
          type: 'value',
          name: '规模(亿元)',
          axisLabel: {
            formatter: '{value}'
          }
        },
        series: [{
          name: '基金规模',
          type: 'bar',
          data: scaleData,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#667eea' },
              { offset: 1, color: '#764ba2' }
            ])
          },
          label: {
            show: true,
            position: 'top',
            formatter: '{c}亿'
          }
        }]
      }

      chartInstance.setOption(option)
    }

    onMounted(() => {
      nextTick(() => {
        initChart()
      })
    })

    watch(() => props.fluctuationScale, () => {
      nextTick(() => {
        initChart()
      })
    }, { deep: true })

    return {
      chartEl,
      categories,
      tableData,
      hasData,
      getMomClass
    }
  }
}
</script>

<style scoped>
.fund-scale-card {
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

.scale-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.scale-chart {
  width: 100%;
  height: 300px;
}

.scale-table {
  overflow-x: auto;
}

.scale-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.scale-table th,
.scale-table td {
  padding: 12px;
  text-align: center;
  border-bottom: 1px solid #e8e8e8;
}

.scale-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.scale-value {
  font-weight: 600;
  color: #333;
}

.mom-value {
  font-weight: 500;
}

.mom-value.positive {
  color: #ff4d4f;
}

.mom-value.negative {
  color: #52c41a;
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
