import React from 'react';
import { CheckCircle2, XCircle, Search, HelpCircle, ExternalLink, MousePointerClick } from 'lucide-react';

export default function VerificationResult({ verifications, verificationRefs }) {
    if (!verifications || verifications.length === 0) return null;

    // Filter to show errors first
    const sortedVerifications = [...verifications]
        // Filter out internal/skipped facts as requested by user
        .filter(v => {
            const isInternal = v.original_fact?.verifiable_type === 'internal';
            const isSkipped = v.skipped === true;
            // Only verify visible items (public facts usually)
            // But if it's "skipped" because of internal, filter it out.
            // If it's supported/unsupported, show it.
            // But user said: "marked as internal information parts do not need to be displayed"
            return !isInternal;
        })
        .sort((a, b) => {
            if (a.is_supported === false && b.is_supported !== false) return -1;
            if (a.is_supported !== false && b.is_supported === false) return 1;
            return 0;
        });

    if (sortedVerifications.length === 0) return (
        <div className="card text-center py-8 text-slate-500">
             <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-green-500 opacity-50" />
             <p>所有可公开验证的事实均已通过校验（或未发现公开事实）</p>
        </div>
    );

    return (
        <div className="space-y-6">
            <h3 className="text-lg font-bold flex items-center gap-2 text-slate-800">
                <Search className="text-blue-500" />
                联网溯源校验 ({verifications.length})
                <span className="text-xs font-normal text-slate-400 flex items-center gap-1">
                    <MousePointerClick className="w-3 h-3" />
                    点击左侧文档高亮可跳转
                </span>
            </h3>

            <div className="grid gap-4">
                {sortedVerifications.map((item, idx) => {
                    const isError = item.is_supported === false;
                    const isPass = item.is_supported === true;
                    const factId = item.original_fact?.fact_id;
                    
                    return (
                        <div 
                            key={factId || idx} 
                            ref={(el) => {
                                if (verificationRefs && factId) {
                                    verificationRefs.current[factId] = el;
                                }
                            }}
                            id={`verification-${factId}`}
                            className={`card transition-all duration-300 ${isError ? 'border-red-200 bg-red-50/50' : ''}`}
                        >
                            <div className="flex items-start gap-4">
                                <div className="mt-1 flex-shrink-0">
                                    {isError ? (
                                        <XCircle className="w-6 h-6 text-red-500" />
                                    ) : isPass ? (
                                        <CheckCircle2 className="w-6 h-6 text-green-500" />
                                    ) : (
                                        <HelpCircle className="w-6 h-6 text-slate-400" />
                                    )}
                                </div>
                                
                                <div className="flex-1 space-y-3">
                                    <div>
                                        <div className="flex items-center justify-between">
                                            <h4 className="font-semibold text-slate-900">
                                                {item.original_fact?.content}
                                            </h4>
                                            <span className={`text-xs px-2 py-1 rounded-full border ${
                                                item.confidence_level === 'High' ? 'bg-green-100 text-green-700 border-green-200' :
                                                item.confidence_level === 'Low' ? 'bg-red-100 text-red-700 border-red-200' :
                                                'bg-slate-100 text-slate-600 border-slate-200'
                                            }`}>
                                                {item.confidence_level} 置信度
                                            </span>
                                        </div>
                                        <div className="text-xs text-slate-500 mt-1">
                                            来源: {item.original_fact?.location?.section_title}
                                        </div>
                                    </div>

                                    {/* Reasoning Chain Display */}
                                    <div className="bg-white/80 p-3 rounded border border-slate-200 text-sm">
                                        <div className="font-medium text-slate-700 mb-1">AI 评估:</div>
                                        <p className="text-slate-600 leading-relaxed">{item.assessment}</p>
                                    </div>

                                    {/* Correction Proposal */}
                                    {isError && item.correction && (
                                        <div className="bg-green-50 p-3 rounded border border-green-200 text-sm">
                                            <span className="font-bold text-green-700">建议修正: </span>
                                            <span className="text-green-800">{item.correction}</span>
                                        </div>
                                    )}

                                    {/* Sources */}
                                    {item.search_snippets && item.search_snippets.length > 0 && (
                                        <div className="text-xs text-slate-400 mt-2">
                                            <div className="flex items-center gap-1 mb-1">
                                                <ExternalLink className="w-3 h-3" />
                                                <span>参考来源片段:</span>
                                            </div>
                                            <ul className="list-disc pl-4 space-y-1">
                                                {item.search_snippets.slice(0, 2).map((snip, i) => (
                                                    <li key={i} className="line-clamp-1" title={snip}>{snip}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
