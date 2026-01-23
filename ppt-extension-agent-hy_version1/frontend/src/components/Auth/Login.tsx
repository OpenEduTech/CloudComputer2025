import { useState } from "react";
import { auth } from "../../services/api";
import { User, Lock, Sparkles, ArrowRight, Loader2 } from "lucide-react";

type LoginProps = {
  onLoginSuccess: (token: string, user: any) => void;
  onSwitchToRegister: () => void;
};

export default function Login({
  onLoginSuccess,
  onSwitchToRegister,
}: LoginProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const data = await auth.login(username, password);
      // Fetch user details after login
      const user = await auth.me(data.access_token);
      onLoginSuccess(data.access_token, user);
    } catch (err) {
      setError("登录失败，请检查用户名和密码。");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center bg-[#f8fafc] p-4 sm:p-6 lg:p-8 relative overflow-hidden">
      {/* Background Blobs */}
      <div className="absolute inset-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-5%] w-[40%] h-[40%] bg-purple-200/40 rounded-full blur-[100px] animate-blob"></div>
        <div className="absolute bottom-[-10%] right-[-5%] w-[40%] h-[40%] bg-blue-200/40 rounded-full blur-[100px] animate-blob animation-delay-2000"></div>
      </div>

      {/* Main Content */}
      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-6">
          <div className="mx-auto mb-4 w-12 h-12 bg-indigo-600 rounded-2xl shadow-lg shadow-indigo-500/25 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            PPT内容扩展智能体
          </h1>
          <p className="text-slate-500 text-sm sm:text-base mt-1">
            登录您的账户
          </p>
        </div>

        <div className="bg-white/80 backdrop-blur-sm border border-slate-200 rounded-2xl shadow-xl shadow-slate-900/5 p-6 sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-4">
              <div className="group">
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  用户名
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="h-5 w-5 text-slate-400 group-focus-within:text-indigo-600 transition-colors" />
                  </div>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    required
                    className="block w-full pl-10 pr-3 py-3 bg-white border border-slate-200 rounded-xl text-base text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all"
                    placeholder="请输入用户名"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
              </div>

              <div className="group">
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-semibold text-slate-700">
                    密码
                  </label>
                  <a
                    href="#"
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
                  >
                    忘记密码？
                  </a>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-slate-400 group-focus-within:text-indigo-600 transition-colors" />
                  </div>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    required
                    className="block w-full pl-10 pr-3 py-3 bg-white border border-slate-200 rounded-xl text-base text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all"
                    placeholder="请输入密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="rounded-xl bg-red-50 p-3 border border-red-100 flex items-start gap-3 animate-in fade-in slide-in-from-top-2">
                <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-red-600 text-xs font-bold">!</span>
                </div>
                <p className="text-sm text-red-600 font-semibold">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white text-base font-semibold rounded-xl shadow-lg shadow-indigo-600/20 hover:shadow-indigo-600/30 focus:outline-none focus:ring-4 focus:ring-indigo-600/20 transition-all duration-200 disabled:opacity-70 disabled:cursor-not-allowed transform active:scale-[0.99] flex items-center justify-center gap-2 group"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <span>登录</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          <div className="mt-5 text-center">
            <p className="text-slate-500 text-sm">
              还没有账号？{" "}
              <button
                onClick={onSwitchToRegister}
                className="text-indigo-600 font-semibold hover:text-indigo-700 transition-colors"
              >
                立即注册
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
