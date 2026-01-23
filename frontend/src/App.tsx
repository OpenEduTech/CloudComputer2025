import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import * as echarts from "echarts";

const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

type Material = {
  id: string;
  title: string;
  source_type: string;
  material_type: string;
  is_primary: boolean;
  status: string;
  text_chunk_count: number;
  summary_chunk_count: number;
  error_message?: string;
};

type Quiz = {
  id: string;
  status: string;
  error_message?: string;
};

type Question = {
  id: string;
  type: "mcq" | "blank" | "short";
  stem: string;
  options?: string[];
};

type Attempt = {
  id: string;
  status: string;
  score?: number;
  grading?: Array<{
    question_id: string;
    result?: {
      score?: number;
      is_correct?: boolean;
      verdict?: string;
      criteria_scores?: Record<string, number>;
      student_answer?: string;
      correct_answer?: string;
      analysis?: string;
      missing_points?: string[];
      error_tags?: string[];
      error_analysis?: string;
      feedback?: string;
    };
    score?: number;
    is_correct?: boolean;
    mistake_added?: boolean;
    analysis?: string;
    knowledge_points?: string[];
  }>;
};

type Mistake = {
  id: string;
  question_id: string;
  error_tags: string[];
  knowledge_points: string[];
  last_error_analysis?: string;
  last_question?: string;
  last_question_type?: string;
  last_options?: string[];
  last_student_answer?: string;
  last_correct_answer?: string;
  last_explanation?: string;
  wrong_count: number;
};

// ---------------- M3: Coach ----------------
type CoachPlanDoc = {
  id: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  plan?: {
    diagnosis?: {
      summary?: string;
      key_weak_node_ids?: string[];
      top_error_tags?: string[];
      top_missing_points?: string[];
    };
    corrective_actions?: Array<{
      issue?: string;
      how_to_fix?: string;
      evidence?: {
        missing_points?: string[];
        error_tags?: string[];
        weak_node_ids?: string[];
      };
    }>;
    practice_plan?: Array<{
      level?: "L1" | "L2";
      focus_node_ids?: string[];
      num_questions?: number;
      notes?: string;
    }>;
    one_click_practice?: {
      node_id?: string | null;
      num_questions?: number;
      difficulty_mix?: Record<string, number>;
      type_mix?: Record<string, number>;
      material_ids?: string[];
    };
  };
};

// ---------------- M3: Tutor ----------------
type TutorMessage = {
  role: "user" | "assistant";
  content: string;
};

// ---------------- M2: Knowledge tree ----------------
type KnowledgeNode = {
  id: string;
  title: string;
  level: number;
  order: number;
  parent_id?: string | null;
  mastery_score?: number;
  // backend variants (some implementations use different field names)
  mastery?: number;
  mastery_percent?: number;
  seen?: number;
  self_seen?: number;
  wrong?: number;
  self_wrong?: number;
  children?: KnowledgeNode[];
};

type KnowledgeTreeResponse = {
  material_id: string;
  tree: KnowledgeNode[];
};

const MATH_REGEX = /\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g;

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br/>");

const renderMathToHtml = (text: string) => {
  const katex = window.katex;
  if (!katex) {
    return escapeHtml(text);
  }
  let result = "";
  let lastIndex = 0;
  MATH_REGEX.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = MATH_REGEX.exec(text)) !== null) {
    result += escapeHtml(text.slice(lastIndex, match.index));
    const math = (match[1] ?? match[2] ?? "").trim();
    const displayMode = Boolean(match[1]);
    try {
      result += katex.renderToString(math, { displayMode, throwOnError: false });
    } catch {
      result += escapeHtml(match[0]);
    }
    lastIndex = match.index + match[0].length;
  }
  result += escapeHtml(text.slice(lastIndex));
  return result;
};

type MathTextProps = {
  text?: string | null;
  as?: "span" | "p" | "div";
  className?: string;
};

