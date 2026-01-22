
import React, { useEffect, useState, useRef, useMemo } from 'react';
import { KeywordAnalysis, Discipline, GraphData, GraphNode } from '../types';
import { DisciplineIcon } from './Icons';

interface ContextScreenProps {
  analysis: KeywordAnalysis;
  graphData?: GraphData; // 添加graphData prop
  onDisciplineSelect: (discipline: Discipline) => void;
  onNodeSelect?: (discipline: Discipline, details: any) => void;
  onBack: () => void;
}

const MORANDI_PALETTE = [
  '#b8c2bb', '#c5aeb1', '#aebdc5', '#d5c8b8', '#c1b8c5', '#cad1b8', '#b8c5c5',
];
const FIELD_COLOR_MAP: Record<string, string> = {
  '数学': MORANDI_PALETTE[0],
  '物理': MORANDI_PALETTE[2],
  '计算机/AI': MORANDI_PALETTE[3],
  '生物/神经科学': MORANDI_PALETTE[5],
  '社会科学/经济学': MORANDI_PALETTE[4],
};
const FIELD_ICON_MAP: Record<string, string> = {
  '数学': 'scale',
  '物理': 'car',
  '计算机/AI': 'laptop',
  '生物/神经科学': 'tree',
  '社会科学/经济学': 'book',
};

