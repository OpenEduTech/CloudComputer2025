import React, { useState, useEffect } from 'react';
import { Upload, Image as ImageIcon, FileText, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { compareImageText, uploadDocument, saveToHistory } from '../api';

export default function ImageTextComparison({ currentDocId, initialData, onHistoryUpdate }) {
    const [imageFile, setImageFile] = useState(null);
    const [docFile, setDocFile] = useState(null);
    const [docId, setDocId] = useState(currentDocId || '');
    const [uploadMode, setUploadMode] = useState('id'); // 'id' or 'file'
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    // Restore from history
    useEffect(() => {
        if (initialData) {
            setResult(initialData);
            // Optionally set image info if available, but we can't restore the file object itself
        }
    }, [initialData]);

    const handleImageChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setImageFile(e.target.files[0]);
        }
    };

    const handleDocFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setDocFile(e.target.files[0]);
            // Clear ID if file is selected to avoid confusion, or keep it?
            // Let's keep ID separate.
        }
    };

    const handleCompare = async () => {
        if (!imageFile) {
            setError("请上传图片");
            return;
        }
        
        setLoading(true);
        setError(null);
        setResult(null);

        try {
            let targetDocId = docId;

            // Scenario 1: User uploaded a file directly
            if (uploadMode === 'file' && docFile) {
                 const uploadRes = await uploadDocument(docFile);
                 targetDocId = uploadRes.document_id;
            }

            // Scenario 2: User provided an ID (or we just got one)
            // If neither, targetDocId is empty -> Image extraction only

            const res = await compareImageText(imageFile, targetDocId);
            
            // Add mode info needed for history
            const finalResult = {
                ...res,
                mode: 'comparison'
            };
            
            setResult(finalResult);
            saveToHistory(finalResult, 'image');
            if (onHistoryUpdate) onHistoryUpdate();

        } catch (err) {
            setError(err.response?.data?.detail || "对比失败");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto p-6">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
                <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <ImageIcon className="text-blue-500" />
                    图文一致性对比
                </h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    {/* Image Upload */}
                    <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:bg-slate-50 transition-colors">
                        <input 
                            type="file" 
                            accept="image/*" 
                            onChange={handleImageChange} 
                            className="hidden" 
                            id="image-upload"
                        />
                        <label htmlFor="image-upload" className="cursor-pointer block">
                            {imageFile ? (
                                <div className="text-slate-700 font-medium break-all">
                                    <ImageIcon className="w-8 h-8 mx-auto mb-2 text-blue-500" />
                                    {imageFile.name}
                                </div>
                            ) : (
                                <div className="text-slate-400">
                                    <Upload className="w-8 h-8 mx-auto mb-2" />
                                    <p>点击上传图片</p>
                                    <p className="text-xs mt-1">支持 PNG, JPG, WEBP</p>
                                </div>
                            )}
                        </label>
                    </div>

                    {/* Document Input Section (Switchable) */}
                    <div className="flex flex-col">
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                            对比文档
                        </label>
                        
                        {/* Toggle Switches */}
                        <div className="flex bg-slate-100 p-1 rounded-lg mb-3">
                            <button
                                onClick={() => setUploadMode('id')}
                                className={`flex-1 py-1 text-xs font-medium rounded ${uploadMode === 'id' ? 'bg-white shadow text-slate-800' : 'text-slate-500'}`}
                            >
                                使用文档 ID
                            </button>
                            <button
                                onClick={() => setUploadMode('file')}
                                className={`flex-1 py-1 text-xs font-medium rounded ${uploadMode === 'file' ? 'bg-white shadow text-slate-800' : 'text-slate-500'}`}
                            >
                                直接上传文档
                            </button>
                        </div>

                        {uploadMode === 'id' ? (
                            <div className="flex flex-col gap-2 h-full justify-center">
                                <input
                                    type="text"
                                    value={docId}
                                    onChange={(e) => setDocId(e.target.value)}
                                    placeholder="输入文档 ID (如已上传)"
                                    className="w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
                                />
                                <p className="text-xs text-slate-500">
                                    如果不提供文档ID，将只提取图片内容。
                                </p>
                            </div>
                        ) : (
                            <div className="border-2 border-dashed border-slate-300 rounded-lg p-4 text-center hover:bg-slate-50 transition-colors h-full flex flex-col justify-center">
                                <input 
                                    type="file" 
                                    onChange={handleDocFileChange} 
                                    className="hidden" 
                                    id="doc-file-upload"
                                />
                                <label htmlFor="doc-file-upload" className="cursor-pointer block">
                                    {docFile ? (
                                        <div className="text-slate-700 font-medium break-all">
                                            <FileText className="w-6 h-6 mx-auto mb-1 text-indigo-500" />
                                            {docFile.name}
                                        </div>
                                    ) : (
                                        <div className="text-slate-400">
                                            <Upload className="w-6 h-6 mx-auto mb-1" />
                                            <p className="text-sm">点击上传文档</p>
                                            <p className="text-xs text-slate-500">
                                    如果不提供文档，将只提取图片内容。
                                </p>
                                        </div>
                                    )}
                                </label>
                            </div>
                        )}
                    </div>
                </div>

                <button
                    onClick={handleCompare}
                    disabled={loading || !imageFile}
                    className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    {loading ? <Loader2 className="animate-spin w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                    开始分析
                </button>

                {error && (
                    <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" />
                        {error}
                    </div>
                )}
            </div>

            {/* Results Display */}
            {result && (
                <div className="space-y-6">
                    {/* Image Description */}
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                        <h3 className="text-lg font-bold text-slate-800 mb-3 border-b pb-2">图片内容描述</h3>
                        <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">
                            {result.image_info?.description || result.description || '暂无描述'}
                        </p>
                    </div>

                    {/* Comparison Results */}
                    {result.mode === 'comparison' && result.comparisons && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-bold text-slate-800">对比详情</h3>
                            {result.comparisons.map((item, idx) => (
                                <div key={idx} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                                    <div className="flex justify-between items-center mb-4">
                                        <div className="px-3 py-1 bg-slate-100 rounded-full text-xs font-mono text-slate-500">
                                            章节: {item.section_title}
                                        </div>
                                        <div className={`px-3 py-1 rounded-full text-sm font-bold ${item.is_consistent ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                            一致性: {item.consistency_score}%
                                        </div>
                                    </div>
                                    
                                    {/* Issues */}
                                    <div className="grid md:grid-cols-2 gap-4">
                                        {item.contradictions && item.contradictions.length > 0 && (
                                            <div className="bg-red-50 p-4 rounded-lg">
                                                <h4 className="font-bold text-red-800 mb-2 flex items-center gap-2">
                                                    <AlertTriangle className="w-4 h-4" /> 矛盾点
                                                </h4>
                                                <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
                                                    {item.contradictions.map((c, i) => <li key={i}>{c}</li>)}
                                                </ul>
                                            </div>
                                        )}
                                        {item.missing_elements && item.missing_elements.length > 0 && (
                                            <div className="bg-amber-50 p-4 rounded-lg">
                                                <h4 className="font-bold text-amber-800 mb-2">遗漏元素</h4>
                                                <ul className="list-disc list-inside text-sm text-amber-700 space-y-1">
                                                    {item.missing_elements.map((m, i) => <li key={i}>{m}</li>)}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                    
                                    {/* Suggestions */}
                                    {item.suggestions && item.suggestions.length > 0 && (
                                        <div className="mt-4 bg-blue-50 p-4 rounded-lg">
                                            <h4 className="font-bold text-blue-800 mb-2">改进建议</h4>
                                            <ul className="list-disc list-inside text-sm text-blue-700 space-y-1">
                                                {item.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