function MathText({ text, as = "span", className }: MathTextProps) {
  if (!text) {
    return null;
  }
  const Tag = as;
  return <Tag className={className} dangerouslySetInnerHTML={{ __html: renderMathToHtml(String(text)) }} />;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const cardStyle = (index: number) =>
  ({ "--delay": `${index * 0.08}s` } as CSSProperties);

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export default function App() {
  const [apiBase] = useState(DEFAULT_API_BASE);
  const [notebookId, setNotebookId] = useState("demo-notebook");
  const [studentId, setStudentId] = useState("demo_user");

  const [materials, setMaterials] = useState<Material[]>([]);
  const [selectedMaterials, setSelectedMaterials] = useState<Record<string, boolean>>({});

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadSourceType, setUploadSourceType] = useState("auto");
  const [materialType, setMaterialType] = useState("textbook");
  const [isPrimary, setIsPrimary] = useState(true);
  const [uploadStatus, setUploadStatus] = useState("");

  const [numQuestions, setNumQuestions] = useState(3);
  const [difficulty, setDifficulty] = useState("正常");
  const [questionTypes, setQuestionTypes] = useState<string[]>(["选择", "填空", "问答"]);
  const [quizId, setQuizId] = useState("");
  const [quizStatus, setQuizStatus] = useState("");
  const [questions, setQuestions] = useState<Question[]>([]);

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attemptId, setAttemptId] = useState("");
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [mistakes, setMistakes] = useState<Mistake[]>([]);

  // ---- M3: Coach state ----
  const [coachStatus, setCoachStatus] = useState("");
  const [coachPlanDoc, setCoachPlanDoc] = useState<CoachPlanDoc | null>(null);

  // ---- M3: Tutor state ----
  const [tutorOpen, setTutorOpen] = useState(false);
  const [tutorQuestionId, setTutorQuestionId] = useState<string>("");
  const [tutorSessionId, setTutorSessionId] = useState<string>("");
  const [tutorLevel, setTutorLevel] = useState<string>("L0");
  const [tutorTurn, setTutorTurn] = useState<number>(0);
  const [tutorMessages, setTutorMessages] = useState<TutorMessage[]>([]);
  const [tutorInput, setTutorInput] = useState<string>("");
  const [tutorGiveUp, setTutorGiveUp] = useState<boolean>(false);

  // ---- M2 state ----
  const [knowledgeTree, setKnowledgeTree] = useState<KnowledgeNode[]>([]);
  const [treeMaterialId, setTreeMaterialId] = useState<string>("");
  const [selectedNodeId, setSelectedNodeId] = useState<string>("");
  const [selectedNodeTitle, setSelectedNodeTitle] = useState<string>("");
  const [treeExpandAll, setTreeExpandAll] = useState(false);
  const [treeHeight, setTreeHeight] = useState(560);
  const treeChartRef = useRef<HTMLDivElement | null>(null);
  const treeChartInstanceRef = useRef<echarts.EChartsType | null>(null);

  const [message, setMessage] = useState("");
  const [activeView, setActiveView] = useState("overview");

  const selectedMaterialIds = useMemo(
    () => Object.keys(selectedMaterials).filter((id) => selectedMaterials[id]),
    [selectedMaterials],
  );

  const primaryMaterial = useMemo(
    () => materials.find((m) => m.is_primary) || null,
    [materials],
  );
  const contextReady = Boolean(notebookId.trim() && studentId.trim());

  const navItems = [
    { id: "overview", label: "总览", desc: "流程与状态" },
    { id: "materials", label: "资料库", desc: "上传与管理" },
    { id: "knowledge", label: "知识树", desc: "章节与掌握度" },
    { id: "quiz", label: "测验", desc: "出题与判卷" },
    { id: "review", label: "复盘", desc: "错题与小灶" },
  ];

  const activeNav = navItems.find((item) => item.id === activeView) ?? navItems[0];

  const gradingMap = useMemo(() => {
    if (!attempt?.grading) {
      return new Map<string, NonNullable<Attempt["grading"]>[number]>();
    }
    return new Map(attempt.grading.map((item) => [item.question_id, item]));
  }, [attempt]);

  const loadMaterials = async () => {
    if (!notebookId.trim()) {
      setMessage("请先填写 notebook_id");
      return;
    }
    if (!studentId.trim()) {
      setMessage("请先填写 student_id");
      return;
    }
    try {
      const data = await fetchJson<Material[]>(
        `${apiBase}/materials/?notebook_id=${encodeURIComponent(notebookId)}&student_id=${encodeURIComponent(studentId)}`,
      );
      setMaterials(data);
      // 默认用于知识树的 material：优先主教材，否则第一个
      const primary = data.find((m) => m.is_primary);
      const treeStillValid = treeMaterialId && data.some((m) => m.id === treeMaterialId);
      if (!treeStillValid) {
        const chosen = primary?.id || data[0]?.id || "";
        setTreeMaterialId(chosen);
        // ---- M2: materials 刷新后自动拉取知识树（进入知识树页无需手动点加载）----
        if (chosen) {
          void loadKnowledgeTree(chosen);
        }
      }
      setMessage("材料列表已更新");
    } catch (err) {
      setMessage(`读取材料失败：${(err as Error).message}`);
    }
  };

  const normalizeMastery = (raw?: number) => {
    if (typeof raw !== "number" || Number.isNaN(raw)) return 0;
    // Accept either [0,1] or [0,100]
    if (raw > 1) return Math.max(0, Math.min(1, raw / 100));
    return Math.max(0, Math.min(1, raw));
  };

  const masteryLabel = (node: KnowledgeNode) => {
    const seen = typeof node.seen === "number" ? node.seen : node.self_seen;
    if (!seen) {
      return null;
    }
    const s = normalizeMastery(
      node.mastery_score ?? node.mastery ?? (typeof node.mastery_percent === "number" ? node.mastery_percent : undefined),
    );
    if (s >= 0.8) return { text: "掌握", cls: "mastery mastery--good" };
    if (s >= 0.5) return { text: "一般", cls: "mastery mastery--mid" };
    return { text: "薄弱", cls: "mastery mastery--low" };
  };

  const masteryRatio = (node: KnowledgeNode) => {
    if (node.level !== 3) {
      return "";
    }
    const seen = typeof node.seen === "number" ? node.seen : node.self_seen;
    if (!seen) {
      return "";
    }
    const wrong = typeof node.wrong === "number" ? node.wrong : node.self_wrong;
    const wrongCount = typeof wrong === "number" ? wrong : 0;
    return `错 ${wrongCount}/${seen}`;
  };

  const nodeById = useMemo(() => {
    const map = new Map<string, KnowledgeNode>();
    const walk = (nodes: KnowledgeNode[]) => {
      nodes.forEach((node) => {
        map.set(node.id, node);
        if (node.children?.length) {
          walk(node.children);
        }
      });
    };
    walk(knowledgeTree);
    return map;
  }, [knowledgeTree]);

  const treeCount = useMemo(() => {
    let total = 0;
    const walk = (nodes: KnowledgeNode[]) => {
      nodes.forEach((node) => {
        total += 1;
        if (node.children?.length) {
          walk(node.children);
        }
      });
    };
    walk(knowledgeTree);
    return total;
  }, [knowledgeTree]);

  const loadKnowledgeTree = async (materialId?: string) => {
    const mid = (materialId ?? treeMaterialId).trim();
    if (!mid) {
      setKnowledgeTree([]);
      return;
    }
    try {
      const url = new URL(`${apiBase}/knowledge/tree`);
      url.searchParams.set("material_id", mid);
      if (studentId.trim()) url.searchParams.set("student_id", studentId.trim());
      if (notebookId.trim()) url.searchParams.set("notebook_id", notebookId.trim());
      const data = await fetchJson<KnowledgeTreeResponse>(url.toString());
      setKnowledgeTree(data.tree || []);
    } catch (err) {
      setMessage(`读取知识树失败：${(err as Error).message}`);
    }
  };

  const uploadMaterial = async () => {
    if (!uploadFile) {
      setMessage("请选择文件");
      return;
    }
    if (!studentId.trim()) {
      setMessage("请先填写 student_id");
      return;
    }
    setUploadStatus("上传中...");
    try {
      const form = new FormData();
      form.append("student_id", studentId.trim());
      form.append("notebook_id", notebookId);
      form.append("material_type", materialType);
      form.append("is_primary", String(isPrimary));
      if (uploadTitle.trim()) {
        form.append("title", uploadTitle.trim());
      }
      if (uploadSourceType !== "auto") {
        form.append("source_type", uploadSourceType);
      }
      form.append("file", uploadFile);

      const data = await fetchJson<{ id: string; status: string; job_id?: string }>(
        `${apiBase}/materials/upload`,
        { method: "POST", body: form },
      );
      setUploadStatus(`已创建：${data.id} (${data.status})`);
      await loadMaterials();
    } catch (err) {
      setUploadStatus("");
      setMessage(`上传失败：${(err as Error).message}`);
    }
  };

  const generateQuiz = async () => {
    const scopedByNode = !!selectedNodeId;
    const materialIdsForQuiz = scopedByNode
      ? (treeMaterialId ? [treeMaterialId] : [])
      : selectedMaterialIds;

    if (materialIdsForQuiz.length === 0) {
      setMessage(scopedByNode ? "请先在 M2 选择用于知识树的 material" : "请至少选择一个材料");
      return;
    }
    if (numQuestions < 1 || numQuestions > 5) {
      setMessage("题量必须在 1 到 5 之间");
      return;
    }
    if (questionTypes.length === 0) {
      setMessage("请至少选择一种题型");
      return;
    }
    try {
      setQuizStatus("出题中...");
      const payload = {
        student_id: studentId,
        notebook_id: notebookId,
        // 规则：
        // - 若在 M2 选择了章节/知识点，则以该知识树所属 material 作为出题语料，并传递 node_id 做范围约束。
        // - 若未选择章节，则使用【材料列表】中勾选的 materials 进行全局出题。
        material_ids: materialIdsForQuiz,
        num_questions: numQuestions,
        difficulty,
        question_types: questionTypes,
        // ---- M2: 按章节/知识点出题（可选）----
        node_id: selectedNodeId || undefined,
      };
      const data = await fetchJson<{ id: string; status: string }>(
        `${apiBase}/quizzes/generate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      setQuizId(data.id);
      setQuizStatus("排队中...");
      await pollQuiz(data.id);
    } catch (err) {
      setQuizStatus("");
      setMessage(`出题失败：${(err as Error).message}`);
    }
  };

  const pollQuiz = async (id: string) => {
    // Quiz generation can take longer (LLM call). Poll a bit longer and surface
    // failures to the user.
    for (let i = 0; i < 40; i += 1) {
      try {
        const data = await fetchJson<{ quiz: Quiz; questions: Question[] }>(`${apiBase}/quizzes/${id}`);
        setQuestions(data.questions || []);
        setQuizStatus(data.quiz.status || "ready");
        setAnswers({});
        if (data.quiz.status === "failed") {
          setMessage(`出题失败：${data.quiz.error_message || "unknown error"}`);
          return;
        }
        if (data.quiz.status === "ready") {
          return;
        }
      } catch (err) {
        setMessage(`查询测验失败：${(err as Error).message}`);
        return;
      }
      await sleep(1500);
    }
    setMessage("出题仍在进行中，请稍后再刷新（或检查 worker 日志/LLM KEY 配置）");
  };

  const submitAttempt = async () => {
    if (!quizId) {
      setMessage("请先生成测验");
      return;
    }
    setMessage("");
    try {
      const payload = {
        student_id: studentId,
        notebook_id: notebookId,
        // 让后端能明确把作答回流到对应的知识树范围（若后端支持这些字段则会使用；不支持也不会破坏）
        material_id: treeMaterialId || undefined,
        node_id: selectedNodeId || undefined,
        answers,
      };
      const data = await fetchJson<{ id: string; status: string }>(
        `${apiBase}/attempts/${quizId}/submit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      setAttemptId(data.id);
      await pollAttempt(data.id);
    } catch (err) {
      setMessage(`提交作答失败：${(err as Error).message}`);
    }
  };

  const pollAttempt = async (id: string) => {
    const maxTries = 30;
    for (let i = 0; i < maxTries; i += 1) {
      try {
        const data = await fetchJson<Attempt>(`${apiBase}/attempts/${id}`);
        setAttempt(data);
        if (data.status === "done") {
          await loadMistakes();
          // ---- M2: 判卷完成后刷新知识树（mastery 回流可见）----
          await loadKnowledgeTree();
          return;
        }
      } catch (err) {
        setMessage(`查询判卷失败：${(err as Error).message}`);
        return;
      }
      await sleep(2000);
    }
    setMessage("判卷仍在处理中，请稍后刷新或再次打开作答页。");
  };

  const loadMistakes = async () => {
    try {
      const data = await fetchJson<{ mistakes: Mistake[] }>(
        `${apiBase}/mistakes?student_id=${encodeURIComponent(studentId)}&notebook_id=${encodeURIComponent(notebookId)}`,
      );
      setMistakes(data.mistakes || []);
    } catch (err) {
      setMessage(`读取错题失败：${(err as Error).message}`);
    }
  };

  // ---------------- M3: Coach ----------------
  const fetchCoachLatest = async () => {
    const url = new URL(`${apiBase}/coach/latest`);
    url.searchParams.set("student_id", studentId.trim());
    if (notebookId.trim()) url.searchParams.set("notebook_id", notebookId.trim());
    if (treeMaterialId.trim()) url.searchParams.set("material_id", treeMaterialId.trim());
    return fetchJson<{ plan: CoachPlanDoc | null }>(url.toString());
  };

  const generateCoach = async () => {
    if (!studentId.trim()) {
      setMessage("请先填写 student_id");
      return;
    }
    setCoachStatus("生成小灶建议中...");
    setCoachPlanDoc(null);
    try {
      await fetchJson<{ status: string; job_id: string }>(`${apiBase}/coach/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_id: studentId.trim(),
          notebook_id: notebookId.trim() || null,
          material_id: treeMaterialId.trim() || null,
          days: 14,
          top_k: 5,
        }),
      });

      // Poll latest plan
      for (let i = 0; i < 20; i += 1) {
        const data = await fetchCoachLatest();
        if (data.plan) {
          setCoachPlanDoc(data.plan);
          setCoachStatus(data.plan.status === "failed" ? "小灶建议生成失败" : "小灶建议已生成");
          return;
        }
        await sleep(1500);
      }
      setCoachStatus("小灶建议仍在生成中，请稍后再点‘刷新’或查看 worker 日志");
    } catch (err) {
      setCoachStatus("");
      setMessage(`生成小灶建议失败：${(err as Error).message}`);
    }
  };

  const refreshCoach = async () => {
    try {
      const data = await fetchCoachLatest();
      setCoachPlanDoc(data.plan);
      setCoachStatus(data.plan ? (data.plan.status === "failed" ? "小灶建议生成失败" : "小灶建议已生成") : "暂无小灶建议");
    } catch (err) {
      setMessage(`刷新小灶建议失败：${(err as Error).message}`);
    }
  };

  const oneClickPractice = async () => {
    const oc = coachPlanDoc?.plan?.one_click_practice;
    if (!oc) {
      setMessage("暂无可用的一键再练计划");
      return;
    }
    const materialIds = (oc.material_ids && oc.material_ids.length > 0)
      ? oc.material_ids
      : (treeMaterialId ? [treeMaterialId] : selectedMaterialIds);
    if (materialIds.length === 0) {
      setMessage("缺少 material_ids：请先上传材料并在‘材料列表’勾选或选择知识树 material");
      return;
    }

    try {
      setQuizStatus("一键再练出题中...");
      const payload = {
        notebook_id: notebookId,
        material_ids: materialIds,
        num_questions: Math.max(1, Math.min(5, oc.num_questions || 5)),
        node_id: oc.node_id || undefined,
        type_mix: oc.type_mix || undefined,
        difficulty_mix: oc.difficulty_mix || undefined,
      };
      const data = await fetchJson<{ id: string; status: string }>(`${apiBase}/quizzes/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setQuizId(data.id);
      setQuestions([]);
      setAnswers({});
      await pollQuiz(data.id);
      setMessage("已按小灶建议生成‘再练’测验");
    } catch (err) {
      setMessage(`一键再练失败：${(err as Error).message}`);
    }
  };

  // ---------------- M3: Tutor ----------------
  const startTutorForQuestion = async (q: Question) => {
    const grading = gradingMap.get(q.id);
    const missing = grading?.result?.missing_points || [];
    const tags = grading?.result?.error_tags || [];
    const knowledgePoints = grading?.knowledge_points || [];
    const studentAnswer = answers[q.id] || "";

    setTutorOpen(true);
    setTutorQuestionId(q.id);
    setTutorMessages([
      { role: "assistant", content: "我们来一步步把这题做对。先从你的思路开始。" },
    ]);
    setTutorInput("");
    setTutorGiveUp(false);

    try {
      const start = await fetchJson<{ session_id: string; hint_level: string; turn: number }>(`${apiBase}/tutor/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_id: studentId.trim(),
          question_id: q.id,
          stem: q.stem,
          student_answer: studentAnswer,
          question_type: q.type,
          options: q.options || [],
          knowledge_points: knowledgePoints,
          missing_points: missing,
          error_tags: tags,
          weak_node_ids: [],
          hint_level: "L0",
        }),
      });
      setTutorSessionId(start.session_id);
      setTutorLevel(start.hint_level);
      setTutorTurn(start.turn);

      // Auto fetch the first hint
      const first = await fetchJson<{ assistant: any; hint_level: string; turn: number }>(`${apiBase}/tutor/next`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: start.session_id,
          message: studentAnswer ? `我的答案是：${studentAnswer}` : "",
          give_up: false,
        }),
      });
      const hint = first.assistant?.hint || first.assistant?.question || JSON.stringify(first.assistant);
      const ask = first.assistant?.question ? `\n\n👉 ${first.assistant.question}` : "";
      setTutorMessages((prev) => [...prev, { role: "assistant", content: `${hint}${ask}` }]);
      setTutorLevel(first.hint_level || start.hint_level);
      setTutorTurn(first.turn || start.turn + 1);
    } catch (err) {
      setMessage(`Tutor 启动失败：${(err as Error).message}`);
    }
  };

  const sendTutor = async () => {
    if (!tutorSessionId) {
      setMessage("Tutor session 未创建");
      return;
    }
    const text = tutorInput.trim();
    if (!text && !tutorGiveUp) {
      setMessage("请输入你的想法，或勾选‘我放弃’获取最终解答");
      return;
    }
    if (text) {
      setTutorMessages((prev) => [...prev, { role: "user", content: text }]);
    }
    setTutorInput("");

    try {
      const data = await fetchJson<{ assistant: any; hint_level: string; turn: number }>(`${apiBase}/tutor/next`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: tutorSessionId, message: text, give_up: tutorGiveUp }),
      });
      const hint = data.assistant?.hint || data.assistant?.answer || "";
      const q = data.assistant?.question ? `\n\n👉 ${data.assistant.question}` : "";
      const final = data.assistant?.final_answer ? `\n\n✅ 最终：${data.assistant.final_answer}` : "";
      setTutorMessages((prev) => [...prev, { role: "assistant", content: `${hint}${q}${final}`.trim() || JSON.stringify(data.assistant) }]);
      setTutorLevel(data.hint_level || tutorLevel);
      setTutorTurn(data.turn || tutorTurn + 1);
    } catch (err) {
      setMessage(`Tutor 失败：${(err as Error).message}`);
    }
  };

  const nodeColor = (node: KnowledgeNode) => {
    const seen = typeof node.seen === "number" ? node.seen : node.self_seen;
    if (!seen) {
      return "#cfd5e6";
    }
    const score = normalizeMastery(
      node.mastery_score ?? node.mastery ?? (typeof node.mastery_percent === "number" ? node.mastery_percent : undefined),
    );
    if (score >= 0.8) return "#7fc9b0";
    if (score >= 0.5) return "#e3c46f";
    return "#e28ca0";
  };

  const buildTreeSeriesNode = (node: KnowledgeNode): any => {
    const isSelected = node.id === selectedNodeId;
    const dotColor = nodeColor(node);
    return {
      name: node.title,
      rawId: node.id,
      rawLevel: node.level,
      itemStyle: {
        color: dotColor,
        borderColor: isSelected ? "#4f6ef7" : "rgba(111, 134, 255, 0.55)",
        borderWidth: isSelected ? 2 : 1,
      },
      label: {
        formatter: (params: any) => `{title|${params.name}} {dot|●}`,
        backgroundColor: "rgba(255, 255, 255, 0.95)",
        borderColor: "rgba(79, 110, 247, 0.28)",
        borderWidth: 1,
        borderRadius: 10,
        padding: [6, 10],
        rich: {
          title: {
            color: "#2b345a",
            fontWeight: isSelected ? 700 : 500,
            fontSize: 12,
            lineHeight: 18,
          },
          dot: {
            color: dotColor,
            fontSize: 12,
            padding: [0, 0, 0, 6],
          },
        },
      },
      children: (node.children || []).map(buildTreeSeriesNode),
    };
  };

  const treeRoot = useMemo(() => {
    const title =
      materials.find((m) => m.id === treeMaterialId)?.title ||
      primaryMaterial?.title ||
      "知识体系";
    if (knowledgeTree.length === 0) {
      return { name: `${title}（暂无节点）`, children: [] };
    }
    return {
      name: title,
      children: knowledgeTree.map(buildTreeSeriesNode),
    };
  }, [knowledgeTree, materials, treeMaterialId, primaryMaterial, selectedNodeId]);

  useEffect(() => {
    if (activeView !== "knowledge") {
      if (treeChartInstanceRef.current) {
        treeChartInstanceRef.current.dispose();
        treeChartInstanceRef.current = null;
      }
      return;
    }
    if (!treeChartRef.current || treeChartInstanceRef.current) return;
    const chart = echarts.init(treeChartRef.current);
    treeChartInstanceRef.current = chart;
    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.dispose();
      treeChartInstanceRef.current = null;
    };
  }, [activeView]);

  // ---- M2: 进入知识树页时自动加载（以及 material/notebook/student 变更时刷新）----
  useEffect(() => {
    if (activeView !== "knowledge") return;
    if (!treeMaterialId.trim()) return;
    void loadKnowledgeTree(treeMaterialId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, treeMaterialId, notebookId, studentId]);

  useEffect(() => {
    if (activeView !== "knowledge") return;
    const chart = treeChartInstanceRef.current;
    if (!chart) return;
    const option = {
      tooltip: {
        trigger: "item",
        triggerOn: "mousemove",
        formatter: (params: any) => {
          const rawId = params?.data?.rawId as string | undefined;
          const node = rawId ? nodeById.get(rawId) : undefined;
          if (!node) return params?.name ?? "";
          const label = masteryLabel(node);
          const ratio = masteryRatio(node);
          return [
            `<strong>${node.title}</strong>`,
            label ? `掌握度：${label.text}` : "掌握度：未测试",
            ratio ? ratio : "",
          ]
            .filter(Boolean)
            .join("<br/>");
        },
      },
      series: [
        {
          type: "tree",
          data: [treeRoot],
          top: "6%",
          left: "4%",
          bottom: "6%",
          right: "18%",
          symbol: "circle",
          symbolSize: 12,
          orient: "LR",
          expandAndCollapse: true,
          initialTreeDepth: treeExpandAll ? 999 : 2,
          animationDuration: 450,
          animationDurationUpdate: 600,
          roam: true,
          label: {
            position: "left",
            verticalAlign: "middle",
            align: "right",
            color: "#2b345a",
            backgroundColor: "rgba(255, 255, 255, 0.92)",
            padding: [6, 10],
            borderRadius: 10,
          },
          leaves: {
            label: {
              position: "right",
              align: "left",
            },
          },
          lineStyle: {
            color: "rgba(79, 110, 247, 0.4)",
            width: 1.4,
            curveness: 0.25,
          },
        },
      ],
    };
    chart.setOption(option, { notMerge: true });
    chart.off("click");
    chart.on("click", (params: any) => {
      const rawId = params?.data?.rawId as string | undefined;
      if (!rawId) return;
      const node = nodeById.get(rawId);
      if (!node) return;
      if (node.level === 3) {
        const parent = node.parent_id ? nodeById.get(node.parent_id) : undefined;
        if (parent) {
          setSelectedNodeId(parent.id);
          setSelectedNodeTitle(parent.title);
          setMessage("最小出题范围为小节，已自动选择上级小节。");
        } else {
          setMessage("最小出题范围为小节，未找到上级小节。");
        }
        return;
      }
      setSelectedNodeId(node.id);
      setSelectedNodeTitle(node.title);
    });
  }, [activeView, treeRoot, treeExpandAll, nodeById, masteryLabel, masteryRatio]);

  useEffect(() => {
    if (activeView !== "knowledge") return;
    const chart = treeChartInstanceRef.current;
    if (!chart) return;
    requestAnimationFrame(() => chart.resize());
  }, [activeView, treeHeight]);

  const toggleType = (value: string) => {
    setQuestionTypes((prev) =>
      prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value],
    );
  };

  return (
    <div className="shell">
      <div className="corner-brand">
        <span className="corner-brand__title">SmartFlow</span>
      </div>
      <aside className="sidebar">
        <nav className="nav">
          {navItems.map((item) => (
            <button
              type="button"
              key={item.id}
              className={activeView === item.id ? "nav__item is-active" : "nav__item"}
              onClick={() => setActiveView(item.id)}
            >
              <span>{item.label}</span>
              <small>{item.desc}</small>
            </button>
          ))}
        </nav>
      </aside>

      <div className="content">
        <header className="topbar">
          <div className="topbar__main">
            <div className="topbar__brand">
              <div>
                <h1>{activeNav.label}</h1>
                <p className="topbar__subtitle">{activeNav.desc}</p>
              </div>
            </div>
            <div className="topbar__actions">
              <button className="ghost" onClick={loadMaterials} disabled={!contextReady}>
                同步资料
              </button>
              <button className="ghost" onClick={() => loadKnowledgeTree()} disabled={!treeMaterialId}>
                刷新体系
              </button>
              <button className="ghost" onClick={loadMistakes} disabled={!contextReady}>
                刷新错题
              </button>
            </div>
          </div>
          <div className="topbar__context">
            <label className="control">
              <span>Notebook</span>
              <input
                value={notebookId}
                onChange={(e) => setNotebookId(e.target.value)}
                placeholder="demo-notebook"
              />
            </label>
            <label className="control">
              <span>Student</span>
              <input
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                placeholder="demo_user"
              />
            </label>
          </div>
          <div className="topbar__meta">
            <span className={primaryMaterial ? "chip chip--primary" : "chip chip--muted"}>
              主教材: {primaryMaterial ? primaryMaterial.title : "未设置"}
            </span>
            {selectedNodeTitle && <span className="chip chip--soft">章节: {selectedNodeTitle}</span>}
            {quizId && <span className="chip">测验: {quizId}</span>}
          </div>
        </header>

        {message && <div className="toast">{message}</div>}

        <main className="views">
          {activeView === "overview" && (
            <section className="view view-stack">
              <div className="card hero-card" style={cardStyle(0)}>
                <p className="eyebrow">SmartFlow</p>
                <h2>盲测 → 纠偏 → 再练</h2>
                <p className="hero__subtitle">
                  先盲测暴露知识盲点，再通过错题与知识点定位，回流到定向训练，形成首尾相接的学习闭环。
                </p>
                <div className="flow">
                  <span className="flow__step">资料导入</span>
                  <span className="flow__step">体系树</span>
                  <span className="flow__step">盲测出题</span>
                  <span className="flow__step">判卷纠偏</span>
                  <span className="flow__step">定向再练</span>
                </div>
                <div className="cta-row">
                  <button onClick={() => setActiveView("materials")}>上传资料</button>
                  <button className="ghost" onClick={() => setActiveView("quiz")}>开始盲测</button>
                </div>
              </div>
              <div className="view-grid">
                <div className="card" style={cardStyle(1)}>
                  <h3>当前 Notebook</h3>
                  <ul className="info-list">
                    <li>材料数：{materials.length}</li>
                    <li>主教材：{primaryMaterial ? "已设置" : "未设置"}</li>
                    <li>知识点节点：{treeCount || 0}</li>
                    <li>错题数量：{mistakes.length}</li>
                  </ul>
                </div>
                <div className="card" style={cardStyle(2)}>
                  <h3>关键状态</h3>
                  <ul className="info-list">
                    <li>测验编号：{quizId || "--"}</li>
                    <li>测验状态：{quizStatus || "--"}</li>
                    <li>判卷状态：{attempt?.status || "--"}</li>
                    <li>章节范围：{selectedNodeTitle || "全局"}</li>
                  </ul>
                </div>
                <div className="card" style={cardStyle(3)}>
                  <h3>下一步建议</h3>
                  <p className="muted">
                    {primaryMaterial
                      ? "建议先盲测，判卷后点击错题直达再练。"
                      : "请先设置主教材，才能生成体系树与章节出题。"}
                  </p>
                  <div className="cta-row">
                    <button className="ghost" onClick={() => setActiveView("knowledge")}>查看体系树</button>
                    <button className="ghost" onClick={() => setActiveView("review")}>查看错题</button>
                  </div>
                </div>
              </div>
            </section>
          )}

          {activeView === "materials" && (
            <section className="view view-grid">
              <section className="card" style={cardStyle(0)}>
                <h2>上传与解析</h2>
                <p className="muted">支持 PDF / DOCX / MP3，解析后可用于出题与知识树。</p>
                <div className="form">
                  <label className="file">
                    <input
                      type="file"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    />
                    <span>{uploadFile ? uploadFile.name : "选择文件"}</span>
                  </label>
                  <div className="row">
                    <input
                      placeholder="标题（可选）"
                      value={uploadTitle}
                      onChange={(e) => setUploadTitle(e.target.value)}
                    />
                    <select value={materialType} onChange={(e) => setMaterialType(e.target.value)}>
                      <option value="textbook">教材</option>
                      <option value="note">笔记</option>
                      <option value="handout">讲义</option>
                      <option value="other">其他</option>
                    </select>
                  </div>
                  <div className="row">
                    <select value={uploadSourceType} onChange={(e) => setUploadSourceType(e.target.value)}>
                      <option value="auto">自动识别类型</option>
                      <option value="pdf">PDF</option>
                      <option value="docx">DOCX</option>
                      <option value="audio">音频</option>
                      <option value="text">TXT</option>
                    </select>
                    <label className="toggle">
                      <input
                        type="checkbox"
                        checked={isPrimary}
                        onChange={(e) => setIsPrimary(e.target.checked)}
                      />
                      设为主教材（唯一）
                    </label>
                  </div>
                  <button onClick={uploadMaterial}>上传并解析</button>
                  {uploadStatus && <p className="status">{uploadStatus}</p>}
                </div>
              </section>

              <section className="card" style={cardStyle(1)}>
                <h2>资料库</h2>
                <p className="muted">
                  用于全局出题的材料范围。若你在知识树选择了章节，则出题以主教材为准并按章节约束。
                </p>
                <div className="list">
                  {materials.length === 0 && <p className="muted">暂无材料</p>}
                  {materials.map((item) => (
                    <label key={item.id} className="list-item">
                      <input
                        type="checkbox"
                        checked={Boolean(selectedMaterials[item.id])}
                        onChange={(e) =>
                          setSelectedMaterials((prev) => ({
                            ...prev,
                            [item.id]: e.target.checked,
                          }))
                        }
                      />
                      <div>
                        <strong>{item.title}</strong>
                        <span className={`chip chip--${item.status}`}>{item.status}</span>
                        {item.is_primary && <span className="chip chip--primary">主教材</span>}
                      </div>
                      <small>
                        {item.source_type} · chunks {item.text_chunk_count}
                        {item.summary_chunk_count ? ` / summary ${item.summary_chunk_count}` : ""}
                      </small>
                    </label>
                  ))}
                </div>
              </section>
            </section>
          )}

          {activeView === "knowledge" && (
            <section className="view view-stack">
              <section className="card" style={cardStyle(0)}>
                <h2>知识体系树</h2>
                <p className="muted">
                  交互式树状图支持伸缩。默认展开到“节”，点击节点可选为出题范围。
                </p>
                {!primaryMaterial && (
                  <div className="callout">
                    <strong>请先设置主教材</strong>
                    <span>主教材是知识体系树的唯一来源。</span>
                  </div>
                )}
                <div className="form">
                  <div className="row">
                    <label>
                      用于知识树的 material
                      <select
                        value={treeMaterialId}
                        onChange={(e) => {
                          const v = e.target.value;
                          setTreeMaterialId(v);
                          setSelectedNodeId("");
                          setSelectedNodeTitle("");
                          void loadKnowledgeTree(v);
                        }}
                      >
                        <option value="">-- 请选择 --</option>
                        {materials.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.title}{m.is_primary ? "（主）" : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button type="button" className="ghost" onClick={() => loadKnowledgeTree()}>
                      加载/刷新
                    </button>
                    <button type="button" className="ghost" onClick={() => setTreeExpandAll(true)}>
                      展开知识点
                    </button>
                    <button type="button" className="ghost" onClick={() => setTreeExpandAll(false)}>
                      收起知识点
                    </button>
                  </div>
                  <div className="muted">
                    当前章节：<strong>{selectedNodeTitle || "（未选择，默认全局出题）"}</strong>
                  </div>
                </div>
                <div className="tree-chart-wrap">
                  <div className="tree-chart__controls">
                    <span>图谱尺寸</span>
                    <input
                      type="range"
                      min={440}
                      max={820}
                      step={20}
                      value={treeHeight}
                      onChange={(e) => setTreeHeight(Number(e.target.value))}
                    />
                    <span>{treeHeight}px</span>
                  </div>
                  <div ref={treeChartRef} className="tree-chart" style={{ height: treeHeight }} />
                  {knowledgeTree.length === 0 && (
                    <div className="tree-chart__empty">暂无知识树，请先上传并解析材料。</div>
                  )}
                </div>
                <div className="cta-row">
                  <button
                    className="ghost"
                    disabled={!selectedNodeId}
                    onClick={() => setActiveView("quiz")}
                  >
                    针对该节出题
                  </button>
                  <button className="ghost" onClick={() => setActiveView("review")}>
                    查看错题汇总
                  </button>
                </div>
              </section>
            </section>
          )}

          {activeView === "quiz" && (
            <section className="view view-grid">
              <section className="card" style={cardStyle(0)}>
                <h2>出题设置</h2>
                <p className="muted">
                  {selectedNodeId
                    ? `当前范围：${selectedNodeTitle}（按章节出题）`
                    : "当前为全局出题（使用材料列表勾选范围）"}
                </p>
                <div className="form">
                  <div className="row">
                    <label>
                      题量
                      <input
                        type="number"
                        min={1}
                        max={5}
                        value={numQuestions}
                        onChange={(e) => setNumQuestions(Number(e.target.value))}
                      />
                    </label>
                    <label>
                      难度
                      <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                        <option value="简单">简单</option>
                        <option value="正常">正常</option>
                        <option value="难">困难</option>
                      </select>
                    </label>
                  </div>
                  <div className="row tags">
                    {"选择 填空 问答".split(" ").map((type) => (
                      <button
                        type="button"
                        key={type}
                        className={questionTypes.includes(type) ? "tag active" : "tag"}
                        onClick={() => toggleType(type)}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                  <button onClick={generateQuiz}>生成测验</button>
                  {quizStatus && <p className="status">{quizStatus}</p>}
                </div>
              </section>

              <section className="card" style={cardStyle(1)}>
                <h2>作答与判卷</h2>
                <p className="muted">测验编号：{quizId || "--"}</p>
                {questions.length === 0 ? (
                  <p className="muted">请先生成测验。</p>
                ) : (
                  <div className="questions">
                    {questions.map((q, index) => {
                      const grading = gradingMap.get(q.id);
                      const isCorrect = grading?.is_correct ?? grading?.result?.is_correct;
                      const score = grading?.score ?? grading?.result?.score;
                      const mistakeAdded = grading?.mistake_added ?? (isCorrect === false);
                      const result = grading?.result;
                      const analysisText = result?.analysis || grading?.analysis || "";
                      return (
                        <div key={q.id} className="question">
                          <div className="question__header">
                            <span>Q{index + 1} · {q.type.toUpperCase()}</span>
                          </div>
                          <MathText as="p" text={q.stem} />
                          {q.type === "mcq" && q.options ? (
                            <div className="options">
                              {q.options.map((opt) => (
                                <label key={opt}>
                                  <input
                                    type="radio"
                                    name={q.id}
                                    value={opt}
                                    checked={answers[q.id] === opt}
                                    onChange={(e) =>
                                      setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                                    }
                                  />
                                  <MathText text={opt} />
                                </label>
                              ))}
                            </div>
                          ) : q.type === "short" ? (
                            <textarea
                              rows={3}
                              placeholder="请输入你的解答..."
                              value={answers[q.id] || ""}
                              onChange={(e) =>
                                setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                              }
                            />
                          ) : (
                            <input
                              placeholder="填写答案..."
                              value={answers[q.id] || ""}
                              onChange={(e) =>
                                setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                              }
                            />
                          )}
                          {grading && (
                            <div className="grading">
                              <div className="grading-block">
                                <strong>正确答案：</strong> <MathText text={result?.correct_answer || "--"} />
                              </div>
                              <div className="grading-block">
                                <strong>你的答案：</strong> <MathText text={result?.student_answer || "--"} />
                              </div>
                              {analysisText && (
                                <div className="grading-block">
                                  <strong>解析：</strong> <MathText text={analysisText} />
                                </div>
                              )}
                              <div className="grading-meta">
                                <span>得分：{typeof score === "number" ? score.toFixed(2) : "--"}</span>
                                <span>判定：{isCorrect ? "正确" : "错误"}</span>
                                <span>错题本：{mistakeAdded ? "已加入" : "未加入"}</span>
                              </div>
                              {isCorrect === false && (
                                <div className="grading-actions">
                                  <button
                                    type="button"
                                    className="ghost"
                                    onClick={() => startTutorForQuestion(q)}
                                  >
                                    Tutor 引导
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                    <button onClick={submitAttempt}>提交作答</button>
                  </div>
                )}
                {attempt && (
                  <div className="result">
                    <p>
                      判卷状态：<strong>{attempt.status}</strong>
                    </p>
                    {attemptId && <p className="muted">attempt_id: {attemptId}</p>}
                  </div>
                )}
              </section>
            </section>
          )}

          {activeView === "review" && (
            <section className="view view-grid">
              <section className="card" style={cardStyle(0)}>
                <h2>小灶建议</h2>
                <p className="muted">根据错题与薄弱点生成针对性练习建议。</p>
                <div className="cta-row">
                  <button onClick={generateCoach}>生成小灶</button>
                  <button className="ghost" onClick={refreshCoach}>刷新</button>
                  <button className="ghost" onClick={oneClickPractice}>一键再练</button>
                </div>
                {coachStatus && <p className="status">{coachStatus}</p>}
                {coachPlanDoc?.plan ? (
                  <div className="coach">
                    <h3>诊断摘要</h3>
                    <p className="muted">{coachPlanDoc.plan.diagnosis?.summary || "--"}</p>
                    <h4>纠偏动作</h4>
                    <ul className="info-list">
                      {(coachPlanDoc.plan.corrective_actions || []).slice(0, 3).map((item, idx) => (
                        <li key={`${item.issue}-${idx}`}>{item.issue || "--"} · {item.how_to_fix || "--"}</li>
                      ))}
                    </ul>
                    <h4>训练计划</h4>
                    <ul className="info-list">
                      {(coachPlanDoc.plan.practice_plan || []).slice(0, 3).map((item, idx) => (
                        <li key={`${item.level}-${idx}`}>
                          {item.level || "L"} · {item.notes || "--"}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="muted">暂无小灶建议。</p>
                )}
              </section>

              <section className="card" style={cardStyle(1)}>
                <h2>错题与薄弱点</h2>
                <p className="muted">按 Notebook 聚合错题记录，支持回到出题页再练。</p>
                <div className="mistake-grid">
                  {mistakes.length === 0 && <p className="muted">暂无错题。</p>}
                  {mistakes.map((m) => (
                    <div key={m.id} className="mistake-card">
                      <h3>{m.knowledge_points.join(" / ") || "未命名知识点"}</h3>
                      {m.last_question && <MathText as="p" text={m.last_question} />}
                      <div className="mistake-meta">
                        <span>你的答案：{m.last_student_answer || "--"}</span>
                        <span>正确答案：{m.last_correct_answer || "--"}</span>
                      </div>
                      {m.last_error_analysis && (
                        <p className="muted">错因：{m.last_error_analysis}</p>
                      )}
                      <div className="mistake-meta">
                        <span>累计次数：{m.wrong_count}</span>
                        <span>错因标签：{m.error_tags.join(" / ") || "--"}</span>
                      </div>
                      <div className="cta-row">
                        <button className="ghost" onClick={() => setActiveView("quiz")}>再练这个点</button>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </section>
          )}
        </main>

        {tutorOpen && (
          <div className="modal">
            <div className="modal__backdrop" onClick={() => setTutorOpen(false)} />
            <div className="modal__content">
              <header className="modal__header">
                <div>
                  <h3>Tutor 引导</h3>
                  <p className="muted">逐步提示，不直接泄露答案。</p>
                </div>
                <button type="button" className="ghost" onClick={() => setTutorOpen(false)}>
                  关闭
                </button>
              </header>
              <div className="modal__body">
                <div className="chat">
                  {tutorMessages.map((msg, idx) => (
                    <div key={`${msg.role}-${idx}`} className={`chat__bubble ${msg.role}`}>
                      <MathText as="p" text={msg.content} />
                    </div>
                  ))}
                </div>
                <div className="chat__controls">
                  <textarea
                    rows={2}
                    placeholder="输入你的思路..."
                    value={tutorInput}
                    onChange={(e) => setTutorInput(e.target.value)}
                  />
                  <label className="toggle">
                    <input
                      type="checkbox"
                      checked={tutorGiveUp}
                      onChange={(e) => setTutorGiveUp(e.target.checked)}
                    />
                    我放弃，直接给出最终提示
                  </label>
                  <button onClick={sendTutor}>发送</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
