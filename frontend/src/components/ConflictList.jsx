import React, { useEffect } from 'react';
import { AlertCircle, ArrowRight, BookOpen, MousePointerClick } from 'lucide-react';

export default function ConflictList({ conflicts, conflictRefs }) {
    if (!conflicts || conflicts.length === 0) return null;

    return (
        <div className="space-y-6">
            <h3 className="text-lg font-bold flex items-center gap-2 text-slate-800">
                <AlertCircle className="text-amber-500" />
                检测到的矛盾 ({conflicts.length})
                <span className="text-xs font-normal text-slate-400 flex items-center gap-1">
                    <MousePointerClick className="w-3 h-3" />
                    点击左侧文档高亮可跳转
                </span>
            </h3>
            
            <div className="grid gap-4">
                {conflicts.map((conflict, idx) => (
                    <div 
                        key={conflict.conflict_id || idx} 
                        ref={(el) => {
                            if (conflictRefs) {
                                conflictRefs.current[conflict.conflict_id] = el;
                            }
                        }}
                        id={`conflict-${conflict.conflict_id}`}
                        className="card border-l-4 border-l-amber-500 transition-all duration-300"
                    >
                        <div className="flex justify-between items-start mb-4">
                            <div>
                                <span className={`inline-block px-2 py-1 rounded text-xs font-bold mb-2 
                                    ${conflict.severity === '高' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                                    {conflict.severity} 风险
                                </span>
                                <span className="ml-2 text-slate-500 text-sm">{conflict.conflict_type}</span>
                            </div>
                            <div className="text-sm text-slate-400">冲突 ID: #{idx + 1}</div>
                        </div>

                        <div className="grid md:grid-cols-2 gap-6 bg-slate-50 p-4 rounded-lg mb-4">
                            {/* Fact A */}
                            <div className="relative">
                                <div className="text-xs font-bold text-slate-400 mb-1">来源 A (前文)</div>
                                <div className="text-slate-800 font-medium">{conflict.fact_a?.content}</div>
                                <div className="flex items-center gap-1 mt-2 text-xs text-slate-500">
                                    <BookOpen className="w-3 h-3" />
                                    {conflict.fact_a?.location?.section_title || '未知章节'}
                                </div>
                            </div>

                            {/* Fact B */}
                            <div className="relative">
                                <div className="absolute left-[-1rem] top-1/2 -translate-y-1/2 hidden md:block">
                                    <ArrowRight className="text-slate-300" />
                                </div>
                                <div className="text-xs font-bold text-slate-400 mb-1">来源 B (后文)</div>
                                <div className="text-slate-800 font-medium">{conflict.fact_b?.content}</div>
                                <div className="flex items-center gap-1 mt-2 text-xs text-slate-500">
                                    <BookOpen className="w-3 h-3" />
                                    {conflict.fact_b?.location?.section_title || '未知章节'}
                                </div>
                            </div>
                        </div>

                        <div className="bg-white p-3 rounded border border-slate-100 text-sm text-slate-600">
                            <strong>AI 分析：</strong> {conflict.explanation}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
