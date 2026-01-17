<template>
  <div class="portfolio-card">
    <div class="card-header">
      <h3>📈 持仓明细</h3>
    </div>
    <div class="card-body">
      <!-- 股票持仓 -->
      <div class="portfolio-content">
        <div v-if="hasStockData" class="stock-list">
          <div class="portfolio-header">
            <span class="col-rank">排名</span>
            <span class="col-code">代码</span>
            <span class="col-name">名称</span>
            <span class="col-market">交易所</span>
          </div>
          <div 
            v-for="(stock, index) in stockList" 
            :key="stock.code || index" 
            class="portfolio-item"
          >
            <span class="col-rank">{{ index + 1 }}</span>
            <span class="col-code">{{ stock.code }}</span>
            <span class="col-name">{{ stock.name }}</span>
            <span class="col-market">{{ stock.market || '--' }}</span>
          </div>
        </div>
        <div v-else class="no-data">
          <p>暂无股票持仓数据</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'FundPortfolio',
  props: {
    portfolio: {
      type: Object,
      default: () => ({})
    }
  },
  setup(props) {
    // 解析持仓数据
    const parseHoldings = (codes) => {
      if (!codes || !Array.isArray(codes)) return []
      
      // 如果数据已经是对象列表(新格式)，直接返回
      if (codes.length > 0 && typeof codes[0] === 'object' && codes[0] !== null) {
        return codes
      }

      const holdings = []
      // 旧格式: 每3个元素为一组: [代码, 名称, 占比]
      for (let i = 0; i < codes.length; i += 3) {
        if (i + 2 < codes.length) {
          holdings.push({
            code: codes[i],
            name: codes[i + 1],
            ratio: parseFloat(codes[i + 2]) || 0,
            market: '--'
          })
        }
      }
      return holdings
    }

    // 优先使用最新数据 (stock_codes_new)，否则使用旧数据
    const stockList = computed(() => {
      const newCodes = props.portfolio?.stock_codes_new
      const oldCodes = props.portfolio?.stock_codes
      return parseHoldings(newCodes?.length ? newCodes : oldCodes)
    })

    const hasStockData = computed(() => stockList.value.length > 0)

    return {
      stockList,
      hasStockData
    }
  }
}
</script>

<style scoped>
.portfolio-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.card-header h3 {
  margin: 0;
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.card-body {
  padding: 10px;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.portfolio-content {
  flex: 1;
  overflow-y: auto;
  padding-right: 12px;
}

.portfolio-header {
  display: flex;
  padding: 8px 0;
  border-bottom: 2px solid #eee;
  font-weight: 600;
  color: #666;
  font-size: 11px;
  position: sticky;
  top: 0;
  background: white;
}

.portfolio-item {
  display: flex;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  align-items: center;
  font-size: 12px;
}

.portfolio-item:hover {
  background: #f9f9f9;
}

.col-rank {
  width: 40px;
  text-align: center;
  color: #999;
  font-weight: 500;
  margin-right: 12px;
}

.portfolio-item .col-rank {
  width: 24px;
  height: 24px;
  line-height: 24px;
  background: #f0f0f0;
  border-radius: 50%;
  font-size: 11px;
  margin: 0 8px;
  display: inline-block;
  text-align: center;
}

.portfolio-item:nth-child(2) .col-rank { background: #ffd700; color: #fff; }
.portfolio-item:nth-child(3) .col-rank { background: #c0c0c0; color: #fff; }
.portfolio-item:nth-child(4) .col-rank { background: #cd7f32; color: #fff; }

.col-code {
  width: 60px;
  color: #667eea;
  font-family: monospace;
  font-size: 11px;
}

.col-name {
  flex: 1;
  color: #333;
  font-weight: 500;
  padding-right: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-market {
  width: 60px;
  text-align: left;
  color: #888;
  font-size: 11px;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
 