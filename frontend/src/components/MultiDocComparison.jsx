import React, { useState, useEffect } from 'react';
import { Upload, FileText, GitCompare, CheckCircle, AlertTriangle, Loader2, ArrowRight } from 'lucide-react';
import { uploadMultipleDocuments, compareReferences, saveToHistory } from '../api';

export default function MultiDocComparison({ initialData, onHistoryUpdate }) {
    const [mainFile, setMainFile] = useState(null);
    const [refFiles, setRefFiles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    // Restore from history
    useEffect(() => {
        if (initialData) {
            setResult(initialData);
        }
    }, [initialData]);

    const handleMainFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setMainFile(e.target.files[0]);
        }
    };

    const handleRefFilesChange = (e) => {
        if (e.target.files) {
            setRefFiles(Array.from(e.target.files));
        }
    };

    const handleCompare = async () => {
        if (!mainFile || refFiles.length === 0) {
            setError("请上传主文档和至少一个参考文档");
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            // 1. Upload All Documents
            const uploadRes = await uploadMultipleDocuments(mainFile, refFiles);
            
            // 2. Perform Comparison
            const compareRes = await compareReferences(
                uploadRes.main_document_id,
                uploadRes.reference_document_ids
            );

            // Construct full result for history
            const fullResult = {
                ...compareRes,
                main_filename: mainFile.name,
                // We could also store ref filenames if we want, but they are in similarities often
            };

            setResult(fullResult);
            saveToHistory(fullResult, 'multi');
            if (onHistoryUpdate) onHistoryUpdate();
            
        } catch (err) {
            setError(err.response?.data?.detail || "对比失败");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto p-6">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
                <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <GitCompare className="text-indigo-500" />
                    多文档/参考验证
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-6">
                    {/* Main Document */}
                    <div>
                        <h3 className="font-semibold text-slate-700 mb-2">主文档 (待验证)</h3>
                        <div className="border-2 border-dashed border-indigo-200 bg-indigo-50/50 rounded-lg p-6 text-center hover:bg-indigo-50 transition-colors">
                            <input 
                                type="file" 
                                onChange={handleMainFileChange} 
                                className="hidden" 
                                id="main-doc-upload"
                            />
                            <label htmlFor="main-doc-upload" className="cursor-pointer block">
                                {mainFile ? (
                                    <div className="text-indigo-700 font-medium flex items-center justify-center gap-2">
                                        <FileText className="w-5 h-5" />
                                        {mainFile.name}
                                    </div>
                                ) : (
                                    <div className="text-slate-400">
                                        <Upload className="w-8 h-8 mx-auto mb-2 text-indigo-400" />
                                        <p>点击上传主文档</p>
                                    </div>
                                )}
                            </label>
                        </div>
                    </div>

                    {/* Reference Documents */}
                    <div>
                        <h3 className="font-semibold text-slate-700 mb-2">参考文档库 (多选)</h3>
                        <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:bg-slate-50 transition-colors">
                            <input 
                                type="file" 
                                multiple
                                onChange={handleRefFilesChange} 
                                className="hidden" 
                                id="ref-docs-upload"
                            />
                            <label htmlFor="ref-docs-upload" className="cursor-pointer block">
                                {refFiles.length > 0 ? (
                                    <div className="text-slate-700 font-medium">
                                        <FileText className="w-8 h-8 mx-auto mb-2 text-slate-500" />
                                        已选择 {refFiles.length} 个文件
                                        <p className="text-xs text-slate-500 mt-1">
                                            {refFiles.map(f => f.name).join(', ')}
                                        </p>
                                    </div>
                                ) : (
                                    <div className="text-slate-400">
                                        <Upload className="w-8 h-8 mx-auto mb-2" />
                                        <p>点击上传参考文档</p>
                                        <p className="text-xs mt-1">支持多选</p>
                                    </div>
                                )}
                            </label>
                        </div>
                    </div>
                </div>

                <div className="flex justify-center">
                    <button
                        onClick={handleCompare}
                        disabled={loading || !mainFile || refFiles.length === 0}
                        className="bg-indigo-600 text-white py-3 px-8 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium shadow-sm transition-all hover:shadow-md"
                    >
                        {loading ? <Loader2 className="animate-spin w-5 h-5" /> : <GitCompare className="w-5 h-5" />}
                        开始全库比对
                    </button>
                </div>

                {error && (
                    <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2 border border-red-100">
                        <AlertTriangle className="w-5 h-5" />
                        {error}
                    </div>
                )}
            </div>

            {/* Results */}
            {result && result.similarities && (
                <div className="space-y-6">
                    <div className="bg-slate-800 text-white p-6 rounded-xl shadow-lg flex justify-between items-center">
                        <div>
                            <h3 className="text-xl font-bold">比对完成</h3>
                            <p className="text-slate-400 text-sm mt-1">
                                共发现 <span className="text-white font-bold text-lg">{result.similarities.length}</span> 处相似段落
                            </p>
                        </div>
                        <div className="text-right">
                            <div className="text-3xl font-bold text-indigo-400">
                                {Math.max(0, ...result.similarities.map(s => s.similarity_score))}%
                            </div>
                            <div className="text-xs text-slate-400">最大相似度</div>
                        </div>
                    </div>

                    <div className="grid gap-6">
                        {result.similarities.map((sim, idx) => (
                            <div key={idx} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                                <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center">
                                    <span className="font-bold text-slate-700">相似点 #{idx + 1}</span>
                                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                                        sim.similarity_type === '直接引用' ? 'bg-blue-100 text-blue-700' :
                                        sim.similarity_type === '改写' ? 'bg-amber-100 text-amber-700' :
                                        'bg-slate-200 text-slate-600'
                                    }`}>
                                        {sim.similarity_type} ({sim.similarity_score}%)
                                    </span>
                                </div>
                                <div className="p-6 grid md:grid-cols-2 gap-6 relative">
                                    {/* Arrow icon in the middle */}
                                    <div className="hidden md:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-full p-2 border shadow-sm z-10">
                                        <ArrowRight className="text-slate-400 w-4 h-4" />
                                    </div>
                                    
                                    {/* Main Doc */}
                                    <div className="bg-red-50/50 p-4 rounded-lg border border-red-100">
                                        <div className="text-xs font-bold text-red-400 mb-2 uppercase tracking-wide">你的文档</div>
                                        <p className="text-slate-800 text-sm leading-relaxed whitespace-pre-wrap">
                                            {sim.main_section?.content || sim.main_text || '无内容'}
                                        </p>
                                    </div>

                                    {/* Ref Doc */}
                                    <div className="bg-green-50/50 p-4 rounded-lg border border-green-100">
                                        <div className="text-xs font-bold text-green-600 mb-2 uppercase tracking-wide">
                                            参考来源: {sim.reference_section?.filename || sim.ref_filename || '未知来源'}
                                        </div>
                                        <p className="text-slate-800 text-sm leading-relaxed whitespace-pre-wrap">
                                            {sim.reference_section?.content || sim.reference_text || '无内容'}
                                        </p>
                                    </div>
                                </div>
                                
                                <div className="px-6 py-4 bg-slate-50/80 border-t border-slate-100 text-sm text-slate-600 flex items-start gap-2">
                                     <CheckCircle className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                                     <div>
                                         <span className="font-semibold mr-2">分析结论:</span>
                                         {sim.reason}
                                     </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
