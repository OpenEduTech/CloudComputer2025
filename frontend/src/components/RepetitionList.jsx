import React from 'react';
import { Copy, MapPin } from 'lucide-react';

export default function RepetitionList({ repetitions, repetitionRefs }) {
    if (!repetitions || repetitions.length === 0) return null;

    return (
        <div className="space-y-6">
            <h3 className="text-lg font-bold flex items-center gap-2 text-slate-800">
                <Copy className="text-purple-500" />
                重复核心内容 ({repetitions.length})
            </h3>
            
            <div className="grid gap-4">
                {repetitions.map((rep, idx) => (
                    <div 
                        key={rep.conflict_id || idx}
                        ref={(el) => {
                            if (repetitionRefs) {
                                repetitionRefs.current[rep.conflict_id] = el;
                            }
                        }}
                        id={`repetition-${rep.conflict_id}`}
                        className="card border-l-4 border-l-purple-500 bg-white shadow-sm hover:shadow-md transition-all p-5 rounded-lg border border-slate-100"
                    >
                        <div className="flex justify-between items-start mb-4">
                            <div>
                                <span className="inline-block px-2 py-1 rounded text-xs font-bold mb-2 bg-purple-100 text-purple-700">
                                    高频重复
                                </span>
                            </div>
                            <div className="text-sm text-slate-400">ID: #{idx + 1}</div>
                        </div>

                        <div className="bg-slate-50 p-4 rounded-lg mb-4">
                            <div className="text-xs font-bold text-slate-400 mb-2">重复文本内容</div>
                            <div className="text-slate-800 font-medium leading-relaxed italic border-l-2 border-slate-300 pl-3">
                                "{rep.fact_a?.content || '未知内容'}"
                            </div>
                        </div>

                        <div className="flex items-start gap-3 mt-4 text-sm text-slate-600 bg-purple-50 p-3 rounded-md">
                             <MapPin className="w-4 h-4 text-purple-600 mt-0.5" />
                             <div>
                                 <span className="font-semibold text-purple-900 block mb-1">
                                     {rep.fact_b?.content || '重复统计'}
                                 </span>
                                 <p className="text-slate-600 text-xs">
                                     {rep.explanation}
                                 </p>
                             </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
