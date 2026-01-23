import React, { useMemo, useCallback } from 'react';
import { FileText, ExternalLink } from 'lucide-react';

export default function DocumentViewer({ sections, conflicts, repetitions, verifications, onHighlightClick }) {
    if (!sections || sections.length === 0) return (
        <div className="card h-full flex items-center justify-center text-slate-400">
            <div className="text-center">
                <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>暂无文档内容</p>
            </div>
        </div>
    );

    // 预处理高亮区域，同时记录关联的 conflict_id 或 fact_id
    const highlightMap = useMemo(() => {
        const map = new Map(); // Key: Original Text Snippet -> { type, id }

        // 1. 冲突检测高亮 (Amber)
        conflicts?.forEach(c => {
            if (c.fact_a?.original_text) {
                map.set(c.fact_a.original_text.trim(), { 
                    type: 'conflict', 
                    id: c.conflict_id,
                    factId: c.fact_a.fact_id
                });
            }
            if (c.fact_b?.original_text) {
                map.set(c.fact_b.original_text.trim(), { 
                    type: 'conflict', 
                    id: c.conflict_id,
                    factId: c.fact_b.fact_id
                });
            }
        });

        // 2. 重复段落高亮 (Purple)
        repetitions?.forEach((r, idx) => {
             // 使用后端返回的 conflict_id 确保与 RepetitionList 的 ref 匹配
             if (r.fact_a?.original_text) {
                 map.set(r.fact_a.original_text.trim(), {
                     type: 'repetition',
                     id: r.conflict_id || `rep-${idx}`, // 优先使用 conflict_id
                     info: r
                 });
             }
             if (r.fact_b?.original_text) {
                 map.set(r.fact_b.original_text.trim(), {
                     type: 'repetition',
                     id: r.conflict_id || `rep-${idx}`,
                     info: r
                 });
             }
        });

        // 3. 事实校验错误高亮 (Red) - 覆盖冲突高亮如果重叠（通常校验错误更严重）
        verifications?.forEach(v => {
            if (v.is_supported === false && v.original_fact?.original_text) {
                map.set(v.original_fact.original_text.trim(), { 
                    type: 'error', 
                    id: v.original_fact.fact_id,
                    factId: v.original_fact.fact_id
                });
            }
        });

        return map;
    }, [conflicts, repetitions, verifications]);

    // 处理高亮点击
    const handleClick = useCallback((highlightInfo) => {
        if (onHighlightClick && highlightInfo) {
            onHighlightClick(highlightInfo.type, highlightInfo.id);
        }
    }, [onHighlightClick]);

    // 简单的高亮渲染函数
    // 注意：这种基于字符串替换的方法在复杂文档中可能不完美（如重复句子），但在 Demo 场景下足够有效
    const renderHighlightedText = (text) => {
        if (!text) return null;
        
        let parts = [{ text, type: 'normal', info: null }];

        highlightMap.forEach((info, searchStr) => {
            if (!searchStr || searchStr.length < 5) return; // 忽略太短的匹配防止误伤

            const newParts = [];
            parts.forEach(part => {
                if (part.type !== 'normal') {
                    newParts.push(part);
                    return;
                }

                const fragments = part.text.split(searchStr);
                fragments.forEach((fragment, i) => {
                    if (fragment) newParts.push({ text: fragment, type: 'normal', info: null });
                    if (i < fragments.length - 1) {
                        newParts.push({ text: searchStr, type: info.type, info: info });
                    }
                });
            });
            parts = newParts;
        });

        return parts.map((part, i) => {
            if (part.type === 'conflict') {
                return (
                    <mark 
                        key={i} 
                        className="bg-amber-200 text-amber-900 rounded px-1 cursor-pointer hover:bg-amber-300 transition-colors group relative"
                        title="点击查看冲突详情"
                        onClick={() => handleClick(part.info)}
                    >
                        {part.text}
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-amber-700 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                            <ExternalLink className="inline w-3 h-3 mr-1" />
                            点击跳转到冲突
                        </span>
                    </mark>
                );
            }
            if (part.type === 'repetition') {
                return (
                    <mark 
                        key={i} 
                        className="bg-purple-200 text-purple-900 rounded px-1 cursor-pointer hover:bg-purple-300 transition-colors group relative"
                        title="点击查看重复详情"
                        onClick={() => handleClick(part.info)}
                    >
                        {part.text}
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-purple-700 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                            <ExternalLink className="inline w-3 h-3 mr-1" />
                            重复段落
                        </span>
                    </mark>
                );
            }
            if (part.type === 'error') {
                return (
                    <mark 
                        key={i} 
                        className="bg-red-200 text-red-900 rounded px-1 cursor-pointer hover:bg-red-300 transition-colors border-b-2 border-red-400 group relative"
                        title="点击查看验证详情"
                        onClick={() => handleClick(part.info)}
                    >
                        {part.text}
                        <span className="absolute -top-6 left-1/2 -translate-x-1/2 bg-red-700 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                            <ExternalLink className="inline w-3 h-3 mr-1" />
                            点击跳转到验证
                        </span>
                    </mark>
                );
            }
            return <span key={i}>{part.text}</span>;
        });
    };

    return (
        <div className="card h-[calc(100vh-140px)] flex flex-col">
            <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-100">
                <h3 className="text-lg font-bold flex items-center gap-2 text-slate-800">
                    <FileText className="text-brand-600" />
                    文档原文
                </h3>
                <div className="flex gap-4 text-xs">
                    <div className="flex items-center gap-1">
                        <span className="w-3 h-3 bg-amber-200 rounded cursor-pointer"></span>
                        <span className="text-slate-600">前后矛盾 (可点击)</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="w-3 h-3 bg-purple-200 rounded cursor-pointer"></span>
                        <span className="text-slate-600">高频重复 (可点击)</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="w-3 h-3 bg-red-200 border-b-2 border-red-400 rounded cursor-pointer"></span>
                        <span className="text-slate-600">事实谬误 (可点击)</span>
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 space-y-6 scrollbar-thin">
                {sections.map((section, idx) => (
                    <div key={idx} className="pb-4 border-b border-slate-50 last:border-0">
                        {section.title && (
                            <h4 className="font-bold text-slate-800 mb-3 text-lg sticky top-0 bg-white/95 py-2 backdrop-blur-sm">
                                {section.title}
                            </h4>
                        )}
                        <p className="text-slate-600 leading-7 text-justify whitespace-pre-wrap font-serif">
                            {renderHighlightedText(section.content)}
                        </p>
                    </div>
                ))}
            </div>
        </div>
    );
}
