<!-- src/App.vue -->
<template>
  <div id="app">
    <header class="app-header">
      <div class="header-content">
        <div class="header-left">
          <h1>GoFundBot</h1>
          <p>一个有趣的基金分析机器人</p>
        </div>
        <!-- 模式切换 -->
        <div class="header-right">
          <div class="mode-switch">
            <button 
              class="mode-btn" 
              :class="{ active: viewMode === 'detail' }"
              @click="viewMode = 'detail'"
            >
              📋 基金详情
            </button>
            <button 
              class="mode-btn" 
              :class="{ active: viewMode === 'compare' }"
              @click="viewMode = 'compare'"
            >
              📈 基金对比
            </button>
          </div>
        </div>
      </div>
    </header>
    
    <main class="app-main">
      <div class="main-layout">
        <!-- 左侧：自选列表 -->
        <aside class="sidebar-left">
          <FundWatchlist 
            @view-fund="handleFundSelected" 
            @add-to-compare="handleAddToCompare"
            :compareMode="viewMode === 'compare'"
            :compareFunds="compareFunds"
          />
        </aside>
        
        <!-- 右侧：根据模式显示不同内容 -->
        <div class="content-area">
          <!-- 对比模式 -->
          <template v-if="viewMode === 'compare'">
            <FundComparison 
              :compareFunds="compareFunds"
              @remove-fund="handleRemoveFromCompare"
              @clear-funds="handleClearCompare"
            />
          </template>
          
          <!-- 详情模式 -->
          <template v-else>
            <FundSearch @fund-selected="handleFundSelected" />
            <FundDetail v-if="selectedFundCode" :fundCode="selectedFundCode" />
            <div v-else class="welcome">
              <div class="welcome-icon">📊</div>
              <p>请在搜索框中输入基金代码或名称</p>
              <p class="welcome-hint">或从左侧自选列表中选择基金开始分析</p>
            </div>
          </template>
        </div>
      </div>
    </main>
    
    <footer class="app-footer">
      <p>数据来源：天天基金 | 更新时间：{{ currentTime }}</p>
    </footer>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import FundSearch from './components/FundSearch.vue'
import FundDetail from './components/FundDetail.vue'
import FundWatchlist from './components/FundWatchlist.vue'
import FundComparison from './components/FundComparison.vue'

export default {
  name: 'App',
  components: {
    FundSearch,
    FundDetail,
    FundWatchlist,
    FundComparison
  },
  setup() {
    const selectedFundCode = ref('')
    const currentTime = ref('')
    const viewMode = ref('detail') // 'detail' 或 'compare'
    const compareFunds = ref([]) // 用于对比的基金列表
    
    const handleFundSelected = (fundCode) => {
      selectedFundCode.value = fundCode
    }
    
    // 添加基金到对比列表
    const handleAddToCompare = (fund) => {
      // 最多5只基金
      if (compareFunds.value.length >= 5) {
        alert('最多只能对比5只基金')
        return
      }
      // 检查是否已存在
      if (compareFunds.value.some(f => f.code === fund.code)) {
        // 如果已存在则移除
        compareFunds.value = compareFunds.value.filter(f => f.code !== fund.code)
        return
      }
      compareFunds.value.push({
        code: fund.code,
        name: fund.name
      })
    }
    
    // 从对比列表移除基金
    const handleRemoveFromCompare = (fundCode) => {
      compareFunds.value = compareFunds.value.filter(f => f.code !== fundCode)
    }
    
    // 清空对比列表
    const handleClearCompare = () => {
      compareFunds.value = []
    }
    
    // 更新时间
    const updateTime = () => {
      const now = new Date()
      currentTime.value = now.toLocaleString('zh-CN')
    }
    
    onMounted(() => {
      updateTime()
      // 每分钟更新时间
      setInterval(updateTime, 60000)
    })
    
    return {
      selectedFundCode,
      currentTime,
      viewMode,
      compareFunds,
      handleFundSelected,
      handleAddToCompare,
      handleRemoveFromCompare,
      handleClearCompare
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 15px 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left h1 {
  font-size: 1.8rem;
  margin-bottom: 2px;
}

.header-left p {
  opacity: 0.9;
  font-size: 0.9rem;
}

.header-right {
  display: flex;
  align-items: center;
}

.mode-switch {
  display: flex;
  gap: 8px;
  background: rgba(255, 255, 255, 0.15);
  padding: 4px;
  border-radius: 8px;
}

.mode-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  background: transparent;
  color: rgba(255, 255, 255, 0.8);
  transition: all 0.2s;
}

.mode-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.mode-btn.active {
  background: white;
  color: #667eea;
}

.app-main {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 20px;
}

/* 主布局：左侧自选 + 右侧内容 */
.main-layout {
  display: flex;
  gap: 20px;
  min-height: calc(100vh - 160px);
}

/* 左侧边栏 */
.sidebar-left {
  width: 360px;
  flex-shrink: 0;
}

/* 右侧内容区 */
.content-area {
  flex: 1;
  min-width: 0;
}

.welcome {
  text-align: center;
  padding: 80px 20px;
  color: #7f8c8d;
  background: white;
  border-radius: 12px;
  margin-top: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.welcome-icon {
  font-size: 48px;
  margin-bottom: 15px;
}

.welcome p {
  font-size: 1.1rem;
  margin-bottom: 8px;
}

.welcome-hint {
  font-size: 0.9rem !important;
  color: #9ca3af;
}

.app-footer {
  background: white;
  text-align: center;
  padding: 12px;
  border-top: 1px solid #e9ecef;
  font-size: 0.85rem;
  color: #6c757d;
}

/* 响应式：小屏幕时自选列表折叠或在上方 */
@media (max-width: 1024px) {
  .main-layout {
    flex-direction: column;
  }
  
  .sidebar-left {
    width: 100%;
  }
}
</style>