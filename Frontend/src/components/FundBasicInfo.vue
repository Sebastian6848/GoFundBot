<template>
  <div v-if="fundInfo" class="fund-basic-info">
    <div class="info-header">
      <div class="header-left">
        <h2>{{ fundInfo.name || '未知基金' }}</h2>
        <span class="fund-code">{{ fundCode }}</span>
      </div>
      <div class="header-right">
        <div class="net-worth-box">
          <div class="label">单位净值</div>
          <div class="value">{{ fundInfo.dwjz || '--' }}</div>
          <div class="date">{{ formatDate(fundInfo.jzrq) }}</div>
        </div>
        <div class="estimate-box">
          <div class="label">估算净值</div>
          <div class="value" :class="getChangeClass(fundInfo.gszzl)">
            {{ fundInfo.gsz || '--' }}
          </div>
          <div class="change" :class="getChangeClass(fundInfo.gszzl)">
            {{ fundInfo.gszzl ? (fundInfo.gszzl > 0 ? '+' : '') + fundInfo.gszzl + '%' : '--' }}
          </div>
          <div class="time">{{ formatTime(fundInfo.gztime) }}</div>
        </div>
      </div>
    </div>
    
    <div class="info-metrics">
      <div class="metric-item">
        <div class="metric-label">近1月</div>
        <div class="metric-value" :class="getChangeClass(fundInfo.syl_1y)">
          {{ fundInfo.syl_1y ? (fundInfo.syl_1y > 0 ? '+' : '') + fundInfo.syl_1y + '%' : '--' }}
        </div>
      </div>
      <div class="metric-item">
        <div class="metric-label">近3月</div>
        <div class="metric-value" :class="getChangeClass(fundInfo.syl_3y)">
          {{ fundInfo.syl_3y ? (fundInfo.syl_3y > 0 ? '+' : '') + fundInfo.syl_3y + '%' : '--' }}
        </div>
      </div>
      <div class="metric-item">
        <div class="metric-label">近6月</div>
        <div class="metric-value" :class="getChangeClass(fundInfo.syl_6y)">
          {{ fundInfo.syl_6y ? (fundInfo.syl_6y > 0 ? '+' : '') + fundInfo.syl_6y + '%' : '--' }}
        </div>
      </div>
      <div class="metric-item">
        <div class="metric-label">近1年</div>
        <div class="metric-value" :class="getChangeClass(fundInfo.syl_1n)">
          {{ fundInfo.syl_1n ? (fundInfo.syl_1n > 0 ? '+' : '') + fundInfo.syl_1n + '%' : '--' }}
        </div>
      </div>
      <div class="metric-item">
        <div class="metric-label">现费率</div>
        <div class="metric-value rate">{{ fundInfo.fund_rate || fundInfo.fund_Rate ? (fundInfo.fund_rate || fundInfo.fund_Rate) + '%' : '--' }}</div>
      </div>
      <div class="metric-item">
        <div class="metric-label">最小申购</div>
        <div class="metric-value">{{ fundInfo.fund_minsg || fundInfo.fund_min_subscription ? (fundInfo.fund_minsg || fundInfo.fund_min_subscription) + '元' : '--' }}</div>
      </div>
    </div>
    
    <div v-if="loading" class="loading">加载中...</div>
  </div>
</template>

<script>
import { fundAPI } from '../services/api'

export default {
  name: 'FundBasicInfo',
  props: {
    fundCode: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      fundInfo: null,
      loading: false
    }
  },
  watch: {
    fundCode: {
      immediate: true,
      handler(newCode) {
        if (newCode) {
          this.fetchFundInfo()
        }
      }
    }
  },
  methods: {
    async fetchFundInfo() {
      this.loading = true
      try {
        const response = await fundAPI.getFundDetail(this.fundCode)
        // 合并 basic_info 到主对象
        this.fundInfo = {
          ...response.data,
          ...response.data.basic_info
        }
      } catch (error) {
        console.error('获取基金信息失败:', error)
        this.fundInfo = null
      } finally {
        this.loading = false
      }
    },
    getChangeClass(value) {
      if (!value) return ''
      const num = parseFloat(value)
      return num > 0 ? 'positive' : num < 0 ? 'negative' : ''
    },
    formatDate(dateStr) {
      if (!dateStr) return '--'
      return dateStr
    },
    formatTime(timeStr) {
      if (!timeStr) return '--'
      return timeStr
    }
  }
}
</script>

<style scoped>
.fund-basic-info {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  margin-bottom: 24px;
  color: white;
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.fund-code {
  background: rgba(255, 255, 255, 0.25);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
}

.header-right {
  display: flex;
  gap: 24px;
}

.net-worth-box,
.estimate-box {
  text-align: right;
}

.net-worth-box .label,
.estimate-box .label {
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 4px;
}

.net-worth-box .value,
.estimate-box .value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}

.net-worth-box .date {
  font-size: 11px;
  opacity: 0.8;
  margin-top: 4px;
}

.estimate-box .change {
  font-size: 16px;
  font-weight: 600;
  margin-top: 2px;
}

.estimate-box .time {
  font-size: 11px;
  opacity: 0.8;
  margin-top: 4px;
}

.info-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 16px;
}

.metric-item {
  background: rgba(255, 255, 255, 0.15);
  padding: 12px;
  border-radius: 8px;
  text-align: center;
  backdrop-filter: blur(10px);
}

.metric-label {
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
}

.metric-value.rate {
  color: #ffd700;
}

.positive {
  color: #ff6b6b; /* 上涨显示红色 */
}

.negative {
  color: #2ed573; /* 下跌显示绿色 */
}

.loading {
  text-align: center;
  padding: 20px;
  opacity: 0.8;
}
</style>