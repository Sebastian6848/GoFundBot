<template>
  <div class="watchlist-container">
    <!-- 头部操作栏 -->
    <div class="watchlist-header">
      <h2>
        <span class="header-icon">⭐</span>
        我的自选
        <span class="count-badge" v-if="totalCount">{{ totalCount }}</span>
      </h2>
      <div class="header-actions">
        <button class="btn btn-add-group" @click="openAddGroupModal" title="新建分组">
          +📁
        </button>
        <button 
          v-if="!editMode && totalCount > 0" 
          class="btn btn-edit" 
          @click="enterEditMode"
        >
          编辑
        </button>
        <template v-if="editMode">
          <button 
            class="btn btn-danger" 
            :disabled="selectedFunds.length === 0"
            @click="batchDelete"
          >
            删除{{ selectedFunds.length > 0 ? `(${selectedFunds.length})` : '' }}
          </button>
          <button class="btn btn-secondary" @click="exitEditMode">
            完成
          </button>
        </template>
        <button class="btn btn-refresh" @click="refreshWatchlist" :disabled="loading" title="刷新">
          🔄
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && totalCount === 0" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="totalCount === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <p>暂无自选基金</p>
      <p class="empty-hint">在基金详情页点击 ⭐ 添加自选</p>
    </div>

    <!-- 分组列表 -->
    <div v-else class="watchlist-content">
      <!-- 未分组的基金 -->
      <div class="fund-group" v-if="ungroupedFunds.length > 0 || groups.length === 0">
        <div class="group-header" @click="toggleGroup(null)">
          <span class="group-toggle">{{ isGroupExpanded(null) ? '▼' : '▶' }}</span>
          <span class="group-name">{{ groups.length > 0 ? '未分组' : '全部基金' }}</span>
          <span class="group-count">{{ ungroupedFunds.length }}</span>
        </div>
        <div class="group-content" v-show="isGroupExpanded(null)">
          <FundListItems
            :funds="ungroupedFunds"
            :editMode="editMode"
            :selectedFunds="selectedFunds"
            :draggingIndex="draggingIndex"
            :groupId="null"
            :compareMode="compareMode"
            :compareFunds="compareFunds"
            @toggle-select="toggleSelect"
            @view-fund="viewFundDetail"
            @remove-fund="removeFund"
            @drag-start="onDragStart"
            @drag-end="onDragEnd"
            @drag-over="onDragOver"
            @drop="onDrop"
            @add-to-compare="addToCompare"
          />
        </div>
      </div>

      <!-- 各分组 -->
      <div 
        v-for="group in groups" 
        :key="group.id" 
        class="fund-group"
        @dragover.prevent="onGroupDragOver($event, group.id)"
        @drop="onGroupDrop($event, group.id)"
      >
        <div class="group-header" @click="toggleGroup(group.id)">
          <span class="group-toggle">{{ isGroupExpanded(group.id) ? '▼' : '▶' }}</span>
          <span class="group-name">📁 {{ group.name }}</span>
          <span class="group-count">{{ getGroupFunds(group.id).length }}</span>
          <div class="group-actions" v-if="editMode" @click.stop>
            <button class="btn-icon-sm" @click="openEditGroupModal(group)" title="重命名">✏️</button>
            <button class="btn-icon-sm btn-del" @click="deleteGroup(group)" title="删除分组">🗑️</button>
          </div>
        </div>
        <div class="group-content" v-show="isGroupExpanded(group.id)">
          <FundListItems
            :funds="getGroupFunds(group.id)"
            :editMode="editMode"
            :selectedFunds="selectedFunds"
            :draggingIndex="draggingIndex"
            :groupId="group.id"
            :compareMode="compareMode"
            :compareFunds="compareFunds"
            @toggle-select="toggleSelect"
            @view-fund="viewFundDetail"
            @remove-fund="removeFund"
            @drag-start="onDragStart"
            @drag-end="onDragEnd"
            @drag-over="onDragOver"
            @drop="onDrop"
            @add-to-compare="addToCompare"
          />
          <div v-if="getGroupFunds(group.id).length === 0" class="group-empty">
            暂无基金，拖拽基金到此分组
          </div>
        </div>
      </div>
    </div>

    <!-- 新建/编辑分组弹窗 -->
    <div v-if="showGroupModal" class="modal-overlay" @click.self="closeGroupModal">
      <div class="modal-box">
        <h3>{{ editingGroup ? '重命名分组' : '新建分组' }}</h3>
        <input 
          v-model="groupName" 
          type="text" 
          placeholder="请输入分组名称"
          class="modal-input"
          @keyup.enter="saveGroup"
          ref="groupNameInput"
        />
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeGroupModal">取消</button>
          <button class="btn btn-primary" @click="saveGroup" :disabled="!groupName.trim()">
            {{ editingGroup ? '保存' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick, toRef } from 'vue'
import { watchlistAPI } from '../services/api'
import FundListItems from './FundListItems.vue'

export default {
  name: 'FundWatchlist',
  components: { FundListItems },
  props: {
    compareMode: { type: Boolean, default: false },
    compareFunds: { type: Array, default: () => [] }
  },
  emits: ['view-fund', 'add-to-compare'],
  setup(props, { emit }) {
    const watchlist = ref([])
    const groups = ref([])
    const loading = ref(false)
    const editMode = ref(false)
    const selectedFunds = ref([])
    const draggingIndex = ref(null)
    const dragOverIndex = ref(null)
    const expandedGroups = ref([null])
    const isInitialLoad = ref(true)
    
    // 分组弹窗
    const showGroupModal = ref(false)
    const editingGroup = ref(null)
    const groupName = ref('')
    const groupNameInput = ref(null)

    // 计算属性
    const totalCount = computed(() => watchlist.value.length)
    
    const ungroupedFunds = computed(() => 
      watchlist.value.filter(f => !f.group_id)
    )
    
    const getGroupFunds = (groupId) => {
      return watchlist.value.filter(f => f.group_id === groupId)
    }
    
    const isGroupExpanded = (groupId) => {
      return expandedGroups.value.includes(groupId)
    }

    // 加载数据
    const loadWatchlist = async () => {
      loading.value = true
      try {
        const response = await watchlistAPI.getWatchlist()
        watchlist.value = response.data.data || []
        groups.value = response.data.groups || []
        // 仅首次加载时展开所有分组，后续刷新保持用户的折叠状态
        if (isInitialLoad.value) {
          expandedGroups.value = [null, ...groups.value.map(g => g.id)]
          isInitialLoad.value = false
        } else {
          // 移除已删除分组的展开状态，添加新分组到展开列表
          const validGroupIds = new Set([null, ...groups.value.map(g => g.id)])
          expandedGroups.value = expandedGroups.value.filter(id => validGroupIds.has(id))
        }
      } catch (error) {
        console.error('加载自选列表失败:', error)
      } finally {
        loading.value = false
      }
    }

    const refreshWatchlist = () => loadWatchlist()

    // 分组展开/折叠
    const toggleGroup = (groupId) => {
      const index = expandedGroups.value.indexOf(groupId)
      if (index > -1) {
        expandedGroups.value.splice(index, 1)
      } else {
        expandedGroups.value.push(groupId)
      }
    }

    // 编辑模式
    const enterEditMode = () => {
      editMode.value = true
      selectedFunds.value = []
    }

    const exitEditMode = () => {
      editMode.value = false
      selectedFunds.value = []
    }

    // 选择基金
    const toggleSelect = (fundCode) => {
      const index = selectedFunds.value.indexOf(fundCode)
      if (index > -1) {
        selectedFunds.value.splice(index, 1)
      } else {
        selectedFunds.value.push(fundCode)
      }
    }

    // 批量删除
    const batchDelete = async () => {
      if (selectedFunds.value.length === 0) return
      if (!confirm(`确定删除选中的 ${selectedFunds.value.length} 只基金吗？`)) return

      try {
        await watchlistAPI.batchDelete(selectedFunds.value)
        watchlist.value = watchlist.value.filter(
          f => !selectedFunds.value.includes(f.fund_code)
        )
        selectedFunds.value = []
        if (watchlist.value.length === 0) exitEditMode()
      } catch (error) {
        console.error('批量删除失败:', error)
        alert('删除失败，请重试')
      }
    }

    // 移除单个
    const removeFund = async (fundCode) => {
      if (!confirm('确定移除该基金吗？')) return
      try {
        await watchlistAPI.removeFromWatchlist(fundCode)
        watchlist.value = watchlist.value.filter(f => f.fund_code !== fundCode)
      } catch (error) {
        console.error('移除失败:', error)
      }
    }

    // 查看详情
    const viewFundDetail = (fundCode) => {
      emit('view-fund', fundCode)
    }

    // 添加到对比
    const addToCompare = (fund) => {
      emit('add-to-compare', fund)
    }

    // 拖拽排序
    const onDragStart = (event, index, groupId) => {
      draggingIndex.value = { index, groupId }
      event.dataTransfer.effectAllowed = 'move'
    }

    const onDragEnd = async () => {
      if (draggingIndex.value !== null && dragOverIndex.value !== null) {
        const fromGroupId = draggingIndex.value.groupId
        const toGroupId = dragOverIndex.value.groupId
        const fromFunds = fromGroupId === null ? ungroupedFunds.value : getGroupFunds(fromGroupId)
        
        // 防御性检查：确保源列表存在
        if (!fromFunds) {
          draggingIndex.value = null
          dragOverIndex.value = null
          return
        }

        if (fromGroupId === toGroupId) {
          // 优化：位置没变不需要请求
          if (draggingIndex.value.index === dragOverIndex.value.index) {
            draggingIndex.value = null
            dragOverIndex.value = null
            return
          }

          // 同分组内排序
          const funds = [...fromFunds]
          // 确保索引在有效范围内
          if (draggingIndex.value.index >= 0 && draggingIndex.value.index < funds.length) {
            const [moved] = funds.splice(draggingIndex.value.index, 1)
            
            // 确保移动的对象存在
            if (moved) {
              funds.splice(dragOverIndex.value.index, 0, moved)
              try {
                await watchlistAPI.reorder(funds.map(f => f.fund_code), fromGroupId)
                loadWatchlist()
              } catch (error) {
                console.error('排序失败:', error)
              }
            }
          }
        } else {
          // 跨分组移动
          const fund = fromFunds[draggingIndex.value.index]
          if (fund) {
            try {
              await watchlistAPI.moveFundToGroup(fund.fund_code, toGroupId)
              loadWatchlist()
            } catch (error) {
              console.error('移动失败:', error)
            }
          }
        }
      }
      
      draggingIndex.value = null
      dragOverIndex.value = null
    }

    const onDragOver = (event, index, groupId) => {
      event.preventDefault()
      dragOverIndex.value = { index, groupId }
    }

    const onDrop = (event, groupId) => {
      event.preventDefault()
    }
    
    // 拖拽到分组区域
    const onGroupDragOver = (event, groupId) => {
      event.preventDefault()
    }
    
    const onGroupDrop = async (event, groupId) => {
      event.preventDefault()
      if (draggingIndex.value && draggingIndex.value.groupId !== groupId) {
        const fromFunds = draggingIndex.value.groupId === null 
          ? ungroupedFunds.value 
          : getGroupFunds(draggingIndex.value.groupId)
        const fund = fromFunds[draggingIndex.value.index]
        
        try {
          await watchlistAPI.moveFundToGroup(fund.fund_code, groupId)
          loadWatchlist()
        } catch (error) {
          console.error('移动失败:', error)
        }
      }
      draggingIndex.value = null
      dragOverIndex.value = null
    }

    // 分组管理
    const openAddGroupModal = () => {
      editingGroup.value = null
      groupName.value = ''
      showGroupModal.value = true
      nextTick(() => groupNameInput.value?.focus())
    }
    
    const openEditGroupModal = (group) => {
      editingGroup.value = group
      groupName.value = group.name
      showGroupModal.value = true
      nextTick(() => groupNameInput.value?.focus())
    }
    
    const closeGroupModal = () => {
      showGroupModal.value = false
      editingGroup.value = null
      groupName.value = ''
    }

    const saveGroup = async () => {
      const name = groupName.value.trim()
      if (!name) return

      try {
        if (editingGroup.value) {
          await watchlistAPI.renameGroup(editingGroup.value.id, name)
        } else {
          const response = await watchlistAPI.createGroup(name)
          // 新创建的分组自动展开
          if (response.data && response.data.id) {
            expandedGroups.value.push(response.data.id)
          }
        }
        closeGroupModal()
        loadWatchlist()
      } catch (error) {
        console.error('保存分组失败:', error)
        alert('操作失败，请重试')
      }
    }

    const deleteGroup = async (group) => {
      if (!confirm(`确定删除分组"${group.name}"吗？\n分组内的基金将移到未分组。`)) return
      try {
        await watchlistAPI.deleteGroup(group.id)
        loadWatchlist()
      } catch (error) {
        console.error('删除分组失败:', error)
      }
    }

    onMounted(() => {
      loadWatchlist()
    })

    return {
      watchlist,
      groups,
      loading,
      editMode,
      selectedFunds,
      draggingIndex,
      expandedGroups,
      totalCount,
      ungroupedFunds,
      getGroupFunds,
      isGroupExpanded,
      showGroupModal,
      editingGroup,
      groupName,
      groupNameInput,
      compareMode: toRef(props, 'compareMode'),
      compareFunds: toRef(props, 'compareFunds'),
      loadWatchlist,
      refreshWatchlist,
      toggleGroup,
      enterEditMode,
      exitEditMode,
      toggleSelect,
      batchDelete,
      removeFund,
      viewFundDetail,
      addToCompare,
      onDragStart,
      onDragEnd,
      onDragOver,
      onDrop,
      onGroupDragOver,
      onGroupDrop,
      openAddGroupModal,
      openEditGroupModal,
      closeGroupModal,
      saveGroup,
      deleteGroup
    }
  }
}
</script>

<style scoped>
.watchlist-container {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 头部 */
.watchlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
  flex-wrap: wrap;
  gap: 8px;
}

.watchlist-header h2 {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 16px;
  color: #1f2937;
  font-weight: 600;
}

.header-icon { font-size: 18px; }

.count-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.header-actions {
  display: flex;
  gap: 6px;
}

/* 按钮 */
.btn {
  padding: 5px 10px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-add-group { background: #f0fdf4; color: #16a34a; }
.btn-add-group:hover { background: #dcfce7; }
.btn-edit { background: #f3f4f6; color: #667eea; }
.btn-edit:hover { background: #e5e7eb; }
.btn-danger { background: #fef2f2; color: #ef4444; }
.btn-danger:hover:not(:disabled) { background: #fee2e2; }
.btn-secondary { background: #f3f4f6; color: #374151; }
.btn-secondary:hover { background: #e5e7eb; }
.btn-refresh { background: #ecfdf5; color: #10b981; padding: 5px 8px; }
.btn-refresh:hover:not(:disabled) { background: #d1fae5; }
.btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
.btn-primary:hover:not(:disabled) { opacity: 0.9; }

/* 状态 */
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 15px;
  color: #9ca3af;
  flex: 1;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-icon { font-size: 36px; margin-bottom: 10px; }
.empty-state p { margin: 0; font-size: 14px; color: #6b7280; }
.empty-hint { font-size: 12px !important; color: #9ca3af !important; margin-top: 6px !important; }

/* 列表内容 */
.watchlist-content {
  flex: 1;
  overflow-y: auto;
}

/* 分组 */
.fund-group {
  margin-bottom: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.group-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #f9fafb;
  cursor: pointer;
  gap: 8px;
  user-select: none;
}

.group-header:hover { background: #f3f4f6; }

.group-toggle {
  font-size: 10px;
  color: #9ca3af;
  width: 12px;
}

.group-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.group-count {
  font-size: 11px;
  color: #9ca3af;
  background: #e5e7eb;
  padding: 1px 6px;
  border-radius: 8px;
}

.group-actions {
  display: flex;
  gap: 4px;
}

.btn-icon-sm {
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 11px;
  border-radius: 4px;
}

.btn-icon-sm:hover { background: #e5e7eb; }
.btn-icon-sm.btn-del:hover { background: #fee2e2; }

.group-content {
  border-top: 1px solid #e5e7eb;
}

.group-empty {
  padding: 20px;
  text-align: center;
  color: #9ca3af;
  font-size: 12px;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: white;
  padding: 20px;
  border-radius: 12px;
  width: 300px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-box h3 {
  margin: 0 0 15px;
  font-size: 16px;
  color: #1f2937;
}

.modal-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 15px;
  box-sizing: border-box;
}

.modal-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

/* 滚动条 */
.watchlist-content::-webkit-scrollbar { width: 6px; }
.watchlist-content::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
.watchlist-content::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 3px; }
.watchlist-content::-webkit-scrollbar-thumb:hover { background: #a1a1a1; }
</style>
