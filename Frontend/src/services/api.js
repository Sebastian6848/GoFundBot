import axios from 'axios'

// 使用相对路径，以便在开发环境中使用 Vite 代理，生产环境中使用 Nginx 代理
// 也可以通过环境变量 import.meta.env.VITE_API_BASE_URL 来配置
const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000
})

export const fundAPI = {
  // 搜索基金
  searchFunds(keyword) {
    return api.get(`/fund/search?q=${encodeURIComponent(keyword)}`)
  },
  
  // 获取搜索数据库状态
  getSearchStatus() {
    return api.get('/fund/search/status')
  },
  
  // 更新搜索数据库
  updateSearchDatabase() {
    return api.post('/fund/search/update')
  },
  
  // 获取基金详细信息
  getFundDetail(fundCode) {
    return api.get(`/fund/${fundCode}`)
  },
  
  // 获取基金基础信息
  getFundBasicInfo(fundCode) {
    return api.get(`/fund/${fundCode}/basic`)
  },
  
  // 获取基金走势数据
  getFundTrend(fundCode) {
    return api.get(`/fund/${fundCode}/trend`)
  },
  
  // 获取基金对比数据（带缓存，包含风险指标）
  getFundCompareData(fundCode, forceRefresh = false) {
    const params = forceRefresh ? '?refresh=true' : ''
    return api.get(`/fund/${fundCode}/compare-data${params}`)
  }
}

// ==================== 自选基金 API ====================
export const watchlistAPI = {
  // 获取自选列表（包含分组信息）
  getWatchlist() {
    return api.get('/watchlist')
  },
  
  // 检查基金是否在自选列表中
  checkInWatchlist(fundCode) {
    return api.get(`/watchlist/${fundCode}`)
  },
  
  // 添加基金到自选
  addToWatchlist(fundCode, fundName, fundType = '', groupId = null) {
    return api.post('/watchlist', {
      fund_code: fundCode,
      fund_name: fundName,
      fund_type: fundType,
      group_id: groupId
    })
  },
  
  // 从自选中移除
  removeFromWatchlist(fundCode) {
    return api.delete(`/watchlist/${fundCode}`)
  },
  
  // 批量删除
  batchDelete(fundCodes) {
    return api.post('/watchlist/batch-delete', {
      fund_codes: fundCodes
    })
  },
  
  // 更新排序 - 传入基金代码数组，顺序即为排序
  reorder(fundCodeOrder, groupId = null) {
    return api.put('/watchlist/reorder', {
      order: fundCodeOrder,
      group_id: groupId
    })
  },
  
  // 移动基金到分组
  moveFundToGroup(fundCode, groupId) {
    return api.put('/watchlist/move', {
      fund_code: fundCode,
      group_id: groupId
    })
  },
  
  // ==================== 分组 API ====================
  
  // 获取所有分组
  getGroups() {
    return api.get('/watchlist/groups')
  },
  
  // 创建分组
  createGroup(name) {
    return api.post('/watchlist/groups', { name })
  },
  
  // 重命名分组
  renameGroup(groupId, name) {
    return api.put(`/watchlist/groups/${groupId}`, { name })
  },
  
  // 删除分组
  deleteGroup(groupId) {
    return api.delete(`/watchlist/groups/${groupId}`)
  },
  
  // 分组排序
  reorderGroups(groupIdOrder) {
    return api.put('/watchlist/groups/reorder', {
      order: groupIdOrder
    })
  },
  
  // 刷新自选基金估值（实时估值更新）
  refreshEstimates() {
    return api.post('/watchlist/refresh-estimates')
  }
}

// ==================== 基金筛选 API ====================
export const screeningAPI = {
  // 获取筛选数据库状态
  getStatus() {
    return api.get('/screening/status')
  },
  
  // 启动数据更新（直接获取完整数据）
  startUpdate(options = {}) {
    return api.post('/screening/update', options)
  },
  
  // 停止更新
  stopUpdate() {
    return api.post('/screening/stop')
  },
  
  // 查询筛选基金
  query(params) {
    return api.post('/screening/query', params)
  },
  
  // 获取预设策略列表
  getStrategies() {
    return api.get('/screening/strategies')
  },
  
  // 获取可用的基金类型（根据当前筛选条件）
  getAvailableTypes(params) {
    return api.post('/screening/available-types', params)
  },
  
  // 获取单只基金筛选详情
  getFundDetail(fundCode) {
    return api.get(`/screening/fund/${fundCode}`)
  },
  
  // 更新单只基金筛选数据
  updateSingleFund(fundCode) {
    return api.post(`/screening/update-single/${fundCode}`)
  },
  
  // 重新计算同类型排名
  recalculateRankings() {
    return api.post('/screening/recalculate-rankings')
  }
}

// ==================== 基金回测 API ====================
export const backtestAPI = {
  // 定投回测
  fixedInvestment(data) {
    return api.post('/backtest/fixed-investment', data)
  }
}

export default api