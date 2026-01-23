import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
});

export const uploadDocument = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const extractFacts = async (docId) => {
    // Note: The backend endpoint is /api/documents/{document_id}/extract-facts
    // But main.py uses post.
    const response = await api.post(`/documents/${docId}/extract-facts`);
    return response.data;
};

export const detectConflicts = async (docId) => {
    const response = await api.post(`/detect-conflicts/${docId}`);
    return response.data;
};

export const verifyFacts = async (docId) => {
    const response = await api.post(`/documents/${docId}/verify-facts`);
    return response.data;
};

/**
 * 订阅进度更新 (SSE)
 * @param {string} docId - 文档ID
 * @param {function} onProgress - 进度回调函数 (progressData) => void
 * @param {function} onError - 错误回调函数 (error) => void
 * @returns {function} 取消订阅函数
 */
export const subscribeProgress = (docId, onProgress, onError) => {
    const eventSource = new EventSource(`/api/progress/${docId}`);
    
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            onProgress(data);
            
            // 如果完成，自动关闭连接
            if (data.stage === 'complete') {
                eventSource.close();
            }
        } catch (e) {
            console.error('解析进度数据失败:', e);
        }
    };
    
    eventSource.onerror = (error) => {
        console.error('SSE 连接错误:', error);
        if (onError) {
            onError(error);
        }
        eventSource.close();
    };
    
    // 返回取消订阅函数
    return () => {
        eventSource.close();
    };
};

/**
 * 轮询获取进度状态（SSE 备选方案）
 * @param {string} docId - 文档ID
 * @returns {Promise} 进度状态
 */
export const getProgressStatus = async (docId) => {
    const response = await api.get(`/progress-status/${docId}`);
    return response.data;
};

/**
 * 保存分析结果到本地存储（历史记录）
 * @param {object} result - 分析结果
 * @param {string} type - 记录类型 ('single' | 'image' | 'multi')
 */
export const saveToHistory = (result, type = 'single') => {
    const history = JSON.parse(localStorage.getItem('factguardian_history') || '[]');
    
    let record = {
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        type: type
    };

    if (type === 'single') {
        record = {
            ...record,
            filename: result.docInfo?.filename || 'unknown',
            documentId: result.docInfo?.document_id,
            stats: result.stats,
            conflicts: result.conflicts,
            repetitions: result.repetitions || [],
            verifications: result.verifications
        };
    } else if (type === 'image') {
        record = {
            ...record,
            filename: result.image_info?.filename || 'image_analysis',
            image_info: result.image_info,
            comparisons: result.comparisons || [],
            description: result.description,
            mode: result.mode
        };
    } else if (type === 'multi') {
        record = {
            ...record,
            filename: result.main_filename || 'multi_doc_comparison',
            similarities: result.similarities || [],
            statistics: result.statistics
        };
    }

    history.unshift(record);
    // 只保留最近 50 条记录
    if (history.length > 50) {
        history.pop();
    }
    localStorage.setItem('factguardian_history', JSON.stringify(history));
    return record;
};

/**
 * 获取历史记录
 * @returns {Array} 历史记录列表
 */
export const getHistory = () => {
    return JSON.parse(localStorage.getItem('factguardian_history') || '[]');
};

/**
 * 删除历史记录
 * @param {string} id - 记录ID
 */
export const deleteFromHistory = (id) => {
    const history = JSON.parse(localStorage.getItem('factguardian_history') || '[]');
    const filtered = history.filter(h => h.id !== id);
    localStorage.setItem('factguardian_history', JSON.stringify(filtered));
    return filtered;
};

/**
 * 导出分析报告为 JSON
 * @param {object} data - 分析数据
 * @param {string} filename - 文件名
 */
export const exportReport = (data, filename) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}_report_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
};

export const uploadMultipleDocuments = async (mainFile, refFiles) => {
    const formData = new FormData();
    formData.append('main_doc', mainFile);
    refFiles.forEach((file) => {
        formData.append('ref_docs', file);
    });
    
    const response = await api.post('/upload-multiple', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const compareReferences = async (mainDocId, refDocIds, threshold = 0.3) => {
    const response = await api.post('/compare-references', {
        main_doc_id: mainDocId,
        ref_doc_ids: refDocIds,
        similarity_threshold: threshold
    });
    return response.data;
};

export const compareImageText = async (imageFile, docId = null, sections = null) => {
    const formData = new FormData();
    formData.append('file', imageFile);
    if (docId) formData.append('document_id', docId);
    if (sections) formData.append('relevant_sections', sections);

    const response = await api.post('/compare-image-text', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};
