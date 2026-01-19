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
              :class="{ active: viewMode === 'screening' }"
              @click="viewMode = 'screening'"
            >
              🔍 基金筛选
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
        <!-- 左侧：自选列表 (非筛选模式显示) -->
        <aside class="sidebar-left" v-if="viewMode !== 'screening'">
          <FundWatchlist 
            @view-fund="handleFundSelected" 
            @add-to-compare="handleAddToCompare"
            :compareMode="viewMode === 'compare'"
            :compareFunds="compareFunds"
          />
        </aside>
        
        <!-- 右侧：根据模式显示不同内容 -->
        <div class="content-area" :class="{ 'full-width': viewMode === 'screening' }">
          <!-- 筛选模式 -->
          <template v-if="viewMode === 'screening'">
            <FundScreening 
              @view-fund="handleScreeningFundView"
              @add-to-compare="handleAddToCompare"
            />
          </template>
          
          <!-- 对比模式 -->
          <template v-else-if="viewMode === 'compare'">
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
            <div v-else class="welcome-container">
              <div class="welcome-header">
                <div class="welcome-icon">📊</div>
                <h2>GoFundBot 基金分析助手</h2>
                <p>您的专业基金投资顾问</p>
              </div>

              <div class="user-guide">
                <h3>📝 快速入门</h3>
                <div class="guide-steps">
                  <div class="step-item">
                    <div class="step-icon-wrapper">
                      <span class="step-icon">🔍</span>
                    </div>
                    <div class="step-content">
                      <h4>搜索基金</h4>
                      <p>输入代码/名称查找</p>
                    </div>
                  </div>
                  <div class="step-item">
                    <div class="step-icon-wrapper">
                      <span class="step-icon">📋</span>
                    </div>
                    <div class="step-content">
                      <h4>深度分析</h4>
                      <p>业绩、持仓与评级</p>
                    </div>
                  </div>
                  <div class="step-item">
                    <div class="step-icon-wrapper">
                      <span class="step-icon">⭐</span>
                    </div>
                    <div class="step-content">
                      <h4>自选管理</h4>
                      <p>定制关注列表</p>
                    </div>
                  </div>
                  <div class="step-item">
                    <div class="step-icon-wrapper">
                      <span class="step-icon">📈</span>
                    </div>
                    <div class="step-content">
                      <h4>多维对比</h4>
                      <p>全方位对比表现</p>
                    </div>
                  </div>
                </div>
              </div>
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
import FundScreening from './components/FundScreening.vue'

export default {
  name: 'App',
  components: {
    FundSearch,
    FundDetail,
    FundWatchlist,
    FundComparison,
    FundScreening
  },
  setup() {
    const selectedFundCode = ref('')
    const currentTime = ref('')
    const viewMode = ref('detail') // 'detail', 'screening' 或 'compare'
    const compareFunds = ref([]) // 用于对比的基金列表
    
    const handleFundSelected = (fundCode) => {
      selectedFundCode.value = fundCode
    }
    
    // 从筛选页面查看基金详情
    const handleScreeningFundView = (fundCode) => {
      selectedFundCode.value = fundCode
      viewMode.value = 'detail'
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
      handleScreeningFundView,
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

.content-area.full-width {
  width: 100%;
}

.welcome-container {
  text-align: center;
  padding: 60px 40px;
  color: #2c3e50;
  background: white;
  border-radius: 12px;
  margin-top: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.welcome-header {
  margin-bottom: 50px;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 20px;
  display: inline-block;
  background: #f0f4ff;
  width: 100px;
  height: 100px;
  line-height: 100px;
  border-radius: 50%;
}

.welcome-header h2 {
  font-size: 2rem;
  margin-bottom: 10px;
  color: #2d3748;
}

.welcome-header p {
  font-size: 1.1rem;
  color: #718096;
}

.user-guide {
  width: 100%;
  max-width: 900px;
}

.user-guide h3 {
  font-size: 1.2rem;
  margin-bottom: 30px;
  color: #4a5568;
  position: relative;
  display: inline-block;
}

.user-guide h3::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 3px;
  background: #667eea;
  border-radius: 2px;
}

.guide-steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.step-item {
  background: #f8fafc;
  padding: 25px 20px;
  border-radius: 12px;
  transition: all 0.3s;
  border: 1px solid transparent;
}

.step-item:hover {
  transform: translateY(-5px);
  background: white;
  border-color: #e2e8f0;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
}

.step-icon-wrapper {
  background: white;
  width: 60px;
  height: 60px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 15px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.step-item:hover .step-icon-wrapper {
  background: #667eea;
  transform: scale(1.1);
}

.step-icon {
  font-size: 28px;
}

.step-content h4 {
  font-size: 1.1rem;
  margin-bottom: 8px;
  color: #2d3748;
}

.step-content p {
  font-size: 0.9rem;
  color: #718096;
  line-height: 1.5;
}

@media (max-width: 768px) {
  .guide-steps {
    grid-template-columns: repeat(2, 1fr);
  }
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