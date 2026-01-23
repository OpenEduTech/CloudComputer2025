import { useState, useEffect } from "react";
import { learning } from "../../services/api";
import {
  Target,
  Book,
  Calendar,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Flag,
  Clock,
} from "lucide-react";

type DashboardProps = {
  token: string;
  user: any;
  onStartLearning: () => void;
  onLogout: () => void;
};

export default function Dashboard({
  token,
  user,
  onStartLearning,
  onLogout,
}: DashboardProps) {
  const [goals, setGoals] = useState<any>({});
  const [topic, setTopic] = useState("");
  const [plan, setPlan] = useState<any>(null);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [recsError, setRecsError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [planMessage, setPlanMessage] = useState("");

  useEffect(() => {
    loadGoals();
  }, []);

  const loadGoals = async () => {
    try {
      const data = await learning.getGoals(token);
      setGoals(data.goals || {});
      if (data.goals?.topic) setTopic(data.goals.topic);
      if (data.goals?.topic) {
        loadRecommendations(data.goals.topic);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveGoals = async () => {
    const trimmedTopic = topic.trim();
    if (!trimmedTopic) {
      setSaveMessage("请输入学习目标后再保存");
      setTimeout(() => setSaveMessage(""), 3000);
      return;
    }

    setSaving(true);
    setSaveMessage("");
    try {
      await learning.setGoals(token, { topic: trimmedTopic });
      setGoals({ ...goals, topic: trimmedTopic });
      setTopic(trimmedTopic);
      setSaveMessage("目标已保存！");
      await loadRecommendations(trimmedTopic);
      setTimeout(() => setSaveMessage(""), 3000);
    } catch (e) {
      console.error(e);
      setSaveMessage("保存失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  const handleGeneratePlan = async () => {
    if (!topic) return;
    setLoadingPlan(true);
    setPlanMessage("");
    try {
      const data = await learning.generatePlan(token, topic, 2, "beginner");
      try {
        let planData = data.plan;
        if (typeof planData === "string") {
          planData = planData
            .replace(/^```json\s*/, "")
            .replace(/^```\s*/, "")
            .replace(/\s*```$/, "");
          const planJson = JSON.parse(planData);
          setPlan(planJson);
        } else {
          setPlan(planData);
        }
        setPlanMessage("");
      } catch (e) {
        console.error("Plan parsing error:", e);
        setPlan({ raw: data.plan });
        setPlanMessage("计划格式非标准JSON，已显示原始内容");
      }
    } catch (e) {
      console.error(e);
      setPlanMessage("生成计划失败，请重试");
    } finally {
      setLoadingPlan(false);
    }
  };

  const loadRecommendations = async (query: string) => {
    const q = (query || "").trim();
    if (!q) return;
    setLoadingRecs(true);
    setRecsError("");
    try {
      const data = await learning.getRecommendations(token, q);
      const allRecs: any[] = [];
      if (data.results) {
        Object.keys(data.results).forEach((source) => {
          if (Array.isArray(data.results[source])) {
            allRecs.push(...data.results[source]);
          }
        });
      }
      setRecommendations(allRecs);
    } catch (e) {
      console.error(e);
      setRecommendations([]);
      setRecsError("获取推荐资源失败，请稍后重试");
    } finally {
      setLoadingRecs(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="flex items-center justify-between py-6">
          <div className="flex items-center gap-3">
            <Book className="w-10 h-10 text-primary-600" />
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
              学习仪表盘
            </h1>
          </div>
          <div className="flex items-center gap-8">
            <span className="text-gray-600 font-medium text-lg">
              欢迎回来, {user.username}
            </span>
            <button
              onClick={onLogout}
              className="text-base px-6 py-3 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-full transition-colors font-medium"
            >
              退出登录
            </button>
          </div>
        </div>
      </header>

      <main className="py-10 space-y-10">
        {/* Goals Section */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-10 transition-shadow hover:shadow-md">
          <div className="flex items-center gap-4 mb-8">
            <div className="p-3 bg-primary-50 rounded-xl">
              <Target className="w-8 h-8 text-primary-600" />
            </div>
            <h2 className="text-3xl font-bold text-gray-800">当前学习目标</h2>
          </div>
          <div className="flex gap-6 items-center">
            <div className="flex-1 relative">
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="您想学习什么？（例如：深度学习基础、微积分入门...）"
                className="w-full pl-6 pr-6 py-5 rounded-xl border-gray-200 bg-gray-50 focus:bg-white focus:border-primary-500 focus:ring-4 focus:ring-primary-100 transition-all border text-xl"
              />
            </div>
            <button
              onClick={handleSaveGoals}
              disabled={saving}
              className="px-8 py-5 bg-primary-600 text-white text-xl font-bold rounded-xl hover:bg-primary-700 disabled:opacity-70 shadow-sm hover:shadow transition-all min-w-[140px]"
            >
              {saving ? (
                <span className="flex items-center gap-3">
                  <Loader2 className="w-6 h-6 animate-spin" /> 保存中
                </span>
              ) : (
                "保存目标"
              )}
            </button>
          </div>
          {saveMessage && (
            <div
              className={`mt-4 text-lg font-medium ${
                saveMessage.includes("失败") ? "text-red-600" : "text-green-600"
              } flex items-center gap-3 animate-in fade-in slide-in-from-top-2`}
            >
              {saveMessage.includes("失败") ? (
                <div className="w-2 h-2 rounded-full bg-red-600" />
              ) : (
                <div className="w-2 h-2 rounded-full bg-green-600" />
              )}
              {saveMessage}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Plan Section - Takes up 7 columns on large screens */}
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-full">
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-100">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-indigo-50 rounded-lg">
                    <Calendar className="w-8 h-8 text-indigo-600" />
                  </div>
                  <h2 className="text-3xl font-bold text-gray-800">
                    个性化学习计划
                  </h2>
                </div>
                <div className="flex items-center gap-3">
                  {planMessage && (
                    <span className="text-base text-yellow-600 bg-yellow-50 px-4 py-2 rounded-full">
                      {planMessage}
                    </span>
                  )}
                  <button
                    onClick={handleGeneratePlan}
                    disabled={loadingPlan || !topic}
                    className="text-lg font-medium text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 px-6 py-3 rounded-lg transition-colors flex items-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loadingPlan ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Clock className="w-5 h-5" />
                    )}
                    {plan ? "重新生成" : "生成计划"}
                  </button>
                </div>
              </div>

              <div className="min-h-[400px]">
                {loadingPlan ? (
                  <div className="flex flex-col items-center justify-center h-[300px] text-gray-400 gap-4">
                    <Loader2 className="w-16 h-16 animate-spin text-indigo-200" />
                    <p className="animate-pulse text-xl">
                      正在为您规划最佳学习路径...
                    </p>
                  </div>
                ) : plan ? (
                  plan.weeks ? (
                    <div className="space-y-6">
                      {plan.weeks.map((week: any, i: number) => (
                        <div
                          key={i}
                          className="group border border-gray-200 rounded-xl overflow-hidden hover:border-indigo-200 transition-colors bg-white"
                        >
                          <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center justify-between group-hover:bg-indigo-50/50 transition-colors">
                            <h3 className="font-bold text-gray-800 flex items-center gap-3">
                              <span className="bg-indigo-600 text-white text-sm px-3 py-1 rounded-full">
                                WEEK {week.week}
                              </span>
                              <span className="text-lg text-gray-600">
                                阶段性规划
                              </span>
                            </h3>
                          </div>

                          <div className="p-6 space-y-8">
                            {/* Targets */}
                            <div>
                              <div className="flex items-center gap-2 mb-4 text-base font-semibold text-gray-500 uppercase tracking-wider">
                                <Flag className="w-5 h-5" /> 核心目标
                              </div>
                              <div className="flex flex-wrap gap-3">
                                {week.targets?.map((target: any, j: number) => (
                                  <span
                                    key={j}
                                    className="inline-flex items-center px-4 py-2 rounded-full text-base font-medium bg-blue-50 text-blue-700 border border-blue-100"
                                  >
                                    {typeof target === "object"
                                      ? target.target ||
                                        target.content ||
                                        JSON.stringify(target)
                                      : target}
                                  </span>
                                ))}
                              </div>
                            </div>

                            {/* Daily Tasks */}
                            <div>
                              <div className="flex items-center gap-2 mb-4 text-base font-semibold text-gray-500 uppercase tracking-wider">
                                <CheckCircle2 className="w-5 h-5" /> 每日任务
                              </div>
                              <div className="space-y-4">
                                {week.daily_tasks?.map(
                                  (task: any, j: number) => (
                                    <div
                                      key={j}
                                      className="flex items-start gap-4 p-4 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
                                    >
                                      <div className="mt-1 min-w-[1.5rem]">
                                        <div className="w-6 h-6 rounded-full border-2 border-gray-300 flex items-center justify-center text-xs text-gray-500 font-bold">
                                          {typeof task === "object" && task.day
                                            ? task.day
                                            : j + 1}
                                        </div>
                                      </div>
                                      <div className="text-base text-gray-700 leading-relaxed">
                                        {typeof task === "object"
                                          ? task.task ||
                                            task.content ||
                                            task.description ||
                                            task.activity ||
                                            JSON.stringify(task)
                                          : task}
                                      </div>
                                    </div>
                                  ),
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap bg-gray-50 p-8 rounded-xl text-base font-mono text-gray-700 border border-gray-200">
                      {typeof plan === "string"
                        ? plan
                        : plan.raw || JSON.stringify(plan, null, 2)}
                    </div>
                  )
                ) : (
                  <div className="text-center py-20 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
                    <Calendar className="w-16 h-16 text-gray-300 mx-auto mb-6" />
                    <p className="text-gray-500 font-medium text-lg">
                      设定学习目标后，点击“生成计划”开始您的学习之旅
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Recommendations Section - Takes up 5 columns */}
          <div className="lg:col-span-5">
            <div className="bg-white rounded-lg shadow p-8 h-full sticky top-24">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <Book className="w-8 h-8 text-primary-600" />
                  <h2 className="text-3xl font-bold text-gray-800">
                    推荐学习资源
                  </h2>
                </div>
                {loadingRecs && (
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                )}
              </div>

              <div className="space-y-6 max-h-[600px] overflow-y-auto pr-2">
                {recsError ? (
                  <p className="text-red-600 text-lg">{recsError}</p>
                ) : recommendations.length > 0 ? (
                  recommendations.map((rec, idx) => (
                    <div
                      key={idx}
                      className="border-b pb-6 last:border-0 hover:bg-gray-50 p-4 rounded-xl transition-colors"
                    >
                      {rec.url ? (
                        <a
                          href={rec.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-bold text-xl text-primary-600 hover:underline block mb-2"
                        >
                          {rec.title}
                        </a>
                      ) : (
                        <div className="font-bold text-xl text-gray-900 block mb-2">
                          {rec.title}
                        </div>
                      )}
                      {rec.authors && rec.authors.length > 0 && (
                        <p className="text-base text-gray-500 mt-2">
                          作者: {rec.authors.join(", ")}
                        </p>
                      )}
                      <p className="text-lg text-gray-600 mt-3 line-clamp-3 leading-relaxed">
                        {rec.summary || rec.abstract || "（暂无摘要）"}
                      </p>
                      <div className="flex gap-3 mt-4">
                        {rec.published && (
                          <span className="text-sm bg-gray-100 px-3 py-1 rounded-lg text-gray-500">
                            {rec.published}
                          </span>
                        )}
                        {rec.source && (
                          <span className="text-sm bg-blue-50 px-3 py-1 rounded-lg text-blue-500 uppercase font-medium">
                            {rec.source}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500 text-lg">
                    {loadingRecs
                      ? "正在搜索相关资源..."
                      : "保存目标后查看推荐资源。"}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-center pt-12 pb-8">
          <button
            onClick={onStartLearning}
            className="group flex items-center gap-3 px-10 py-5 bg-gradient-to-r from-green-600 to-emerald-600 text-white text-xl font-bold rounded-2xl hover:shadow-xl hover:scale-105 transition-all duration-300 ring-4 ring-green-50"
          >
            开始 PPT 沉浸式学习
            <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </main>
    </div>
  );
}
