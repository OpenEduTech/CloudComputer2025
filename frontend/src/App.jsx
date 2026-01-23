import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Layout, FileText, CheckCircle, Smartphone, Globe, ShieldAlert, History, Download, Trash2, Image, Files } from 'lucide-react';
import UploadSection from './components/UploadSection';
import ConflictList from './components/ConflictList';
import RepetitionList from './components/RepetitionList';
import VerificationResult from './components/VerificationResult';
import DocumentViewer from './components/DocumentViewer';
import FunLoading from './components/FunLoading';
import ImageTextComparison from './components/ImageTextComparison';
import MultiDocComparison from './components/MultiDocComparison';
import { 
    uploadDocument, 
    extractFacts, 
    detectConflicts, 
    verifyFacts,
    subscribeProgress,
    saveToHistory,
    getHistory,
    deleteFromHistory,
    exportReport
} from './api';

function App() {
  const [currentTab, setCurrentTab] = useState('single'); // single, image, multi
  const [status, setStatus] = useState('idle'); // idle, uploading, processing, done, error
  const [progressStep, setProgressStep] = useState('');
  const [progress, setProgress] = useState(null); // SSE 进度数据
  const [docId, setDocId] = useState(null);
  const [data, setData] = useState({
    docInfo: null,
    conflicts: [],
    repetitions: [],
    verifications: [],
    stats: {}
  });
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistoryState] = useState([]);
  const [historyTab, setHistoryTab] = useState('single');
  const [imageInitialData, setImageInitialData] = useState(null);
  const [multiInitialData, setMultiInitialData] = useState(null);
  
  // 用于跳转高亮的 ref
  const conflictRefs = useRef({});
  const verificationRefs = useRef({});
  const repetitionRefs = useRef({});
  
  // 取消订阅函数
  const unsubscribeRef = useRef(null);

  // 加载历史记录
  useEffect(() => {
    setHistoryState(getHistory());
  }, []);

  // 刷新历史记录
  const refreshHistory = () => {
    setHistoryState(getHistory());
  };

  // 处理高亮点击跳转
  const handleHighlightClick = useCallback((type, id) => {
    // type: 'conflict', 'verification' 或 'repetition'
    // id: 对应的 conflict_id 或 fact_id
    let targetRef;
    
    if (type === 'conflict') {
      targetRef = conflictRefs.current[id];
    } else if (type === 'verification' || type === 'error') {
      targetRef = verificationRefs.current[id];
    } else if (type === 'repetition') {
      targetRef = repetitionRefs.current[id];
    }
    
    if (targetRef) {
      targetRef.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // 添加高亮动画
      targetRef.classList.add('ring-4', 'ring-brand-400', 'ring-opacity-75');
      setTimeout(() => {
        targetRef.classList.remove('ring-4', 'ring-brand-400', 'ring-opacity-75');
      }, 2000);
    }
  }, []);

  const handleUpload = async (file) => {
    try {
      setStatus('uploading');
      setProgressStep('正在上传并解析文档结构...');
      setProgress(null);
      
      const uploadRes = await uploadDocument(file);
      setDocId(uploadRes.document_id);
      
      // Chain the analysis process
      setStatus('processing');
      
      // 订阅进度更新
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
      
      unsubscribeRef.current = subscribeProgress(
        uploadRes.document_id,
        (progressData) => {
          setProgress(progressData);
          setProgressStep(progressData.message);
        },
        (error) => {
          console.error('进度订阅错误:', error);
        }
      );
      
      setProgressStep('正在使用 LLM 提取关键事实 (Entity Extraction)...');
      const factRes = await extractFacts(uploadRes.document_id);
      
      setProgressStep('正在进行全文档逻辑矛盾检测 (Conflict Detection)...');
      const conflictRes = await detectConflicts(uploadRes.document_id);
      
      setProgressStep('正在联网进行事实溯源与校验 (Source Verification)...');
      const verifyRes = await verifyFacts(uploadRes.document_id);

      const resultData = {
        docInfo: uploadRes,
        conflicts: conflictRes.conflicts || [],
        repetitions: conflictRes.repetitions || [],
        verifications: verifyRes.verifications || [],
        stats: {
          totalFacts: factRes.total_facts,
          conflictCount: conflictRes.conflicts_found,
          repetitionCount: (conflictRes.repetitions || []).length,
          verifyFail: verifyRes.statistics?.unsupported || 0
        }
      };
      
      setData(resultData);
      
      // 保存到历史记录
      saveToHistory(resultData, 'single');
      setHistoryState(getHistory());
      
      // 取消订阅
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      
      setStatus('done');
      setProgress(null);
    } catch (error) {
      alert('处理失败: ' + (error.response?.data?.detail || error.message));
      setStatus('idle');
      setProgress(null);
      
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
    }
  };

  // 从历史记录恢复
  const handleRestoreHistory = (record) => {
    const type = record.type || 'single';

    if (type === 'single') {
        setData({
          docInfo: { 
            document_id: record.documentId, 
            filename: record.filename,
            sections: [] 
          },
          conflicts: record.conflicts || [],
          repetitions: record.repetitions || [], // Restore repetitions too
          verifications: record.verifications || [],
          stats: record.stats || {}
        });
        setDocId(record.documentId);
        setStatus('done');
        setCurrentTab('single');
    } else if (type === 'image') {
        setImageInitialData(record);
        setCurrentTab('image');
    } else if (type === 'multi') {
        setMultiInitialData(record);
        setCurrentTab('multi');
    }
    
    setShowHistory(false);
  };

  // 删除历史记录
  const handleDeleteHistory = (id, e) => {
    e.stopPropagation();
    const updated = deleteFromHistory(id);
    setHistoryState(updated);
  };

  // 导出报告
  const handleExport = () => {
    exportReport(data, data.docInfo?.filename || 'document');
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-brand-600 text-white p-1.5 rounded-lg">
              <ShieldAlert size={24} />
            </div>
            <h1 className="text-xl font-bold text-slate-800">FactGuardian <span className="text-slate-400 font-normal text-sm ml-2">长文本"事实卫士"</span></h1>
          </div>

           <div className="flex bg-slate-100 p-1 rounded-lg">
              <button 
                  onClick={() => setCurrentTab('single')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${currentTab === 'single' ? 'bg-white shadow text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
              >
                  单文档分析
              </button>
              <button 
                  onClick={() => setCurrentTab('image')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1 ${currentTab === 'image' ? 'bg-white shadow text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
              >
                  <Image size={14} /> 图文一致性
              </button>
              <button 
                  onClick={() => setCurrentTab('multi')}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1 ${currentTab === 'multi' ? 'bg-white shadow text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
              >
                  <Files size={14} /> 多文档/库
              </button>
           </div>

          <div className="flex items-center gap-4 text-sm font-medium text-slate-600">
            {/* 历史记录按钮 */}
            <button 
              onClick={() => setShowHistory(!showHistory)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <History size={18} />
              <span>历史记录</span>
              {history.length > 0 && (
                <span className="bg-brand-100 text-brand-700 text-xs px-1.5 py-0.5 rounded-full">{history.length}</span>
              )}
            </button>
            
            <div className="flex items-center gap-1.5">
               <span className={`w-2 h-2 rounded-full ${status === 'processing' ? 'bg-amber-500 animate-pulse' : 'bg-green-500'}`}></span>
               {status === 'processing' ? 'AI 分析中...' : '系统就绪'}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        
        {/* 历史记录面板 */}
        {showHistory && (
          <div className="mb-6 card animate-in fade-in slide-in-from-top-2 duration-300">

            {/* History Tabs */}
            <div className="flex border-b border-slate-200 mb-4">
                <button 
                    onClick={() => setHistoryTab('single')}
                    className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${historyTab === 'single' ? 'border-brand-600 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                >
                    单文档分析
                </button>
                <button 
                    onClick={() => setHistoryTab('image')}
                    className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${historyTab === 'image' ? 'border-brand-600 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                >
                    图文一致性
                </button>
                <button 
                    onClick={() => setHistoryTab('multi')}
                    className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${historyTab === 'multi' ? 'border-brand-600 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                >
                    多文档比对
                </button>
            </div>
            
            {history.filter(h => (h.type || 'single') === historyTab).length === 0 ? (
              <p className="text-slate-500 text-center py-8">该分类下暂无历史记录</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {history.filter(h => (h.type || 'single') === historyTab).map((record) => (
                  <div 
                    key={record.id}
                    onClick={() => handleRestoreHistory(record)}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 cursor-pointer transition-colors group"
                  >
                    <div className="flex-1">
                      <div className="font-medium text-slate-800">{record.filename}</div>
                      <div className="text-xs text-slate-500 flex items-center gap-2">
                        <span>{new Date(record.timestamp).toLocaleString('zh-CN')}</span>
                        
                        {/* Summary Badges based on Type */}
                        {(record.type === 'single' || !record.type) && (
                            <>
                                <span className="mx-1">·</span>
                                <span>{record.stats?.totalFacts || 0} 事实</span>
                                <span className={`px-1.5 py-0.5 rounded ${record.stats?.conflictCount > 0 ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}`}>
                                    {record.stats?.conflictCount || 0} 冲突
                                </span>
                            </>
                        )}
                        {record.type === 'image' && (
                            <>
                                <span className="mx-1">·</span>
                                <span className={`px-1.5 py-0.5 rounded ${(record.comparisons?.length || 0) > 0 ? 'bg-blue-100 text-blue-600' : 'bg-slate-200'}`}>
                                    {record.comparisons?.length || 0} 对比项
                                </span>
                            </>
                        )}
                        {record.type === 'multi' && (
                            <>
                                <span className="mx-1">·</span>
                                <span className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-600">
                                    {(record.similarities?.length || 0)} 相似点
                                </span>
                            </>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDeleteHistory(record.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-red-500 transition-all"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* TAB 1: Single Document Analysis */}
        {currentTab === 'single' && (
        <>
            {/* State: IDLE / UPLOADING */}
            {(status === 'idle' || status === 'uploading') && (
          <UploadSection onUpload={handleUpload} isUploading={status === 'uploading'} />
        )}

        {/* State: PROCESSING OVERLAY */}
        {status === 'processing' && (
          <FunLoading progressText={progressStep} progress={progress} />
        )}

        {/* State: RESULTS DASHBOARD */}
        {status === 'done' && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="card border-l-4 border-l-blue-500">
                <div className="text-slate-500 text-sm font-medium uppercase tracking-wider">提取事实</div>
                <div className="text-3xl font-bold text-slate-800 mt-1">{data.stats.totalFacts}</div>
                <div className="text-xs text-slate-400 mt-2">自 {data.docInfo.filename}</div>
              </div>
              <div className={`card border-l-4 ${data.stats.conflictCount > 0 ? 'border-l-amber-500' : 'border-l-green-500'}`}>
                <div className="text-slate-500 text-sm font-medium uppercase tracking-wider">冲突矛盾</div>
                <div className="text-3xl font-bold text-slate-800 mt-1">{data.stats.conflictCount}</div>
                <div className="text-xs text-slate-400 mt-2">{data.stats.conflictCount > 0 ? '需人工复核' : '全文档一致'}</div>
              </div>
              <div className={`card border-l-4 ${data.stats.repetitionCount > 0 ? 'border-l-purple-500' : 'border-l-green-500'}`}>
                <div className="text-slate-500 text-sm font-medium uppercase tracking-wider">重复核心</div>
                <div className="text-3xl font-bold text-slate-800 mt-1">{data.stats.repetitionCount}</div>
                <div className="text-xs text-slate-400 mt-2">{data.stats.repetitionCount > 0 ? '高频重复检测' : '无明显重复'}</div>
              </div>
              <div className={`card border-l-4 ${data.stats.verifyFail > 0 ? 'border-l-red-500' : 'border-l-green-500'}`}>
                <div className="text-slate-500 text-sm font-medium uppercase tracking-wider">事实谬误</div>
                <div className="text-3xl font-bold text-slate-800 mt-1">{data.stats.verifyFail}</div>
                <div className="text-xs text-slate-400 mt-2">联网查证发现错误</div>
              </div>
            </div>

            {/* Main Content Area - Split View */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 h-full">
              
              {/* Left Column: Document Viewer (Sticky) */}
              <div className="xl:sticky xl:top-24 h-fit min-h-[500px]">
                <DocumentViewer 
                    sections={data.docInfo.sections} 
                    conflicts={data.conflicts}
                    repetitions={data.repetitions}
                    verifications={data.verifications}
                    onHighlightClick={handleHighlightClick}
                />
              </div>

              {/* Right Column: Analysis Results */}
              <div className="space-y-8 pb-10">
                
                {/* 1. Doc Overview Card */}
                <div className="card bg-slate-800 text-white border-transparent">
                  <div className="flex justify-between items-start">
                    <div>
                        <h3 className="font-bold flex items-center gap-2 mb-2">
                            <FileText size={18} /> 文档分析概览
                        </h3>
                        <p className="text-slate-400 text-sm">{data.docInfo.filename}</p>
                    </div>
                    <div className="flex gap-2">
                      <button 
                          onClick={handleExport}
                          className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs transition-colors flex items-center gap-1"
                      >
                          <Download size={14} />
                          导出报告
                      </button>
                    </div>
                  </div>
                </div>

                {/* 2. Conflicts */}
                {data.stats.conflictCount > 0 && (
                   <div id="conflicts">
                      <ConflictList 
                        conflicts={data.conflicts} 
                        conflictRefs={conflictRefs}
                      />
                   </div>
                )}
                
                {/* 3. Repetitions */}
                {data.stats.repetitionCount > 0 && (
                   <div id="repetitions">
                      <RepetitionList repetitions={data.repetitions} repetitionRefs={repetitionRefs} />
                   </div>
                )}
                
                {/* 4. Verifications */}
                <div id="verifications">
                    <VerificationResult 
                      verifications={data.verifications}
                      verificationRefs={verificationRefs}
                    />
                </div>
              </div>

            </div>
          </div>
        )}
        </>
        )}

        {/* TAB 2: Image-Text Comparison */}
        {currentTab === 'image' && (
          <ImageTextComparison 
            currentDocId={docId} 
            initialData={imageInitialData} 
            onHistoryUpdate={refreshHistory}
          />
        )}

        {/* TAB 3: Multi-Doc Comparison */}
        {currentTab === 'multi' && (
          <MultiDocComparison 
            initialData={multiInitialData} 
            onHistoryUpdate={refreshHistory}
          />
        )}

      </main>
    </div>
  );
}

export default App;