const ContextScreen: React.FC<ContextScreenProps> = ({ analysis, graphData, onDisciplineSelect, onBack }) => {
  // 调试信息已移除以避免控制台噪音
  useEffect(() => {
    // keep a minimal loaded flag
  }, [graphData, analysis]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [ripples, setRipples] = useState<Array<{ id: number; x: number; y: number; timestamp: number }>>([]);
  const [lastMouseMove, setLastMouseMove] = useState<number>(Date.now());
  const [isCreatingRipples, setIsCreatingRipples] = useState(false);
  
  
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [selectedChild, setSelectedChild] = useState<GraphNode | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedChild(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
 
  const [hoveredBranch, setHoveredBranch] = useState<{ discipline: string; nodeId: string; x: number; y: number } | null>(null);
  // selectedRelation popup removed
  
  const containerRef = useRef<HTMLDivElement>(null);
  const [layoutVersion, setLayoutVersion] = useState(0);
  const rippleIdRef = useRef(0);
  const mouseTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const rippleIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentMousePosRef = useRef({ x: 0, y: 0 });
  
  useEffect(() => {
    // 确保组件挂载后再触发动画
    const timer = setTimeout(() => setIsLoaded(true), 150);
    return () => clearTimeout(timer);
  }, []);

  // 鼠标跟踪和波动效果
  useEffect(() => {
    const createRipple = (x: number, y: number) => {
      const rippleId = ++rippleIdRef.current;
      const newRipple = {
        id: rippleId,
        x: x,
        y: y,
        timestamp: Date.now()
      };

      setRipples(prev => [...prev, newRipple]);

      // 2秒后移除这个波纹，让波纹更快消失
      setTimeout(() => {
        setRipples(prev => prev.filter(r => r.id !== rippleId));
      }, 2000);
    };

    const handleMouseMove = (e: MouseEvent) => {
      const newPos = { x: e.clientX, y: e.clientY };
      setMousePosition(newPos);
      currentMousePosRef.current = newPos;
      setLastMouseMove(Date.now());
      setIsCreatingRipples(false);

      // 清除之前的定时器
      if (mouseTimeoutRef.current) {
        clearTimeout(mouseTimeoutRef.current);
      }
      if (rippleIntervalRef.current) {
        clearInterval(rippleIntervalRef.current);
        rippleIntervalRef.current = null;
      }

      // 鼠标悬停1秒后，开始持续产生波纹
      mouseTimeoutRef.current = setTimeout(() => {
        setIsCreatingRipples(true);
        // 每3秒产生一个波纹
        rippleIntervalRef.current = setInterval(() => {
          createRipple(currentMousePosRef.current.x, currentMousePosRef.current.y);
        }, 3000);
      }, 1000); // 1秒后开始
    };

    const handleMouseLeave = () => {
      if (mouseTimeoutRef.current) {
        clearTimeout(mouseTimeoutRef.current);
      }
      if (rippleIntervalRef.current) {
        clearInterval(rippleIntervalRef.current);
        rippleIntervalRef.current = null;
      }
      setIsCreatingRipples(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      if (mouseTimeoutRef.current) {
        clearTimeout(mouseTimeoutRef.current);
      }
      if (rippleIntervalRef.current) {
        clearInterval(rippleIntervalRef.current);
      }
    };
  }, []);

  // 网状布局计算
  const canvasWidth = 2000;
  const canvasHeight = 1200;
  const centerX = canvasWidth / 2;
  const centerY = canvasHeight / 2;

  // Helper: get element center relative to container
  const getElementCenter = (el: HTMLElement | null) => {
    if (!el || !containerRef.current) return null;
    const containerRect = containerRef.current.getBoundingClientRect();
    const rect = el.getBoundingClientRect();
    return {
      x: rect.left + rect.width / 2 - containerRect.left,
      y: rect.top + rect.height / 2 - containerRect.top
    };
  };

  // Recompute endpoints on scroll/resize so line endpoints stay aligned with DOM centers
  useEffect(() => {
    const sc = containerRef.current;
    if (!sc) return;
    const onScroll = () => setLayoutVersion(v => v + 1);
    const onResize = () => setLayoutVersion(v => v + 1);
    sc.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize);
    return () => {
      sc.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onResize);
    };
  }, [containerRef.current]);

  // 当 graphData 更新时，强制重新计算布局并触发重绘（处理 LLM 数据替换旧 mock 的情形）
  useEffect(() => {
    if (!graphData) return;
    // bump layout version to force any position/recomputation hooks to run
    setLayoutVersion(v => v + 1);
    // retrigger load animation to ensure DOM centers are recalculated after render
    setIsLoaded(false);
    const t = setTimeout(() => setIsLoaded(true), 120);
    return () => clearTimeout(t);
  }, [graphData]);

  // 学科分支位置计算 (根据跨学科连接重排顺序，使有关联的学科彼此邻近)
  const computeDisciplineOrder = () => {
    const fields = Object.keys(disciplineGroups);
    // build weight map between fields based on detailedNodeRelations
    const weight: Record<string, Record<string, number>> = {};
    fields.forEach(f => (weight[f] = {}));
    detailedNodeRelations.forEach(rel => {
      const sField = allNodes.find(n => n.id === rel.source)?.field;
      const tField = allNodes.find(n => n.id === rel.target)?.field;
      if (sField && tField && sField !== tField) {
        // cross_discipline carries higher influence
        const weightIncrease = rel.type === 'cross_discipline' ? 2 : 1;
        weight[sField][tField] = (weight[sField][tField] || 0) + weightIncrease;
        weight[tField][sField] = (weight[tField][sField] || 0) + weightIncrease;
      }
    });

    // total connection strength per field
    const totalWeight: Record<string, number> = {};
    fields.forEach(f => {
      totalWeight[f] = Object.values(weight[f] || {}).reduce((a, b) => a + b, 0);
    });

    const remaining = new Set(fields);
    const order: string[] = [];

    // start with max totalWeight
    let start = fields[0];
    let maxW = -1;
    fields.forEach(f => {
      if (totalWeight[f] > maxW) { maxW = totalWeight[f]; start = f; }
    });
    order.push(start);
    remaining.delete(start);

    // Greedy: always append the remaining field most strongly connected to the last placed field.
    // This ensures fields with direct cross-discipline links become neighbors.
    while (remaining.size > 0) {
      const last = order[order.length - 1];
      let best: string | null = null;
      let bestScore = -1;

      remaining.forEach(f => {
        const conn = weight[last][f] || 0;
        if (conn > bestScore) {
          bestScore = conn;
          best = f;
        }
      });

      // if no direct connection to last, pick the remaining with highest totalWeight
      if (bestScore <= 0) {
        remaining.forEach(f => {
          if ((totalWeight[f] || 0) > bestScore) {
            bestScore = totalWeight[f] || 0;
            best = f;
          }
        });
      }

      if (!best) {
        const it = remaining.values();
        best = it.next().value;
      }

      order.push(best);
      remaining.delete(best);
    }
    // Post-process: enforce adjacency for pairs with cross-discipline links.
    // For each field pair with non-zero weight, move the second field to be adjacent to the first.
    const adjacencyPairs: Array<[string, string]> = [];
    fields.forEach(f => {
      Object.keys(weight[f] || {}).forEach(t => {
        if ((weight[f][t] || 0) > 0 && f !== t) {
          adjacencyPairs.push([f, t]);
        }
      });
    });

    // Deduplicate symmetric pairs
    const seenPair = new Set<string>();
    adjacencyPairs.forEach(([a, b]) => {
      const pairKey = [a, b].sort().join('|');
      if (seenPair.has(pairKey)) return;
      seenPair.add(pairKey);
      const ia = order.indexOf(a);
      const ib = order.indexOf(b);
      if (ia === -1 || ib === -1) return;
      if (Math.abs(ia - ib) === 1) return; // already adjacent

      // Remove b from its current position and insert it right after a
      order.splice(ib, 1);
      const newIa = order.indexOf(a);
      order.splice(newIa + 1, 0, b);
    });

    return order;
  };

  // orderedFields and disciplinePositions will be computed after allNodes/disciplineGroups are defined

  // 从实际数据中获取所有节点（包括通过API调用获取的完整数据）
  // 优先从 graphData 找到 core 节点（LLM 生成），否则回退到 analysis.disciplines
  let coreNode = null;
  if (graphData?.nodes) {
    const core = graphData.nodes.find(n => n.type === 'core' || n.field === '核心' || n.id.toLowerCase().includes('core'));
    if (core) {
      coreNode = {
        id: core.id,
        name: core.label,
        field: core.field,
        icon: FIELD_ICON_MAP[core.field] || 'book',
        shortSummary: core.summary || core.label
      };
    }
  }
  if (!coreNode) {
    coreNode = (analysis?.disciplines && analysis.disciplines.find(d => d.name === '熵')) || (analysis?.disciplines && analysis.disciplines[0]) || { id: 'root', name: analysis?.keyword || '根节点', field: '核心', icon: 'book', shortSummary: '' };
  }

  // 使用graphData中的实际节点数据，如果没有则回退到analysis数据
  const allNodes = useMemo(() => {
    if (graphData?.nodes) {
      // 从LLM返回的数据中提取节点信息，修复field字段的编码问题
      return graphData.nodes.map(node => {
        // 修复field字段的编码问题 - 基于LLM返回的实际乱码模式
        let fixedField = node.field;
        if (node.field === '??????') fixedField = '核心';
        else if (node.field === '???��?-|') fixedField = '数学';
        else if (node.field === '??????') fixedField = '物理';
        else if (node.field === '��???????o/AI') fixedField = '计算机/AI';
        else if (node.field === '??????/?��?????��??-|') fixedField = '生物/神经科学';
        else if (node.field === '?��?????��??-|/????��??-|') fixedField = '社会科学/经济学';
        else if (node.field.includes('数学') || node.field.includes('Math')) fixedField = '数学';
        else if (node.field.includes('物理') || node.field.includes('Physics')) fixedField = '物理';
        else if (node.field.includes('计算机') || node.field.includes('AI') || node.field.includes('Computer')) fixedField = '计算机/AI';
        else if (node.field.includes('生物') || node.field.includes('Bio')) fixedField = '生物/神经科学';
        else if (node.field.includes('社会') || node.field.includes('Social')) fixedField = '社会科学/经济学';
        else fixedField = '核心'; // 默认归为核心

        return {
          id: node.id,
          name: node.label,
          field: fixedField,
          icon: FIELD_ICON_MAP[fixedField] || 'book',
          shortSummary: node.summary || `${node.label}的概念`,
          // 添加LLM额外字段
          details: node.details,
          keyPoints: node.key_points,
          readingHint: node.reading_hint
        };
      });
    } else {
      // 回退到硬编码数据（向后兼容）
      return [
        { id: 'Entropy', name: '熵', field: '核心', icon: 'book', shortSummary: '刻画系统不确定性或无序程度的量' },
        { id: 'ThermodynamicEntropy', name: '热力学熵', field: '物理', icon: 'car', shortSummary: '用于描述宏观热力学过程不可逆性与能量弥散的状态函数' },
        { id: 'BoltzmannFormula', name: '玻尔兹曼公式 S = k ln W', field: '物理', icon: 'car', shortSummary: '将熵与微观状态数联系起来的关键公式' },
        { id: 'MicrostateCount', name: '微观状态数', field: '物理', icon: 'car', shortSummary: '系统在给定宏观约束下可实现的微观配置数量' },
        { id: 'InformationEntropy', name: '信息熵（香农熵）', field: '数学', icon: 'scale', shortSummary: '度量随机变量不确定性的函数，常写作 H = -Σ p log p' },
        { id: 'ProbabilityDistribution', name: '概率分布', field: '数学', icon: 'scale', shortSummary: '描述随机事件取值及其概率的函数或表' },
        { id: 'LogFunction', name: '对数函数', field: '数学', icon: 'scale', shortSummary: '将乘法结构转化为加法结构的函数' },
        { id: 'KLDivergence', name: 'KL 散度', field: '数学', icon: 'scale', shortSummary: '度量两个概率分布差异的非对称量' },
        { id: 'CrossEntropy', name: '交叉熵', field: '计算机/AI', icon: 'laptop', shortSummary: '用于衡量预测分布与真实分布差异的损失函数' },
        { id: 'Softmax', name: 'Softmax', field: '计算机/AI', icon: 'laptop', shortSummary: '将实数向量映射为概率分布的函数' },
        { id: 'MaximumEntropyPrinciple', name: '最大熵原理', field: '数学', icon: 'scale', shortSummary: '在已知约束下选择熵最大的分布' },
        { id: 'FreeEnergy', name: '自由能', field: '物理', icon: 'car', shortSummary: '结合能量与熵效应的量' },
        { id: 'VariationalInference', name: '变分推断', field: '计算机/AI', icon: 'laptop', shortSummary: '通过优化可计算下界来近似复杂后验分布' },
        { id: 'ELBO', name: '证据下界（ELBO）', field: '计算机/AI', icon: 'laptop', shortSummary: '变分推断中的目标函数' },
        { id: 'NeuralCoding', name: '神经编码', field: '生物/神经科学', icon: 'tree', shortSummary: '研究神经系统如何用放电模式表示信息' },
        { id: 'MutualInformation', name: '互信息', field: '数学', icon: 'scale', shortSummary: '度量两个随机变量共享信息量的指标' },
        { id: 'DecisionUncertainty', name: '决策不确定性', field: '社会科学/经济学', icon: 'book', shortSummary: '在不完全信息条件下对结果分布的不确定感' },
        { id: 'RiskAversion', name: '风险厌恶', field: '社会科学/经济学', icon: 'book', shortSummary: '偏好确定收益、厌恶波动的行为倾向' },
        { id: 'UtilityFunction', name: '效用函数', field: '社会科学/经济学', icon: 'book', shortSummary: '用数值刻画偏好结构的函数' },
        { id: 'Regularization', name: '正则化', field: '计算机/AI', icon: 'laptop', shortSummary: '在学习中引入约束以改善泛化能力' },
      ];
    }
  }, [graphData]);

  // 基于entropy.json的完整节点数据进行分组
  const disciplineGroups = useMemo(() => {
    const groups = {
      '数学': allNodes.filter(node => node.field === '数学'),
      '物理': allNodes.filter(node => node.field === '物理'),
      '计算机/AI': allNodes.filter(node => node.field === '计算机/AI'),
      '生物/神经科学': allNodes.filter(node => node.field === '生物/神经科学'),
      '社会科学/经济学': allNodes.filter(node => node.field === '社会科学/经济学'),
    };
    // removed debug logging to reduce console noise
    return groups;
  }, [allNodes]);

  // 使用graphData中的edges数据，如果没有则回退到硬编码数据
  const detailedNodeRelations = useMemo(() => {
    if (graphData?.edges) {
      // 从LLM返回的数据中提取边信息
      return graphData.edges.map(edge => ({
        source: edge.source,
        target: edge.target,
        relation: edge.relation, // LLM返回的relation已经是处理过的，可能还有乱码但先保持
        type: edge.relation_type || 'unknown',
        evidence: edge.evidence,
        confidence: edge.confidence,
        direction: edge.direction || 'undirected',
        reasoning_chain: edge.reasoning_chain,
        tags: edge.tags
      }));
    } else {
      // 回退到硬编码数据（向后兼容）
      return [
        // 数学内部关系
        { source: 'InformationEntropy', target: 'ProbabilityDistribution', relation: '定义基于概率分布', type: 'math_internal' },
        { source: 'InformationEntropy', target: 'LogFunction', relation: '使用对数函数计算', type: 'math_internal' },
        { source: 'InformationEntropy', target: 'KLDivergence', relation: '推广为相对熵', type: 'math_internal' },
        { source: 'KLDivergence', target: 'CrossEntropy', relation: '构成交叉熵基础', type: 'math_internal' },

        // 物理内部关系
        { source: 'ThermodynamicEntropy', target: 'BoltzmannFormula', relation: '通过玻尔兹曼公式量化', type: 'physics_internal' },
        { source: 'BoltzmannFormula', target: 'MicrostateCount', relation: '与微观状态数相关', type: 'physics_internal' },
        { source: 'ThermodynamicEntropy', target: 'FreeEnergy', relation: '影响自由能计算', type: 'physics_internal' },

        // AI内部关系
        { source: 'CrossEntropy', target: 'Softmax', relation: '常与Softmax结合使用', type: 'ai_internal' },
        { source: 'VariationalInference', target: 'ELBO', relation: '通过ELBO优化', type: 'ai_internal' },
        { source: 'ELBO', target: 'KLDivergence', relation: '包含KL散度项', type: 'ai_internal' },

        // 跨学科关系 - 重点关系用于测试相邻排序
        { source: 'MutualInformation', target: 'NeuralCoding', relation: '用于神经编码分析', type: 'cross_discipline' },
        // 其他跨学科关系
        { source: 'InformationEntropy', target: 'CrossEntropy', relation: '在机器学习中作为损失函数', type: 'cross_discipline' },
        { source: 'BoltzmannFormula', target: 'LogFunction', relation: '使用对数函数进行计算', type: 'cross_discipline' },
        { source: 'KLDivergence', target: 'VariationalInference', relation: '在变分推断中作为优化目标', type: 'cross_discipline' },
      ];
    }
  }, [graphData]);

  // compute ordered fields and positions now that disciplineGroups, allNodes, and detailedNodeRelations exist
  const orderedFields = useMemo(() => {
    const fields = Object.keys(disciplineGroups);

    // build weight map between fields based on detailedNodeRelations (cross_discipline has stronger weight)
    const weight: Record<string, Record<string, number>> = {};
    fields.forEach(f => (weight[f] = {}));
    detailedNodeRelations.forEach(rel => {
      const sField = allNodes.find(n => n.id === rel.source)?.field;
      const tField = allNodes.find(n => n.id === rel.target)?.field;
      if (sField && tField && sField !== tField) {
        const inc = rel.type === 'cross_discipline' ? 2 : 1;
        if (!weight[sField]) weight[sField] = {};
        if (!weight[tField]) weight[tField] = {};
        weight[sField][tField] = (weight[sField][tField] || 0) + inc;
        weight[tField][sField] = (weight[tField][sField] || 0) + inc;
      }
    });

    // build neighbor sets for connected components (using any non-zero weight)
    const neighbors: Record<string, Set<string>> = {};
    fields.forEach(f => (neighbors[f] = new Set<string>()));
    fields.forEach(f => {
      Object.keys(weight[f] || {}).forEach(t => {
        if ((weight[f][t] || 0) > 0) {
          // ensure both sides exist in neighbors
          if (!neighbors[f]) neighbors[f] = new Set<string>();
          if (!neighbors[t]) neighbors[t] = new Set<string>();
          neighbors[f].add(t);
          neighbors[t].add(f);
        }
      });
    });

    // find connected components of fields based on neighbor links
    const visited = new Set<string>();
    const components: string[][] = [];
    fields.forEach(f => {
      if (visited.has(f)) return;
      const stack = [f];
      const comp: string[] = [];
      visited.add(f);
      while (stack.length) {
        const cur = stack.pop() as string;
        comp.push(cur);
        const curNeighbors = neighbors[cur];
        if (!curNeighbors) continue;
        curNeighbors.forEach(nb => {
          if (!visited.has(nb)) {
            visited.add(nb);
            stack.push(nb);
          }
        });
      }
      components.push(comp);
    });

    // compute totalWeight per field
    const totalWeight: Record<string, number> = {};
    fields.forEach(f => {
      totalWeight[f] = Object.values(weight[f] || {}).reduce((a, b) => a + b, 0);
    });

    // order components by maximum totalWeight inside component (so stronger components come first)
    components.sort((a, b) => {
      const aw = Math.max(...a.map(x => totalWeight[x] || 0));
      const bw = Math.max(...b.map(x => totalWeight[x] || 0));
      return bw - aw;
    });

    // inside each component, order fields greedily to place directly connected fields adjacent
    const result: string[] = [];
    components.forEach(comp => {
      if (comp.length === 1) {
        result.push(comp[0]);
        return;
      }
      // pick start as node with highest totalWeight in comp
      let start = comp[0];
      let maxW = -1;
      comp.forEach(f => { if ((totalWeight[f] || 0) > maxW) { maxW = totalWeight[f]; start = f; } });
      const remaining = new Set(comp);
      const subOrder: string[] = [];
      subOrder.push(start);
      remaining.delete(start);
      while (remaining.size > 0) {
        const last = subOrder[subOrder.length - 1];
        let best: string | null = null;
        let bestScore = -1;
        remaining.forEach(f => {
          const conn = weight[last][f] || 0;
          if (conn > bestScore) { bestScore = conn; best = f; }
        });
        if (!best) {
          // fallback to highest totalWeight in remaining
          remaining.forEach(f => {
            if ((totalWeight[f] || 0) > bestScore) { bestScore = totalWeight[f] || 0; best = f; }
          });
        }
        if (!best) {
          const it = remaining.values();
          best = it.next().value;
        }
        subOrder.push(best);
        remaining.delete(best);
      }
      // append the ordered fields from this component
      result.push(...subOrder);
    });

    return result;
  }, [disciplineGroups, allNodes, detailedNodeRelations]);

  const disciplineCount = orderedFields.length || 5;
  const baseDistance = 140;
  const disciplinePositions = orderedFields.map((field, i) => {
    const angle = (Math.PI * 2 * i) / disciplineCount;
    return {
      field,
      angle,
      distance: baseDistance,
      x: centerX + Math.cos(angle) * baseDistance,
      y: centerY + Math.sin(angle) * baseDistance
    };
  });
 
  // helper: find discipline position by field
  const getDisciplinePos = (fieldName: string) => disciplinePositions.find(p => p.field === fieldName) || null;

  // For each discipline, compute an ordering of its child nodes such that connected nodes are adjacent when possible.
  const nodeOrderMap = useMemo(() => {
    const map: Record<string, string[]> = {};
    Object.keys(disciplineGroups).forEach(field => {
      const nodes = disciplineGroups[field as keyof typeof disciplineGroups] || [];
      const nodeIds = nodes.map(n => n.id);
      if (nodeIds.length <= 1) {
        map[field] = nodeIds;
        return;
      }

      // build weight map between nodes within this field (internal relations)
      const nw: Record<string, Record<string, number>> = {};
      nodeIds.forEach(id => (nw[id] = {}));
      detailedNodeRelations.forEach(rel => {
        if (nodeIds.includes(rel.source) && nodeIds.includes(rel.target)) {
          const inc = rel.type === 'cross_discipline' ? 2 : 1;
          nw[rel.source][rel.target] = (nw[rel.source][rel.target] || 0) + inc;
          nw[rel.target][rel.source] = (nw[rel.target][rel.source] || 0) + inc;
        }
      });

      // compute degree
      const degree: Record<string, number> = {};
      nodeIds.forEach(id => {
        degree[id] = Object.values(nw[id] || {}).reduce((a, b) => a + b, 0);
      });

      // greedy order: start from node with highest degree, then pick remaining node most connected to last
      const remaining = new Set(nodeIds);
      let startNode = nodeIds[0];
      let maxD = -1;
      nodeIds.forEach(id => { if ((degree[id] || 0) > maxD) { maxD = degree[id]; startNode = id; } });
      const order: string[] = [];
      order.push(startNode);
      remaining.delete(startNode);
      while (remaining.size > 0) {
        const last = order[order.length - 1];
        let best: string | null = null;
        let bestScore = -1;
        remaining.forEach(id => {
          const lastKey = last as string;
          const idKey = id as string;
          const conn = ((nw as any)[lastKey] && (nw as any)[lastKey][idKey]) || 0;
          if (conn > bestScore) { bestScore = conn; best = idKey; }
        });
        if (!best) {
          // fallback to highest degree
          remaining.forEach(id => {
            const idKey = id as string;
            if ((degree[idKey] || 0) > bestScore) { bestScore = degree[idKey] || 0; best = idKey; }
          });
        }
        if (!best) {
          const it = remaining.values();
          best = it.next().value;
        }
        order.push(best);
        remaining.delete(best);
      }
      map[field] = order;
    });
    return map;
  }, [disciplineGroups, detailedNodeRelations]);

  // Helper to darken a hex color by a given percent (0-1)
  const hexDarken = (hex: string, percent: number) => {
    try {
      const c = hex.replace('#', '');
      const num = parseInt(c, 16);
      let r = (num >> 16) & 0xff;
      let g = (num >> 8) & 0xff;
      let b = num & 0xff;
      r = Math.max(0, Math.floor(r * (1 - percent)));
      g = Math.max(0, Math.floor(g * (1 - percent)));
      b = Math.max(0, Math.floor(b * (1 - percent)));
      return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
    } catch (e) {
      return hex;
    }
  };

  const sanitizeId = (s: string) => {
    try {
      return encodeURIComponent(s).replace(/%/g, '_');
    } catch (e) {
      return String(s).replace(/[^\w\-]/g, '_');
    }
  };

  // Prepare gradient definitions for disciplines and detailed edges
  const gradientDefs = useMemo(() => {
    const defs: {
      id: string;
      from: string;
      to: string;
      opacityFrom?: number;
      opacityTo?: number;
    }[] = [];

    // root->discipline gradients (gray ribbon)
    Object.keys(disciplineGroups).forEach(field => {
      const id = `grad-root-${sanitizeId(field)}`;
      defs.push({
        id,
        from: '#111827',
        to: '#374151',
        opacityFrom: 0.85,
        opacityTo: 0.35
      });
    });

    // discipline gradients (discipline -> subnode) deeper Morandi
    Object.keys(disciplineGroups).forEach(field => {
      const base = FIELD_COLOR_MAP[field] || MORANDI_PALETTE[0];
      const from = hexDarken(base, 0.12);
      const to = hexDarken(base, 0.28);
      defs.push({ id: `grad-discipline-${sanitizeId(field)}`, from, to, opacityFrom: 0.95, opacityTo: 0.7 });
    });

    // edge gradients for each detailed relation (source->target)
    detailedNodeRelations.forEach((edge, idx) => {
      const sField = allNodes.find(n => n.id === edge.source)?.field;
      const tField = allNodes.find(n => n.id === edge.target)?.field;
      const sColor = FIELD_COLOR_MAP[sField || ''] || MORANDI_PALETTE[1];
      const tColor = FIELD_COLOR_MAP[tField || ''] || MORANDI_PALETTE[2];
      const from = hexDarken(sColor, 0.18);
      const to = hexDarken(tColor, 0.28);
      defs.push({ id: `grad-edge-${idx}`, from, to, opacityFrom: 0.85, opacityTo: 0.5 });
    });

    return defs;
  }, [disciplineGroups, detailedNodeRelations, allNodes]);

  // Relations between node and root (for hovered node)
  const relationsToRoot = useMemo(() => {
    const nodeId = hoveredBranch?.nodeId || hoveredNodeId;
    if (!nodeId || !coreNode) return [];
    return detailedNodeRelations.filter(rel =>
      (rel.source === nodeId && rel.target === coreNode.id) ||
      (rel.target === nodeId && rel.source === coreNode.id)
    );
  }, [hoveredBranch, hoveredNodeId, detailedNodeRelations, coreNode]);

  // 计算节点位置
  const getNodePosition = (nodeId: string, field?: string) => {
    // 检查是否是核心节点（根节点）
    const node = allNodes.find(n => n.id === nodeId);
    if (node && node.field === '核心') {
      return { x: centerX, y: centerY };
    }

    const disciplinePos = disciplinePositions.find(pos => pos.field === field);
    if (disciplinePos) {
      // 为每个学科的子节点计算位置
      const nodesInField = disciplineGroups[field as keyof typeof disciplineGroups] || [];
      const nodeOrderForField = (typeof nodeOrderMap !== 'undefined' ? (nodeOrderMap[field as keyof typeof nodeOrderMap] || []) : []) as string[];
      const effectiveOrder = nodeOrderForField.length ? nodeOrderForField : nodesInField.map(n => n.id);
      const nodeIndex = effectiveOrder.findIndex(id => id === nodeId);
      // use effectiveOrder for index calculations

      // 将子节点均匀分布在学科分支的“外侧”弧线上，且与学科主节点的连线长度保持相同
      const count = nodesInField.length || 1;
      // 最大弧度跨度约 120deg，避免过密
      const maxSpan = Math.PI * 2 / 3;
      // 基础跨度随节点数适度增大，受限于 maxSpan
      const span = count > 1 ? Math.min(maxSpan, 0.6 + 0.25 * (count - 1)) : 0.4;
      const angleOffset = count > 1 ? (nodeIndex - (count - 1) / 2) * (span / (count - 1)) : 0;
      const finalAngle = disciplinePos.angle + angleOffset;

      // 固定子节点与学科主节点之间的连线长度（使每条分支到其子节点的连线长度相同）
      const branchToChildDistance = 260; // 比学科distance更长，使子节点位于分支外侧

      return {
        x: disciplinePos.x + Math.cos(finalAngle) * branchToChildDistance,
        y: disciplinePos.y + Math.sin(finalAngle) * branchToChildDistance
      };
    }

    return { x: centerX, y: centerY };
  };

  // 主干总时长 - 保持较慢生长以体现学术沉淀感
  const trunkDuration = 6; 

  return (
    <div className="relative w-full h-screen bg-[#e5e2df] font-serif overflow-hidden">
      {/* selectedEdge panel removed */}

      {/* selectedDiscipline panel removed */}

      {/* 选中的节点概念详情 */}
      {/* selectedNode panel removed */}

      {/* 调试信息已移除 */}

      {/* 鼠标悬停波纹效果 */}
      {ripples.map((ripple) => (
        <div
          key={ripple.id}
          className="absolute pointer-events-none"
          style={{
            left: ripple.x - 120,
            top: ripple.y - 120,
            width: '240px',
            height: '240px',
            zIndex: 5, // 调高z-index确保不被遮挡
            background: `
              radial-gradient(ellipse at 30% 20%, rgba(107, 114, 128, 0.12) 0%, rgba(107, 114, 128, 0.06) 20%, transparent 50%),
              radial-gradient(ellipse at 70% 80%, rgba(75, 85, 99, 0.10) 0%, rgba(75, 85, 99, 0.04) 25%, transparent 55%),
              radial-gradient(ellipse at 50% 50%, rgba(55, 65, 81, 0.08) 0%, rgba(55, 65, 81, 0.03) 30%, transparent 60%),
              radial-gradient(ellipse at 20% 70%, rgba(31, 41, 55, 0.06) 0%, rgba(31, 41, 55, 0.02) 35%, transparent 65%)
            `,
            borderRadius: '50%',
            animation: 'wave-ripple 2s ease-out forwards',
            boxShadow: `
              inset 0 0 60px rgba(107, 114, 128, 0.1),
              inset -20px -20px 40px rgba(75, 85, 99, 0.08),
              0 0 100px rgba(55, 65, 81, 0.06),
              0 20px 40px rgba(31, 41, 55, 0.04)
            `,
          }}
        />
      ))}

      {/* 顶部固定导航 */}
      <div className="absolute top-0 left-0 w-full h-32 flex items-center px-10 z-50 pointer-events-none">
        <button 
          onClick={onBack}
          className="pointer-events-auto text-stone-500 hover:text-black flex items-center gap-3 transition-colors bg-white/40 backdrop-blur-md px-6 py-2.5 rounded-full border border-white/50 shadow-sm"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"/>
          </svg>
          <span className="text-[10px] tracking-[0.4em] uppercase font-bold">Return</span>
        </button>
      </div>

      {/* 网状布局视图 */}
      <div className="w-full h-full overflow-auto scroll-smooth custom-scrollbar">
        <div 
          ref={containerRef}
          style={{ width: `${canvasWidth}px`, height: `${canvasHeight}px` }}
          className="relative"
        >
          {/* SVG 线条层 */}
          <svg 
            width={canvasWidth}
            height={canvasHeight}
            className="absolute inset-0 z-0"
            style={{ display: 'block' }}
          >
            <defs>
              {gradientDefs.map(g => (
                <linearGradient key={g.id} id={g.id} x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor={g.from} stopOpacity={g.opacityFrom ?? 1} />
                  <stop offset="100%" stopColor={g.to} stopOpacity={g.opacityTo ?? 1} />
                </linearGradient>
              ))}
            </defs>
            {/* 核心节点到学科分支的连接线 */}
            {disciplinePositions.map((disciplinePos, index) => {
              const delay = index * 0.3;
              // try to use DOM centers for exact endpoint alignment
              let sx = centerX, sy = centerY, ex = disciplinePos.x, ey = disciplinePos.y;
              try {
                const coreEl = containerRef.current?.querySelector('[data-core="true"]') as HTMLElement | null;
                const discEl = containerRef.current?.querySelector(`[data-discipline="${disciplinePos.field}"]`) as HTMLElement | null;
                const c = getElementCenter(coreEl);
                const d = getElementCenter(discEl);
                if (c && d) {
                  sx = c.x; sy = c.y;
                  ex = d.x; ey = d.y;
                }
              } catch (e) {
                // fallback to math coords
              }

              return (
                <g key={`discipline-connection-${disciplinePos.field}`}>
            <path 
                    d={`M ${sx} ${sy} L ${ex} ${ey}`}
                    stroke={`url(#grad-root-${sanitizeId(disciplinePos.field)})`}
                    strokeWidth="6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
              fill="none"
              pathLength="100"
                    onMouseEnter={() => {
                      // find first relation between core and any node in this discipline
                      const nodeIds = (disciplineGroups[disciplinePos.field as keyof typeof disciplineGroups] || []).map(n => n.id);
                      const rel = detailedNodeRelations.find(r => (r.source === coreNode?.id && nodeIds.includes(r.target)) || (r.target === coreNode?.id && nodeIds.includes(r.source)));
                      // hover label disabled
                    }}
                    onMouseLeave={() => {}}
              style={{
                strokeDasharray: 100,
                strokeDashoffset: isLoaded ? 0 : 100,
                      transition: `stroke-dashoffset 2s ease-out ${delay}s`
                    }}
                  />
                  {/* 学科分支节点 (SVG marker removed; visual marker is rendered in HTML layer to ensure perfect center alignment) */}
                </g>
              );
            })}

            {/* 学科级别连线已移除：只显示根->学科、学科->子节点和子节点间的关系（详见下方） */}

            {/* 分支节点到子节点的连线 */}
            {disciplinePositions.map((disciplinePos) => {
              const disciplineNodes = disciplineGroups[disciplinePos.field as keyof typeof disciplineGroups] || [];

              return disciplineNodes.map((node, nodeIndex) => {
                const nodePos = getNodePosition(node.id, disciplinePos.field);
                const delay = 3 + nodeIndex * 0.1;

                // try DOM centers for precise endpoints
                let sx = disciplinePos.x, sy = disciplinePos.y, ex = nodePos.x, ey = nodePos.y;
                try {
                  const discEl = containerRef.current?.querySelector(`[data-discipline="${disciplinePos.field}"]`) as HTMLElement | null;
                  const childEl = containerRef.current?.querySelector(`[data-node-id="${node.id}"]`) as HTMLElement | null;
                  const d = getElementCenter(discEl);
                  const c = getElementCenter(childEl);
                  if (d && c) {
                    sx = d.x; sy = d.y;
                    ex = c.x; ey = c.y;
                  }
                } catch (e) { /* fallback */ }

                const branchColor = FIELD_COLOR_MAP[disciplinePos.field] || '#94a3b8';
              return (
                <g key={`branch-to-subnode-${disciplinePos.field}-${node.id}`}>
                  {
                    (() => {
                      const midX = (sx + ex) / 2;
                      const midY = (sy + ey) / 2;
                      return (
                  <path 
                      d={`M ${sx} ${sy} L ${ex} ${ey}`}
                      stroke={`url(#grad-discipline-${sanitizeId(disciplinePos.field)})`}
                           strokeWidth={hoveredBranch && hoveredBranch.nodeId === node.id && hoveredBranch.discipline === disciplinePos.field ? 7 : 4}
                          strokeLinecap="round"
                    fill="none"
                    pathLength="100"
                          onMouseEnter={() => setHoveredBranch({ discipline: disciplinePos.field, nodeId: node.id, x: midX, y: midY })}
                          onMouseLeave={() => setHoveredBranch(null)}
                          pointerEvents="stroke"
                      onClick={(ev) => {
                        ev.stopPropagation();
                        // find the relation between this node and the discipline representative node
                        const disciplineNodesLocal = disciplineGroups[disciplinePos.field as keyof typeof disciplineGroups] || [];
                        // heuristic: prefer a node whose label matches the discipline name or type === 'bridge'
                        const disciplineRep = disciplineNodesLocal.find(n => n.label === disciplinePos.field) ||
                          disciplineNodesLocal.find(n => (n as any).type === 'bridge') ||
                          disciplineNodesLocal[0];
                        let rel = null;
                        if (disciplineRep) {
                          rel = detailedNodeRelations.find(r =>
                            (r.source === node.id && r.target === disciplineRep.id) ||
                            (r.target === node.id && r.source === disciplineRep.id)
                          );
                        }
                        // fallback: still allow relation to core if discipline relation not found
                        if (!rel) {
                          rel = detailedNodeRelations.find(r =>
                            (r.source === node.id && r.target === coreNode?.id) ||
                            (r.target === node.id && r.source === coreNode?.id)
                          );
                        }
                        if (rel) {
                          // no inline popup — delegate to discipline selection or other UI
                        }
                      }}
                    style={{
                      cursor: 'pointer',
                      strokeDasharray: 100,
                      strokeDashoffset: isLoaded ? 0 : 100,
                      transition: `stroke-dashoffset 1s ease-out ${delay}s`,
                      opacity: 0.95
                    }}
                        />
                      );
                    })()
                  }
                </g>
              );
              });
            })}

            {/* 子节点之间的连线 */}
            {detailedNodeRelations.map((edge, index) => {
              const sourcePos = getNodePosition(edge.source,
                Object.keys(disciplineGroups).find(field =>
                  disciplineGroups[field as keyof typeof disciplineGroups]?.some(d => d.id === edge.source)
                ));
              const targetPos = getNodePosition(edge.target,
                Object.keys(disciplineGroups).find(field =>
                  disciplineGroups[field as keyof typeof disciplineGroups]?.some(d => d.id === edge.target)
                ));

              if (!sourcePos || !targetPos) return null;

              // try DOM centers for endpoints
              let sx = sourcePos.x, sy = sourcePos.y, ex = targetPos.x, ey = targetPos.y;
              try {
                const sEl = containerRef.current?.querySelector(`[data-node-id="${edge.source}"]`) as HTMLElement | null;
                const tEl = containerRef.current?.querySelector(`[data-node-id="${edge.target}"]`) as HTMLElement | null;
                const sC = getElementCenter(sEl);
                const tC = getElementCenter(tEl);
                if (sC && tC) {
                  sx = sC.x; sy = sC.y;
                  ex = tC.x; ey = tC.y;
                }
              } catch (e) { /* fallback */ }

              // only show subnode-subnode relations when hovering over one of the endpoints
              if (!hoveredNodeId || !(edge.source === hoveredNodeId || edge.target === hoveredNodeId)) return null;

              const connectsToRoot = edge.source === coreNode?.id || edge.target === coreNode?.id;
              const delay = 4 + index * 0.05;
              // color based on source field (fallback to neutral)
              const sourceField = allNodes.find(n => n.id === edge.source)?.field || allNodes.find(n => n.id === edge.target)?.field;
              const strokeColor = FIELD_COLOR_MAP[sourceField as string] || '#64748b';

              // compute control point slightly outside the midpoint direction:
              // place control point outward from midpoint toward canvas edge but only by a moderate offset
              const midX = (sx + ex) / 2;
              const midY = (sy + ey) / 2;
              const ang = Math.atan2(midY - centerY, midX - centerX);
              const segDist = Math.sqrt((ex - sx) * (ex - sx) + (ey - sy) * (ey - sy));
              const halfDiag = Math.sqrt((canvasWidth/2)**2 + (canvasHeight/2)**2);
              // offset proportional to segment length but clamped to avoid going too far
              const offset = Math.min( Math.max(60, segDist * 0.6), Math.max(120, halfDiag * 0.25) );
              const cx = midX + Math.cos(ang) * offset;
              const cy = midY + Math.sin(ang) * offset;

              // Quadratic Bezier: M sx,sy Q cx,cy ex,ey
              const d = `M ${sx} ${sy} Q ${cx} ${cy} ${ex} ${ey}`;

              // midpoint on quadratic at t=0.5 => (0.25*s + 0.5*c + 0.25*e)
              const indicatorX = (sx * 0.25) + (cx * 0.5) + (ex * 0.25);
              const indicatorY = (sy * 0.25) + (cy * 0.5) + (ey * 0.25);

              // determine if this edge touches a discipline representative node (label equals a discipline name)
              const sourceNode = allNodes.find(n => n.id === edge.source);
              const targetNode = allNodes.find(n => n.id === edge.target);
              const sourceIsDiscipline = !!(sourceNode && orderedFields.includes(sourceNode.label));
              const targetIsDiscipline = !!(targetNode && orderedFields.includes(targetNode.label));
              const isDisciplineEdge = sourceIsDiscipline || targetIsDiscipline;

              if (connectsToRoot && !isDisciplineEdge) {
                // Do not draw line to root; instead show small relation label near branch when hovering
                return (
                  <g key={`root-rel-${edge.source}-${edge.target}-${index}`}>
                    <rect x={indicatorX - 6} y={indicatorY - 16} width={12} height={12} rx={3} fill="transparent" />
                    <text
                      x={indicatorX + 12}
                      y={indicatorY}
                      fontSize={12}
                      fill="#374151"
                      style={{ cursor: 'pointer', userSelect: 'none' }}
                      onClick={(ev) => {
                        ev.stopPropagation();
                        // popups removed — no action
                      }}
                    >
                      {edge.relation}
                    </text>
                  </g>
                );
              }

              return (
                <g key={`subnode-edge-${edge.source}-${edge.target}-${index}`}>
                    <path
                      d={d}
                      stroke={`url(#grad-edge-${index})`}
                      strokeWidth="2"
                      strokeLinecap="round"
                      fill="none"
                      pathLength="100"
                      className="cursor-pointer"
                    style={{
                        strokeDasharray: 100,
                        strokeDashoffset: isLoaded ? 0 : 100,
                        transition: `stroke-dashoffset 0.6s ease-out ${delay}s, opacity 0.2s`,
                        opacity: 0.7
                      }}
                      onMouseEnter={() => {}}
                      onMouseLeave={() => {}}
                      onClick={() => {}}
                    />
                    {/* show edge relation label when hovering the endpoint node (render when edge is present because hoveredNodeId matches)
                        removed for discipline-edge to avoid showing text between discipline and subnode */}
                    {!isDisciplineEdge && (
                      <g pointerEvents="none">
                        <text
                          x={indicatorX}
                          y={indicatorY - 8}
                          fontSize={12}
                          textAnchor="middle"
                          style={{ fontStyle: 'italic', fill: hexDarken(strokeColor, 0.22), pointerEvents: 'none' }}
                          stroke="rgba(0,0,0,0.10)"
                          strokeWidth={0.8}
                        >
                          {edge.relation}
                        </text>
                        <text
                          x={indicatorX}
                          y={indicatorY - 8}
                          fontSize={12}
                          textAnchor="middle"
                          style={{ fontStyle: 'italic', fill: hexDarken(strokeColor, 0.22), pointerEvents: 'none' }}
                        >
                          {edge.relation}
                        </text>
                      </g>
                    )}
                </g>
              );
            })}

          </svg>

          {/* HTML 交互层 */}
          <div className="absolute inset-0 z-10">
            {/* 核心节点 */}
            <div 
              className="absolute pointer-events-auto"
              style={{ 
                left: centerX,
                top: centerY,
                transform: 'translate(-50%, -50%)'
              }}
            >
              <div
                className="flex flex-col items-center group cursor-pointer relative"
                onClick={() => {}}
              >
                <div data-core="true" className="w-24 h-24 flex items-center justify-center transition-all duration-500 group-hover:scale-125 mb-3 bg-[#e5e2df] rounded-full shadow-2xl" style={{ position: 'relative', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.25), 0 10px 10px -5px rgba(0, 0, 0, 0.04)' }}>
                  <span className="text-base font-black tracking-[0.15em] text-black transition-colors uppercase text-center px-2">
                {analysis.keyword}
                  </span>
            </div>
              </div>
            </div>
            {/* 根节点黑色小圆点（内嵌在白色DOM内，无需额外外部点） */}

            {/* 学科分支节点 */}
            {disciplinePositions.map((disciplinePos, index) => {
              const disciplineNodes = disciplineGroups[disciplinePos.field as keyof typeof disciplineGroups] || [];
              const delay = 1 + index * 0.3;

              return (
                <div key={`discipline-${disciplinePos.field}`}>
                  {/* 学科主节点 */}
                <div 
                  className="absolute pointer-events-auto"
                  style={{ 
                      left: disciplinePos.x,
                      top: disciplinePos.y,
                      transform: 'translate(-50%, -50%)',
                    opacity: isLoaded ? 1 : 0,
                      transition: `all 1s ease-out ${delay}s`
                  }}
                >
                  <div 
                    className="flex flex-col items-center group cursor-pointer relative"
                    >
                      <div
                        data-discipline={disciplinePos.field}
                        className="w-16 h-16 flex flex-col items-center justify-center transition-all duration-500 group-hover:scale-125 mb-2 bg-[#e5e2df] rounded-full shadow-lg"
                        style={{ position: 'relative', boxShadow: '0 8px 20px -5px rgba(0, 0, 0, 0.2), 0 8px 8px -5px rgba(0, 0, 0, 0.04)' }}
                      >
                        <DisciplineIcon name={FIELD_ICON_MAP[disciplinePos.field] || 'book'} fillColor={FIELD_COLOR_MAP[disciplinePos.field] || '#aebdc5'} className="w-8 h-8" />
                        <span className="text-[10px] mt-1 font-semibold text-center px-1">{disciplinePos.field}</span>
                    </div>
                    </div>
            </div>

                  {/* 学科子节点 */}
                  {disciplineNodes.map((node, nodeIndex) => {
                    const nodePos = getNodePosition(node.id, disciplinePos.field);
                    const nodeDelay = delay + 0.5 + nodeIndex * 0.2;


              return (
                <div 
                        key={node.id}
                  className="absolute pointer-events-auto"
                  style={{ 
                          left: nodePos.x,
                          top: nodePos.y,
                          transform: 'translate(-50%, -50%)',
                    opacity: isLoaded ? 1 : 0,
                          transition: `all 0.8s ease-out ${nodeDelay}s`
                  }}
                >
                  <div 
                    className="flex flex-col items-center group cursor-pointer relative"
                          onClick={() => setSelectedChild(node)}
                        >
                          <div
                            data-node-id={node.id}
                            onMouseEnter={() => setHoveredNodeId(node.id)}
                            onMouseLeave={() => setHoveredNodeId(null)}
                            className="w-12 h-12 flex items-center justify-center transition-all duration-500 group-hover:scale-125 mb-1 bg-[#e5e2df] rounded-full shadow-md"
                            style={{ position: 'relative', boxShadow: '0 6px 15px -5px rgba(0, 0, 0, 0.15), 0 6px 6px -5px rgba(0, 0, 0, 0.04)' }}
                          >
                            <div className="text-[11px] font-medium text-center px-2">{node.name}</div>
                    </div>
                        </div>
                  </div>
                    );
                  })}
            {/* 学科黑色小圆点已内嵌在学科 DOM 内，外部黑点已移除 */}
                </div>
              );
            })}
          </div>
          {/* Hovered branch relation label removed per user request */}

      {/* Child detail panel (left-side) */}
      {selectedChild && (() => {
        const node = selectedChild as GraphNode;
        const color = FIELD_COLOR_MAP[node.field] || MORANDI_PALETTE[0];
        const renderStars = (value?: number) => {
          const filled = Math.max(0, Math.min(5, Math.round((value || 0) * 5)));
          const stars = [];
          for (let i = 0; i < 5; i++) {
            const fill = i < filled ? color : '#e6e7e9';
            stars.push(
              <svg key={i} width="16" height="16" viewBox="0 0 24 24" className="inline-block mr-1" aria-hidden>
                <path fill={fill} d="M12 .587l3.668 7.431L24 9.748l-6 5.848L19.335 24 12 20.201 4.665 24 6 15.596 0 9.748l8.332-1.73z" />
              </svg>
            );
          }
          return <div className="flex items-center">{stars}</div>;
        };

        // aggregate evidence from edges connected to this node (prefer edges with evidence)
        const relatedEdges = detailedNodeRelations.filter(r => r.source === node.id || r.target === node.id);
        const evidenceText = relatedEdges.find(e => e.evidence)?.evidence || (relatedEdges[0] ? relatedEdges[0].relation : '');

        // fallback lookups for importance/confidence (some nodes may be missing fields)
        // try to find a matching node in allNodes or graphData.nodes by id or label variations
        let fallbackNode = allNodes.find(n => n.id === node.id);
        if (!fallbackNode && graphData?.nodes) {
          const norm = (s?: string) => (s || '').toString().trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_\-]/gi, '');
          const targetId = (node.id || '').toString();
          const targetLabel = (node.label || '').toString();
          fallbackNode = graphData.nodes.find((n: any) => {
            if (!n) return false;
            const nId = (n.id || '').toString();
            const nLabel = (n.label || '').toString();
            const nAliases = Array.isArray(n.aliases) ? n.aliases.map(String) : [];
            if (nId === targetId) return true;
            if (nLabel === targetId) return true;
            if (nId === targetLabel) return true;
            if (nLabel === targetLabel) return true;
            if (norm(nId) === norm(targetId)) return true;
            if (norm(nLabel) === norm(targetLabel)) return true;
            // aliases match
            if (nAliases.find((a: string) => a === targetLabel || norm(a) === norm(targetLabel))) return true;
            return false;
          }) as any;
        }
        const parseNum = (v: any): number | null => {
          if (typeof v === 'number') return v;
          if (typeof v === 'string') {
            const cleaned = v.replace('%', '').trim();
            const p = parseFloat(cleaned);
            if (!isNaN(p)) return p;
          }
          return null;
        };
        const normalize = (v: number | null): number | null => {
          if (v === null) return null;
          if (v > 1) {
            if (v <= 5) return Math.min(1, v / 5); // 1-5 scale -> 0-1
            // percent-like or large number
            return Math.min(1, v / 100);
          }
          return Math.max(0, Math.min(1, v));
        };
        const rawImportance = parseNum(node.importance ?? (fallbackNode && fallbackNode.importance));
        const rawConfidence = parseNum(node.confidence ?? (fallbackNode && fallbackNode.confidence));
        const importanceVal = normalize(rawImportance);
        const confidenceVal = normalize(rawConfidence);

        // attempt to estimate missing values from same-field nodes or related edges
        const fieldNodes = disciplineGroups[node.field as keyof typeof disciplineGroups] || [];
        const collectNums = (arr: any[], key: string) => {
          const vals: number[] = [];
          arr.forEach((n) => {
            const v = parseNum((n as any)[key]);
            if (v !== null) vals.push(normalize(v) as number);
          });
          return vals;
        };
        const importanceCandidates = collectNums(fieldNodes, 'importance');
        const confidenceCandidates = collectNums(fieldNodes, 'confidence');
        const avg = (a: number[]) => a.length ? (a.reduce((s, x) => s + x, 0) / a.length) : null;
        const avgImportance = avg(importanceCandidates);
        const avgConfidence = avg(confidenceCandidates);

        const estimatedImportance = importanceVal ?? avgImportance ?? 0.5;
        const estimatedConfidence = confidenceVal ?? (relatedEdges.length ? (relatedEdges.map(e => (e.confidence || 0)).reduce((s, x) => s + x, 0) / relatedEdges.length) : avgConfidence) ?? 0.5;
        // no debug logging

        return (
          <div className="fixed left-6 z-50 w-96 bg-white/98 backdrop-blur rounded-3xl shadow-2xl overflow-y-auto border border-white/20 p-6"
               style={{ top: '7.5rem', maxHeight: 'calc(100vh - 12rem)' }}>
            <div className="relative">
              <button onClick={() => setSelectedChild(null)} aria-label="Close" className="absolute right-4 -top-6 p-2 rounded-full hover:bg-stone-100 transition z-50">
                <svg className="w-4 h-4 text-stone-600" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>

              {/* Summary */}
              {(node as any).shortSummary && (
                <div className="mb-4">
                  <p className="font-serif italic text-stone-700 text-base leading-relaxed">“{(node as any).shortSummary}”</p>
                </div>
              )}

              {/* Key points */}
              {((node as any).keyPoints && (node as any).keyPoints.length > 0) && (
                <div className="mb-4">
                  <div className="text-xs mb-2 uppercase tracking-wider" style={{ color: hexDarken(color, 0.18) }}>关键要点</div>
                  <ul className="list-disc list-inside text-stone-700 text-sm space-y-1">
                    {(node as any).keyPoints.map((kp: string, i: number) => <li key={i}>{kp}</li>)}
                  </ul>
                </div>
              )}

              {/* Details */}
              {(node as any).details && (
                <div className="mb-4">
                  <div className="text-xs mb-2 uppercase tracking-wider" style={{ color: hexDarken(color, 0.18) }}>详细说明</div>
                  <div className="text-stone-700 text-sm leading-relaxed whitespace-pre-wrap">{(node as any).details}</div>
                </div>
              )}

              {/* Importance & Confidence */}
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <div className="text-xs mb-1 uppercase tracking-wider" style={{ color: hexDarken(color, 0.18) }}>重要性</div>
                  <div>{renderStars((importanceVal === null ? estimatedImportance : importanceVal) as number)}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs mb-1 uppercase tracking-wider" style={{ color: hexDarken(color, 0.18) }}>置信度</div>
                  {renderStars((confidenceVal === null ? estimatedConfidence : confidenceVal) as number)}
                </div>
              </div>

              {/* Evidence */}
              <div className="mb-4">
                <div className="text-xs mb-2 uppercase tracking-wider" style={{ color: hexDarken(color, 0.18) }}>证据</div>
                <div className="text-stone-700 text-sm leading-relaxed">{evidenceText || '—'}</div>
              </div>

              {/* Debug info removed */}

              {/* Reading hint */}
              {(node as any).readingHint && (
                <div className="mt-3">
                  <div className="text-xs mb-2 uppercase tracking-wider" style={{ color: hexDarken(color, 0.18) }}>阅读建议</div>
                  <div className="text-stone-600 text-sm italic">{(node as any).readingHint}</div>
                </div>
              )}
            </div>
          </div>
        );
      })()}
        </div>
      </div>

      {/* 滑动指引 */}
      <div className={`absolute bottom-8 right-12 flex items-center gap-4 text-stone-500 text-[10px] font-bold tracking-[0.4em] uppercase transition-opacity duration-1000 delay-[5s] ${isLoaded ? 'opacity-100' : 'opacity-0'}`}>
        <span>Explore knowledge paths</span>
        <div className="w-20 h-px bg-stone-400"></div>
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar { height: 5px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0,0,0,0.05); }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #bbb; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #999; }
        .font-serif { font-family: 'Noto Serif SC', serif; }

        @keyframes wave-ripple {
          0% {
            transform: scale(0) rotate(-10deg);
            opacity: 0;
            filter: blur(0px);
          }
          20% {
            transform: scale(0.3) rotate(5deg);
            opacity: 0.8;
            filter: blur(0.5px);
          }
          50% {
            transform: scale(0.6) rotate(-5deg);
            opacity: 0.6;
            filter: blur(1px);
          }
          80% {
            transform: scale(0.9) rotate(10deg);
            opacity: 0.2;
            filter: blur(2px);
          }
          100% {
            transform: scale(1) rotate(0deg);
            opacity: 0;
            filter: blur(3px);
          }
        }
      `}</style>
    </div>
  );
};

export default ContextScreen;
