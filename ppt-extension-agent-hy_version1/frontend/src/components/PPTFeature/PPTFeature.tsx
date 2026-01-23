import { useState } from "react";
import UploadArea from "../UploadArea/UploadArea";
import PPTViewer from "../PPTViewer/PPTViewer";
import ExpansionPanel from "../ExpansionPanel/ExpansionPanel";
import ProgressBar from "../ProgressBar/ProgressBar";
import { Upload, FileText, Sparkles, ArrowLeft } from "lucide-react";

type Slide = {
  page_number: number;
  title: string;
  text_boxes: Array<{
    id: number;
    text: string;
    position: { left: number; top: number; width: number; height: number };
    is_title: boolean;
  }>;
};

type PPTData = {
  metadata: {
    file_name: string;
    slide_count: number;
  };
  slides: Slide[];
};

type ExpandedContent = {
  background: string;
  principles: string;
  formulas: string;
  examples: string;
  summary: string;
  references: Array<{ title: string; url: string }>;
};

type PPTFeatureProps = {
  onBack: () => void;
};

function PPTFeature({ onBack }: PPTFeatureProps) {
  const [pptData, setPPTData] = useState<PPTData | null>(null);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [selectedTextBoxes, setSelectedTextBoxes] = useState<number[]>([]);
  const [expandedContent, setExpandedContent] =
    useState<ExpandedContent | null>(null);
  const [isExpanding, setIsExpanding] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleUpload = (data: PPTData) => {
    setPPTData(data);
    setCurrentSlide(0);
    setSelectedTextBoxes([]);
    setExpandedContent(null);
  };

  const handleTextBoxSelect = (textBoxId: number) => {
    setSelectedTextBoxes((prev) => {
      if (prev.includes(textBoxId)) {
        return prev.filter((id) => id !== textBoxId);
      } else {
        return [...prev, textBoxId];
      }
    });
  };

  const handleExpand = async () => {
    if (!pptData || selectedTextBoxes.length === 0) return;

    setIsExpanding(true);
    setProgress(0);

    const slide = pptData.slides[currentSlide];
    const selectedTexts = slide.text_boxes
      .filter((tb) => selectedTextBoxes.includes(tb.id))
      .map((tb) => tb.text)
      .join("\n");

    try {
      const response = await fetch("/api/v1/expand", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: slide.title,
          content: selectedTexts,
          context: { page_number: currentSlide + 1 },
        }),
      });

      const data = await response.json();
      setExpandedContent(data.expanded_content);
      setProgress(100);
    } catch (error) {
      console.error("Expansion failed:", error);
    } finally {
      setIsExpanding(false);
    }
  };

  const handleExpandAll = async () => {
    if (!pptData) return;

    setIsExpanding(true);
    setProgress(0);

    const slide = pptData.slides[currentSlide];
    const allTexts = slide.text_boxes.map((tb) => tb.text).join("\n");

    try {
      const response = await fetch("/api/v1/expand", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: slide.title,
          content: allTexts,
          context: { page_number: currentSlide + 1 },
        }),
      });

      const data = await response.json();
      setExpandedContent(data.expanded_content);
      setProgress(100);
    } catch (error) {
      console.error("Expansion failed:", error);
    } finally {
      setIsExpanding(false);
    }
  };

  const handleExport = async (format: "markdown" | "pdf") => {
    if (!pptData || !expandedContent) return;

    try {
      const response = await fetch("/api/v1/export", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ppt_data: pptData,
          expanded_data: {
            [`slide_${currentSlide + 1}_box_${selectedTextBoxes.length > 0 ? selectedTextBoxes[0] : ""}`]:
              expandedContent,
          },
          format,
          page_number: currentSlide + 1,
        }),
      });

      const data = await response.json();

      if (format === "markdown") {
        const blob = new Blob([data.content], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename;
        a.click();
        URL.revokeObjectURL(url);
      } else if (data.download_url) {
        window.open(`http://localhost:8000${data.download_url}`, "_blank");
      }
    } catch (error) {
      console.error("Export failed:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <header className="bg-white/80 backdrop-blur-sm sticky top-0 z-50 border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500 hover:text-gray-900"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-primary-500 to-indigo-600 rounded-lg shadow-sm">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">
                PPT 智能扩展
              </h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {!pptData ? (
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                上传 PPT 文件
              </h2>
              <p className="text-gray-500 text-lg">
                AI 智能分析，一键生成扩展内容与学习资料
              </p>
            </div>
            <UploadArea onUpload={handleUpload} />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Panel - PPT Viewer & Controls */}
            <div className="lg:col-span-7 space-y-6 lg:sticky lg:top-24">
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="p-4 border-b border-gray-50 flex items-center justify-between bg-gray-50/50">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-blue-50 rounded text-blue-600">
                      <FileText className="w-4 h-4" />
                    </div>
                    <span
                      className="font-semibold text-gray-700 truncate max-w-[200px]"
                      title={pptData.metadata.file_name}
                    >
                      {pptData.metadata.file_name}
                    </span>
                  </div>
                  <button
                    onClick={() => setPPTData(null)}
                    className="text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-md transition-all"
                  >
                    重新上传
                  </button>
                </div>

                <div className="p-6">
                  <PPTViewer
                    slides={pptData.slides}
                    currentSlide={currentSlide}
                    onSlideChange={setCurrentSlide}
                    selectedTextBoxes={selectedTextBoxes}
                    onTextBoxSelect={handleTextBoxSelect}
                  />
                </div>

                <div className="p-4 bg-gray-50/50 border-t border-gray-100 flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setSelectedTextBoxes([])}
                      className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 rounded-lg transition-all shadow-sm"
                    >
                      清除选择
                    </button>
                    <button
                      onClick={() =>
                        setSelectedTextBoxes(
                          pptData.slides[currentSlide].text_boxes.map(
                            (tb) => tb.id,
                          ),
                        )
                      }
                      className="px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 rounded-lg transition-all shadow-sm"
                    >
                      全选本页
                    </button>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleExpand}
                      disabled={selectedTextBoxes.length === 0 || isExpanding}
                      className="px-4 py-2 text-sm font-medium bg-white text-primary-600 border border-primary-200 hover:bg-primary-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center gap-2"
                    >
                      <Upload className="w-4 h-4" />
                      扩展选中
                    </button>
                    <button
                      onClick={handleExpandAll}
                      disabled={isExpanding}
                      className="px-4 py-2 text-sm font-bold bg-gradient-to-r from-primary-600 to-indigo-600 text-white rounded-lg hover:shadow-lg hover:scale-[1.02] disabled:opacity-70 disabled:cursor-not-allowed transition-all shadow-md flex items-center gap-2"
                    >
                      <Sparkles className="w-4 h-4" />
                      扩展整页
                    </button>
                  </div>
                </div>
              </div>

              {isExpanding && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-primary-700">
                      正在生成智能扩展...
                    </span>
                    <span className="text-xs font-bold text-primary-600">
                      {progress}%
                    </span>
                  </div>
                  <ProgressBar progress={progress} />
                </div>
              )}
            </div>

            {/* Right Panel - Expansion Content */}
            <div className="lg:col-span-5">
              <ExpansionPanel
                content={expandedContent}
                onExport={handleExport}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default PPTFeature;
