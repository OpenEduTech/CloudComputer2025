
import React, { useState } from 'react';

interface SearchScreenProps {
  onSearch: (keyword: string) => void;
  isLoading: boolean;
  error: string | null;
}

const SearchScreen: React.FC<SearchScreenProps> = ({ onSearch, isLoading, error }) => {
  const [inputValue, setInputValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(inputValue);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 bg-[#e5e2df]">
      <div className="mb-16 text-center animate-fade-in">
        <h1 className="text-6xl md:text-8xl font-bold text-stone-800 tracking-tighter mb-6 opacity-95 font-serif">
          知识的脉络
        </h1>
        <div className="flex items-center justify-center gap-4">
            <div className="h-px w-8 bg-stone-400"></div>
            <p className="text-stone-500 text-xs md:text-sm font-light tracking-[0.5em] uppercase">
                跨学科词汇释义图谱
            </p>
            <div className="h-px w-8 bg-stone-400"></div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="w-full max-w-3xl relative">
        <input 
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="探索一个概念，如：拓扑、张力、镜像..."
          className="w-full bg-white/80 backdrop-blur border border-stone-300 rounded-2xl py-6 px-10 text-xl focus:outline-none focus:ring-4 focus:ring-stone-400/20 transition-all shadow-xl shadow-stone-400/10 text-stone-700 placeholder-stone-400 font-serif"
          autoFocus
        />
        <button 
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          className="absolute right-4 top-1/2 -translate-y-1/2 bg-stone-800 text-white rounded-xl px-10 py-3.5 hover:bg-black transition-all disabled:bg-stone-400 disabled:cursor-not-allowed font-bold text-xs tracking-widest uppercase shadow-lg active:scale-95"
        >
          {isLoading ? '解析中' : '探索'}
        </button>
      </form>

      {error && (
        <p className="mt-6 text-red-500 font-medium animate-pulse text-sm tracking-wide">{error}</p>
      )}

      <div className="mt-20 flex gap-6 flex-wrap justify-center opacity-60">
        {["熵", "混沌", "赋能", "赛博朋克"].map(tag => (
          <button 
            key={tag}
            onClick={() => { setInputValue(tag); onSearch(tag); }}
            className="px-5 py-2 border border-stone-300 rounded-full text-[10px] font-bold tracking-widest text-stone-600 hover:bg-stone-800 hover:text-white hover:border-stone-800 transition-all uppercase"
          >
            {tag}
          </button>
        ))}
      </div>

      <style>{`
        .animate-fade-in { animation: fadeIn 1s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  );
};

export default SearchScreen;
