
import React, { useState, useEffect } from 'react';
import { AppScreen, KeywordAnalysis, Discipline, DetailedExplanation, GraphData } from './types';
import { analyzeKeyword, fetchDisciplineDetail } from './geminiService';
import SearchScreen from './components/SearchScreen';
import ContextScreen from './components/ContextScreen';

const App: React.FC = () => {
  const [screen, setScreen] = useState<AppScreen>(AppScreen.SEARCH);
  const [keyword, setKeyword] = useState("");
  const [analysis, setAnalysis] = useState<KeywordAnalysis | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
 
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (val: string) => {
    if (!val.trim()) return;
    setLoading(true);
    setError(null);
    setKeyword(val);
    try {
      const result = await analyzeKeyword(val, true); // 强制刷新，总是调用AI生成
      setAnalysis(result.analysis);
      setGraphData(result.graphData);
      setScreen(AppScreen.CONTEXT);
    } catch (err) {
      console.error('搜索失败:', err);
      const errorMessage = err instanceof Error ? err.message : '未知错误';
      setError(`无法分析该词汇: ${errorMessage}。请确保后端服务已启动 (http://localhost:8080)。`);
    } finally {
      setLoading(false);
    }
  };

  const handleDisciplineClick = async (_discipline: Discipline) => {
    // popups removed — this handler intentionally left empty
    return;
  };


  const reset = () => {
    setScreen(AppScreen.SEARCH);
    setKeyword("");
    setAnalysis(null);
    setSelectedDiscipline(null);
    setDetails(null);
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#e5e2df]">
      {/* Background Decor */}
      <div className="absolute top-10 right-10 w-64 h-64 bg-slate-300/20 blur-3xl rounded-full -z-10" />
      <div className="absolute bottom-10 left-10 w-96 h-96 bg-stone-300/30 blur-3xl rounded-full -z-10" />

      {screen === AppScreen.SEARCH && (
        <SearchScreen onSearch={handleSearch} isLoading={loading} error={error} />
      )}

      {screen === AppScreen.CONTEXT && analysis && (
        <ContextScreen 
          analysis={analysis} 
          graphData={graphData}
          onDisciplineSelect={handleDisciplineClick}
          onBack={reset}
        />
      )}

      {loading && screen !== AppScreen.SEARCH && (
        <div className="fixed inset-0 bg-white/40 backdrop-blur-sm flex items-center justify-center z-[100]">
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 border-4 border-stone-300 border-t-stone-600 rounded-full animate-spin"></div>
            <p className="mt-4 text-stone-600 font-medium">深度解析中...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
