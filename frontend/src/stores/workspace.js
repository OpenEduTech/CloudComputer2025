import { defineStore } from 'pinia'

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    fileId: '',
    userId: 'default',
    llmValidation: null,
    llmValidationOpen: false,
    llmValidationEnabled: true,
  }),
  actions: {
    setFileId(fileId) {
      this.fileId = fileId ? String(fileId).trim() : ''
    },
    setUserId(userId) {
      this.userId = userId ? String(userId).trim() : 'default'
    },
    setLlmValidation(payload) {
      this.llmValidation = payload || null
      this.llmValidationOpen = !!payload && this.llmValidationEnabled
    },
    closeLlmValidation() {
      this.llmValidationOpen = false
    },
    setLlmValidationEnabled(enabled) {
      this.llmValidationEnabled = !!enabled
      if (!enabled) this.llmValidationOpen = false
      try {
        localStorage.setItem('llm_validation_enabled', String(!!enabled))
      } catch (e) {
        // ignore
      }
    },
    initLlmValidationPreference() {
      try {
        const raw = localStorage.getItem('llm_validation_enabled')
        if (raw === null) return null
        this.llmValidationEnabled = raw === 'true'
        return this.llmValidationEnabled
      } catch (e) {
        return null
      }
    },
    clearFileId() {
      this.fileId = ''
    },
  },
})
