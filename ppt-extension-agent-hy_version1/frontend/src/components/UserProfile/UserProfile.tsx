import { useState, useEffect } from "react";
import { learning } from "../../services/api";
import {
  User,
  Calendar,
  Clock,
  ArrowLeft,
  BookOpen,
  Target,
  Loader2,
} from "lucide-react";

type UserProfileProps = {
  token: string;
  user: any;
  onBack: () => void;
};

export default function UserProfile({ token, user, onBack }: UserProfileProps) {
  const [plans, setPlans] = useState<any[]>([]);
  const [goals, setGoals] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState<any | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [plansData, goalsData] = await Promise.all([
        learning.getPlans(token),
        learning.getGoals(token),
      ]);
      setPlans(plansData.plans || []);
      setGoals(goalsData.goals || {});
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-[95%] mx-auto flex items-center justify-between py-6 px-6">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
              title="返回仪表盘"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
            <h1 className="text-2xl font-bold text-gray-900">用户个人中心</h1>
          </div>
        </div>
      </header>

      <main className="max-w-[95%] mx-auto px-6 py-10 space-y-8">
        {/* User Info Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 flex items-center gap-8">
          <div className="w-24 h-24 bg-primary-100 rounded-full flex items-center justify-center text-primary-600 text-4xl font-bold">
            {user.username[0].toUpperCase()}
          </div>
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-2">
              {user.username}
            </h2>
            <div className="flex items-center gap-6 text-gray-500 text-lg">
              <span className="flex items-center gap-2">
                <User className="w-5 h-5" />
                普通用户
              </span>
              <span className="flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                已生成 {plans.length} 个学习计划
              </span>
            </div>
          </div>
        </div>

        {/* Current Goal Section */}
        {goals?.topic && (
          <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-2xl shadow-md p-8 text-white flex items-center justify-between animate-in fade-in slide-in-from-bottom-4">
            <div>
              <h3 className="text-primary-100 text-lg font-medium mb-2 flex items-center gap-2">
                <Target className="w-5 h-5" />
                当前专注目标
              </h3>
              <p className="text-3xl font-bold">{goals.topic}</p>
            </div>
            <button
              onClick={onBack}
              className="px-6 py-3 bg-white/20 hover:bg-white/30 rounded-xl transition-colors font-medium backdrop-blur-sm border border-white/30"
            >
              继续学习
            </button>
          </div>
        )}

        {/* Plans History */}
        <div>
          <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-3">
            <Clock className="w-7 h-7 text-primary-600" />
            历史学习计划
          </h3>

          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-10 h-10 animate-spin text-primary-600" />
            </div>
          ) : plans.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-2xl border border-gray-200">
              <BookOpen className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-xl text-gray-500">暂无历史计划</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {plans.map((plan, index) => (
                <div
                  key={index}
                  onClick={() => setSelectedPlan(plan)}
                  className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md hover:border-primary-300 transition-all cursor-pointer group"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className="p-3 bg-primary-50 rounded-lg group-hover:bg-primary-100 transition-colors">
                      <Target className="w-6 h-6 text-primary-600" />
                    </div>
                    <span className="text-sm text-gray-500">
                      {formatDate(plan.created_at)}
                    </span>
                  </div>
                  <h4 className="text-xl font-bold text-gray-900 mb-3 line-clamp-2 h-14">
                    {plan.topic}
                  </h4>
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded">
                      <Calendar className="w-4 h-4" />
                      {plan.content.weeks.length} 周计划
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Plan Detail Modal */}
      {selectedPlan && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6 backdrop-blur-sm">
          <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6 border-b flex items-center justify-between bg-gray-50">
              <div>
                <h3 className="text-2xl font-bold text-gray-900">
                  {selectedPlan.topic}
                </h3>
                <p className="text-gray-500 mt-1">
                  创建于 {formatDate(selectedPlan.created_at)}
                </p>
              </div>
              <button
                onClick={() => setSelectedPlan(null)}
                className="p-2 hover:bg-gray-200 rounded-full transition-colors text-gray-500 hover:text-gray-700"
              >
                <span className="text-2xl">&times;</span>
              </button>
            </div>

            <div className="p-8 overflow-y-auto">
              <div className="space-y-8">
                {selectedPlan.content.weeks.map((week: any, i: number) => (
                  <div
                    key={i}
                    className="border border-gray-200 rounded-xl overflow-hidden"
                  >
                    <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
                      <h4 className="font-bold text-lg text-gray-800">
                        第 {week.week} 周
                      </h4>
                    </div>
                    <div className="p-6 space-y-6">
                      <div>
                        <h5 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                          核心目标
                        </h5>
                        <div className="flex flex-wrap gap-2">
                          {week.targets?.map((target: any, j: number) => (
                            <span
                              key={j}
                              className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-50 text-blue-700 border border-blue-100"
                            >
                              {typeof target === "object"
                                ? target.target || target.content
                                : target}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <h5 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                          每日任务
                        </h5>
                        <div className="space-y-3">
                          {week.daily_tasks?.map((task: any, j: number) => (
                            <div
                              key={j}
                              className="flex items-start gap-3 p-3 rounded-lg bg-gray-50"
                            >
                              <span className="w-6 h-6 rounded-full bg-white border border-gray-200 flex items-center justify-center text-xs font-bold text-gray-500 flex-shrink-0">
                                {task.day || j + 1}
                              </span>
                              <span className="text-gray-700">
                                {typeof task === "object"
                                  ? task.task || task.content
                                  : task}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-6 border-t bg-gray-50 flex justify-end">
              <button
                onClick={() => setSelectedPlan(null)}
                className="px-6 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 font-medium text-gray-700 transition-colors"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
