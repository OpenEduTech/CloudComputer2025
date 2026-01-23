import React from 'react';
import { Upload, FileText, Loader2, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function UploadSection({ onUpload, isUploading }) {
    const fileInputRef = React.useRef(null);

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) onUpload(file);
    };

    return (
        <div className="card max-w-2xl mx-auto mt-10 text-center py-16">
            <div className="mb-6 flex justify-center">
                <div className="bg-brand-50 p-4 rounded-full">
                    <Upload className="w-12 h-12 text-brand-600" />
                </div>
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">上传文档进行智能核查</h2>
            <p className="text-slate-500 mb-8 max-w-md mx-auto">
                支持 .txt, .docx, .pdf 格式。系统将自动提取事实、检测前后矛盾，并进行联网溯源校验。
            </p>

            <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".txt,.md,.docx,.pdf"
                onChange={handleFileChange}
            />

            <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="btn-primary flex items-center gap-2 mx-auto text-lg px-8 py-3"
            >
                {isUploading ? <Loader2 className="animate-spin" /> : <FileText />}
                {isUploading ? '正在分析文档...' : '选择文件'}
            </button>
            
            <div className="mt-8 flex justify-center gap-8 text-sm text-slate-400">
                <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4" /> <span>联网溯源</span>
                </div>
                <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" /> <span>矛盾检测</span>
                </div>
            </div>
        </div>
    );
}
