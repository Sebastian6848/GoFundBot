<template>
  <div class="fund-list-items" @dragover.prevent @drop="$emit('drop', $event, groupId)">
    <div
      v-for="(fund, index) in funds"
      :key="fund.fund_code"
      class="list-item"
      :class="{ 
        'selected': selectedFunds.includes(fund.fund_code),
        'dragging': isDragging(index),
        'in-compare': isInCompare(fund.fund_code)
      }"
      :draggable="editMode"
      @dragstart="$emit('drag-start', $event, index, groupId)"
      @dragend="$emit('drag-end')"
      @dragover="$emit('drag-over', $event, index, groupId)"
    >
      <!-- 编辑模式：选择框 -->
      <div class="col-checkbox" v-if="editMode">
        <input 
          type="checkbox" 
          :checked="selectedFunds.includes(fund.fund_code)"
          @change="$emit('toggle-select', fund.fund_code)"
          class="checkbox"
        />
      </div>
      
      <!-- 编辑模式：拖拽手柄 -->
      <div class="col-drag" v-if="editMode">
        <span class="drag-handle">⋮⋮</span>
      </div>

      <!-- 对比模式：添加按钮 -->
      <div class="col-compare" v-if="compareMode && !editMode">
        <button 
          class="btn-compare" 
          :class="{ 'in-compare': isInCompare(fund.fund_code) }"
          @click.stop="$emit('add-to-compare', { code: fund.fund_code, name: fund.fund_name })"
          :title="isInCompare(fund.fund_code) ? '已添加到对比' : '添加到对比'"
        >
          {{ isInCompare(fund.fund_code) ? '✓' : '+' }}
        </button>
      </div>

      <!-- 基金名称/代码 -->
      <div class="col-name" @click="!editMode && !compareMode && $emit('view-fund', fund.fund_code)">
        <div class="fund-name">{{ fund.fund_name }}</div>
        <div class="fund-code">{{ fund.fund_code }}</div>
      </div>

      <!-- 最新净值 -->
      <div class="col-nav">
        <div class="nav-value">{{ fund.net_worth || fund.estimate_value || '--' }}</div>
        <div class="nav-date">{{ fund.net_worth_date || fund.estimate_time || '' }}</div>
      </div>

      <!-- 日涨跌幅 -->
      <div class="col-change" :class="getChangeClass(fund.estimate_change)">
        {{ formatChange(fund.estimate_change) }}
      </div>

      <!-- 操作按钮 -->
      <div class="col-action" v-if="!editMode && !compareMode">
        <button class="btn-icon btn-remove" @click.stop="$emit('remove-fund', fund.fund_code)" title="移除">
          ✕
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FundListItems',
  props: {
    funds: { type: Array, default: () => [] },
    editMode: { type: Boolean, default: false },
    selectedFunds: { type: Array, default: () => [] },
    draggingIndex: { type: Object, default: null },
    groupId: { type: [Number, null], default: null },
    compareMode: { type: Boolean, default: false },
    compareFunds: { type: Array, default: () => [] }
  },
  emits: ['toggle-select', 'view-fund', 'remove-fund', 'drag-start', 'drag-end', 'drag-over', 'drop', 'add-to-compare'],
  methods: {
    isDragging(index) {
      return this.draggingIndex && 
             this.draggingIndex.index === index && 
             this.draggingIndex.groupId === this.groupId
    },
    isInCompare(fundCode) {
      return this.compareFunds && this.compareFunds.some(f => f.code === fundCode)
    },
    formatChange(change) {
      if (!change && change !== 0) return '--'
      const num = parseFloat(change)
      if (isNaN(num)) return change
      const sign = num > 0 ? '+' : ''
      return `${sign}${num.toFixed(2)}%`
    },
    getChangeClass(change) {
      if (!change && change !== 0) return ''
      const num = parseFloat(change)
      if (isNaN(num)) return ''
      if (num > 0) return 'change-up'
      if (num < 0) return 'change-down'
      return 'change-flat'
    }
  }
}
</script>

<style scoped>
.fund-list-items {
  min-height: 20px;
}

.list-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  gap: 8px;
  border-bottom: 1px solid #f3f4f6;
  transition: all 0.15s;
  cursor: pointer;
}

.list-item:last-child { border-bottom: none; }
.list-item:hover { background: #f9fafb; }
.list-item.selected { background: #eef2ff; }
.list-item.dragging { opacity: 0.5; background: #eef2ff; }

.col-checkbox { width: 24px; flex-shrink: 0; }
.col-drag { width: 20px; flex-shrink: 0; }
.col-compare { width: 28px; flex-shrink: 0; }
.col-name { flex: 1; min-width: 0; overflow: hidden; }
.col-nav { width: 65px; flex-shrink: 0; text-align: right; }
.col-change { width: 60px; flex-shrink: 0; text-align: right; font-weight: 600; font-size: 12px; }
.col-action { width: 30px; flex-shrink: 0; display: flex; justify-content: flex-end; }

.fund-name {
  color: #1f2937;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fund-code { color: #9ca3af; font-size: 11px; margin-top: 1px; }
.nav-value { color: #1f2937; font-size: 12px; font-weight: 500; }
.nav-date { color: #9ca3af; font-size: 10px; margin-top: 1px; }

.change-up { color: #ef4444; }
.change-down { color: #10b981; }
.change-flat { color: #9ca3af; }

.checkbox { width: 16px; height: 16px; cursor: pointer; accent-color: #667eea; }

.drag-handle { cursor: grab; color: #9ca3af; font-size: 14px; user-select: none; }
.drag-handle:active { cursor: grabbing; }

.btn-compare {
  width: 22px;
  height: 22px;
  border: 2px solid #667eea;
  border-radius: 50%;
  background: white;
  color: #667eea;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-compare:hover {
  background: #667eea;
  color: white;
}

.btn-compare.in-compare {
  background: #667eea;
  color: white;
}

.list-item.in-compare {
  background: #f0f5ff;
}

.btn-icon {
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  font-size: 11px;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover { background: #fee2e2; color: #ef4444; }
</style>
