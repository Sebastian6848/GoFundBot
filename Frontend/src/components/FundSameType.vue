<template>
  <div class="same-type-container">
    <div class="section-header">
      <h3>📈 同类型基金涨幅榜</h3>
      <div class="period-tabs">
        <button
          v-for="(period, index) in periods"
          :key="index"
          :class="['period-tab', { active: activePeriod === index }]"
          @click="activePeriod = index"
        >
          {{ period }}
        </button>
      </div>
    </div>

    <div class="fund-list" v-if="currentFunds.length > 0">
      <div
        v-for="(fund, index) in currentFunds"
        :key="fund.code"
        class="fund-item"
        @click="onFundClick(fund.code)"
      >
        <div class="rank" :class="getRankClass(index)">{{ index + 1 }}</div>
        <div class="fund-info">
          <div class="fund-name" :title="fund.name">{{ fund.name }}</div>
          <div class="fund-code">{{ fund.code }}</div>
        </div>
        <div class="return-rate" :class="getReturnClass(fund.return_rate)">
          {{ formatReturn(fund.return_rate) }}
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <span>暂无数据</span>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'FundSameType',
  props: {
    sameTypeFunds: {
      type: Array,
      default: () => []
    },
    isExpanded: {
      type: Boolean,
      default: false
    }
  },
  emits: ['fund-select'],
  setup(props, { emit }) {
    const activePeriod = ref(0)
    const periods = ['主题1', '主题2', '主题3', '主题4', '主题5']

    const currentFunds = computed(() => {
      if (!props.sameTypeFunds || !Array.isArray(props.sameTypeFunds)) {
        return []
      }
      return props.sameTypeFunds[activePeriod.value] || []
    })

    const getRankClass = (index) => {
      if (index === 0) return 'rank-1'
      if (index === 1) return 'rank-2'
      if (index === 2) return 'rank-3'
      return ''
    }

    const getReturnClass = (rate) => {
      const value = parseFloat(rate)
      return value >= 0 ? 'positive' : 'negative'
    }

    const formatReturn = (rate) => {
      const value = parseFloat(rate)
      if (isNaN(value)) return '--'
      const sign = value >= 0 ? '+' : ''
      return `${sign}${value.toFixed(2)}%`
    }

    const onFundClick = (code) => {
      emit('fund-select', code)
    }

    return {
      activePeriod,
      periods,
      currentFunds,
      getRankClass,
      getReturnClass,
      formatReturn,
      onFundClick
    }
  }
}
</script>

<style scoped>
.same-type-container {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
  --header-padding-right: v-bind(isExpanded ? '40px' : '0');
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
  /* 模态框模式下，顶部留出空间避免被关闭按钮遮挡 */
  padding-right: var(--header-padding-right, 0); 
}

.section-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.period-tabs {
  display: flex;
  gap: 4px;
}

.period-tab {
  padding: 4px 8px;
  font-size: 11px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background: white;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.period-tab:hover {
  border-color: #667eea;
  color: #667eea;
}

.period-tab.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.fund-list {
  flex: 1;
  overflow-y: auto;
}

.fund-item {
  display: flex;
  align-items: center;
  padding: 10px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}

.fund-item:hover {
  background: #f5f7fa;
}

.rank {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #999;
  background: #f0f0f0;
  margin-right: 10px;
  flex-shrink: 0;
}

.rank-1 {
  background: linear-gradient(135deg, #ffd700 0%, #ffb800 100%);
  color: white;
}

.rank-2 {
  background: linear-gradient(135deg, #c0c0c0 0%, #a8a8a8 100%);
  color: white;
}

.rank-3 {
  background: linear-gradient(135deg, #cd7f32 0%, #b8722b 100%);
  color: white;
}

.fund-info {
  flex: 1;
  min-width: 0;
  margin-right: 8px;
}

.fund-name {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fund-code {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.return-rate {
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.return-rate.positive {
  color: #e74c3c;
}

.return-rate.negative {
  color: #27ae60;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}

/* 滚动条样式 */
.fund-list::-webkit-scrollbar {
  width: 4px;
}

.fund-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 2px;
}

.fund-list::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 2px;
}

.fund-list::-webkit-scrollbar-thumb:hover {
  background: #999;
}
</style>
