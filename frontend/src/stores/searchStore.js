import { defineStore } from 'pinia'
import { api } from '../api'

export const useSearchStore = defineStore('search', {
  state: () => ({
    // 当前概念
    currentConcept: '',
    
    // 学科列表 (完整对象格式，包含详情)
    disciplines: [],
    
    // 主学科
    primaryDiscipline: '',
    
    // 默认选中的学科ID列表
    defaultSelectedIds: [],
    
    // 建议添加的学科
    suggestedAdditions: [],
    
    // 分类加载状态
    isClassifying: false,
    classifyError: null,
    
    // 搜索任务相关
    currentTaskId: null,
    searchStatus: null, // 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
    searchProgress: {
      overall: 0,
      currentStage: 'pending',
      stages: {}
    },
    partialResults: {
      totalChunksFound: 0,
      validatedChunks: 0,
      byDiscipline: {}
    },
    
    // 搜索结果
    searchResults: null,
    
    // 搜索加载状态
    isSearching: false,
    searchError: null,
    
    // 用于取消请求
    classifyAbortController: null
  }),
  
  getters: {
    // 获取学科名称列表（兼容旧代码）
    disciplineNames: (state) => {
      return state.disciplines.map(d => 
        typeof d === 'string' ? d : d.name
      );
    },
    
    // 搜索是否正在进行
    isSearchInProgress: (state) => {
      return state.searchStatus === 'pending' || state.searchStatus === 'processing';
    },
    
    // 搜索是否完成
    isSearchComplete: (state) => {
      return state.searchStatus === 'completed';
    }
  },
  
  actions: {
    // 设置当前概念
    setConcept(concept) {
      this.currentConcept = concept;
    },
    
    // 设置学科列表（兼容字符串数组和对象数组）
    setDisciplines(list) {
      this.disciplines = list.map(item => 
        typeof item === 'string' 
          ? { id: item, name: item, relevance_score: 1.0, reason: '', search_keywords: [], is_primary: false }
          : item
      );
    },
    
    // 添加学科
    addDiscipline(item) {
      const name = typeof item === 'string' ? item : item.name;
      if (!this.disciplines.some(d => (typeof d === 'string' ? d : d.name) === name)) {
        if (typeof item === 'string') {
          this.disciplines.push({ 
            id: item, 
            name: item, 
            relevance_score: 1.0, 
            reason: '用户手动添加', 
            search_keywords: [], 
            is_primary: false 
          });
        } else {
          this.disciplines.push(item);
        }
      }
    },
    
    // 移除学科
    removeDiscipline(item) {
      const name = typeof item === 'string' ? item : item.name;
      this.disciplines = this.disciplines.filter(d => 
        (typeof d === 'string' ? d : d.name) !== name
      );
    },
    
    // 调用分类API
    async classifyConcept(concept, maxDisciplines = 8, minRelevance = 0.3, defaultSelected = 3) {
      // 如果有之前的请求，先取消
      if (this.classifyAbortController) {
        this.classifyAbortController.abort();
      }
      
      this.isClassifying = true;
      this.classifyAbortController = new AbortController();
      this.classifyError = null;
      
      try {
        const result = await api.classifyConcept(
          concept, 
          maxDisciplines, 
          minRelevance, 
          defaultSelected,
          { signal: this.classifyAbortController.signal }
        );
        
        this.currentConcept = result.concept;
        this.primaryDiscipline = result.primary_discipline;
        this.disciplines = result.disciplines;
        this.defaultSelectedIds = result.defaults || [];
        this.suggestedAdditions = result.suggested_additions || [];
        
        return result;
      } catch (error) {
        if (error.name === 'AbortError') {
          console.log('分类请求已取消');
          return;
        }
        this.classifyError = error.message;
        console.error('分类失败:', error);
        throw error;
      } finally {
        this.isClassifying = false;
        this.classifyAbortController = null;
      }
    },
    
    // 取消分类请求
    cancelClassification() {
      if (this.classifyAbortController) {
        this.classifyAbortController.abort();
        this.isClassifying = false;
        this.classifyAbortController = null;
      }
    },
    
    // 开始搜索
    async startSearch(searchConfig = {}) {
      if (!this.currentConcept || this.disciplines.length === 0) {
        throw new Error('请先设置概念和学科');
      }
      
      this.isSearching = true;
      this.searchError = null;
      this.searchResults = null;
      
      try {
        const result = await api.startSearch(
          this.currentConcept,
          this.disciplines,
          searchConfig
        );
        
        this.currentTaskId = result.task_id;
        this.searchStatus = result.status;
        
        return result;
      } catch (error) {
        this.searchError = error.message;
        console.error('启动搜索失败:', error);
        throw error;
      }
    },
    
    // 轮询搜索状态
    async pollSearchStatus() {
      if (!this.currentTaskId) {
        throw new Error('没有正在进行的搜索任务');
      }
      
      try {
        const status = await api.getSearchStatus(this.currentTaskId);
        
        this.searchStatus = status.status;
        this.searchProgress = {
          overall: status.progress.overall,
          currentStage: status.progress.current_stage,
          stages: status.progress.stages
        };
        this.partialResults = {
          totalChunksFound: status.partial_results.total_chunks_found,
          validatedChunks: status.partial_results.validated_chunks,
          byDiscipline: status.partial_results.by_discipline
        };
        
        return status;
      } catch (error) {
        console.error('获取搜索状态失败:', error);
        throw error;
      }
    },
    
    // 获取搜索结果
    async getSearchResults(options = {}) {
      if (!this.currentTaskId) {
        throw new Error('没有搜索任务');
      }
      
      try {
        const results = await api.getSearchResults(this.currentTaskId, options);
        this.searchResults = results;
        this.isSearching = false;
        return results;
      } catch (error) {
        console.error('获取搜索结果失败:', error);
        throw error;
      }
    },
    
    // 运行完整搜索流程（开始 + 轮询 + 获取结果）
    async runFullSearch(searchConfig = {}, onProgress) {
      // 开始搜索
      await this.startSearch(searchConfig);
      
      // 轮询直到完成
      const results = await api.pollSearchUntilComplete(
        this.currentTaskId,
        (status) => {
          // 更新本地状态
          this.searchStatus = status.status;
          this.searchProgress = {
            overall: status.progress.overall,
            currentStage: status.progress.current_stage,
            stages: status.progress.stages
          };
          this.partialResults = {
            totalChunksFound: status.partial_results.total_chunks_found,
            validatedChunks: status.partial_results.validated_chunks,
            byDiscipline: status.partial_results.by_discipline
          };
          
          if (onProgress) {
            onProgress(status);
          }
        }
      );
      
      this.searchResults = results;
      this.isSearching = false;
      
      return results;
    },
    
    // 取消搜索
    async cancelSearch() {
      if (!this.currentTaskId) {
        return;
      }
      
      try {
        await api.cancelSearch(this.currentTaskId);
        this.searchStatus = 'cancelled';
        this.isSearching = false;
      } catch (error) {
        console.error('取消搜索失败:', error);
        throw error;
      }
    },
    
    // 重置状态
    reset() {
      this.currentConcept = '';
      this.disciplines = [];
      this.primaryDiscipline = '';
      this.defaultSelectedIds = [];
      this.suggestedAdditions = [];
      this.isClassifying = false;
      this.classifyError = null;
      this.currentTaskId = null;
      this.searchStatus = null;
      this.searchProgress = { overall: 0, currentStage: 'pending', stages: {} };
      this.partialResults = { totalChunksFound: 0, validatedChunks: 0, byDiscipline: {} };
      this.searchResults = null;
      this.isSearching = false;
      this.searchError = null;
    }
  }
})
