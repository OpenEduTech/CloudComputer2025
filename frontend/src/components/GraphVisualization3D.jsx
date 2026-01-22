import React, { useEffect, useRef } from "react";
import "./GraphVisualization.css";

const COLOR_PALETTE = [
  "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
  "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B739", "#52B788",
];

const DOMAIN_COLORS = {
  Mathematics: "#E63946", Physics: "#457B9D", "Computer Science": "#52B788",
  Biology: "#F8B739", Sociology: "#BB8FCE", 数学: "#E63946",
  物理学: "#457B9D", 计算机科学: "#52B788", 生物学: "#F8B739",
  社会学: "#BB8FCE", Unknown: "#95a5a6",
};

const getDomainColor = (domain, allDomains) => {
  if (DOMAIN_COLORS[domain]) return DOMAIN_COLORS[domain];
  const domainList = Array.from(allDomains).sort();
  return COLOR_PALETTE[domainList.indexOf(domain) % COLOR_PALETTE.length];
};

function GraphVisualization3D({ data, onNodeClick, onNodeRightClick, loading }) {
  const fgContainerRef = useRef(null);
  const fgInstanceRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    const init3D = async () => {
      if (!data || !data.nodes || !fgContainerRef.current) return;

      try {
        const [{ default: ForceGraph3D }, THREE, d3] = await Promise.all([
          import("3d-force-graph"),
          import("three"),
          import("d3-force"),
        ]);

        if (!mounted) return;
        fgContainerRef.current.innerHTML = "";

        const allDomains = new Set(data.nodes.map((n) => n.domain));
        
        const Graph = ForceGraph3D()(fgContainerRef.current)
          .graphData({
            nodes: data.nodes.map((n) => ({
              id: n.id,
              name: n.label || n.id,
              domain: n.domain,
              type: n.type,
            })),
            links: data.edges.map((e) => ({
              source: e.source,
              target: e.target,
              strength: e.strength || 5,
            })),
          })
          .backgroundColor("#0f0f23")
          .width(fgContainerRef.current.clientWidth)
          .height(600)
          .nodeLabel(node => `
            <div style="
              background: rgba(0,0,0,0.9);
              color: white;
              padding: 12px 16px;
              border-radius: 8px;
              font-size: 14px;
              font-weight: bold;
              border: 2px solid ${getDomainColor(node.domain, allDomains)};
              box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            ">
              ${node.name}<br/>
              <span style="font-size: 11px; opacity: 0.8;">${node.domain}</span>
            </div>
          `)
          // 自定义节点：球体 + 文字
          .nodeThreeObject(node => {
            const isCenterNode = node.type === "center";
            const baseSize = isCenterNode ? 13 : 10;
            const color = getDomainColor(node.domain, allDomains);
            
            const group = new THREE.Group();
            
            // 球体
            const sphere = new THREE.Mesh(
              new THREE.SphereGeometry(baseSize, 32, 32),
              new THREE.MeshPhongMaterial({
                color: color,
                transparent: true,
                opacity: 0.9,
                shininess: 100,
                emissive: color,
                emissiveIntensity: 0.2,
              })
            );
            group.add(sphere);
            
            // 创建文字精灵
            const canvas = document.createElement('canvas');
            const size = 512;
            canvas.width = size;
            canvas.height = size;
            const ctx = canvas.getContext('2d');
            
            ctx.clearRect(0, 0, size, size);
            
            // 绘制背景
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.beginPath();
            ctx.roundRect(60, size/2 - 50, size - 120, 100, 15);
            ctx.fill();
            
            // 绘制文字
            ctx.fillStyle = 'white';
            ctx.font = 'bold 70px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.shadowColor = 'rgba(0,0,0,0.8)';
            ctx.shadowBlur = 8;
            
            const text = String(node.name).substring(0, 6);
            ctx.fillText(text, size / 2, size / 2);
            
            const texture = new THREE.CanvasTexture(canvas);
            const sprite = new THREE.Sprite(
              new THREE.SpriteMaterial({
                map: texture,
                transparent: true,
              })
            );
            
            const scale = isCenterNode ? 28 : 22;
            sprite.scale.set(scale, scale, 1);
            sprite.position.set(0, baseSize + 8, 0);
            group.add(sprite);
            
            return group;
          })
          // 连接线样式 - 减慢粒子速度
          .linkWidth(link => Math.max(0.8, link.strength / 4))
          .linkColor(() => 'rgba(100, 150, 255, 0.5)')
          .linkOpacity(0.6)
          .linkDirectionalParticles(2)  // 减少粒子数量
          .linkDirectionalParticleWidth(1.5)
          .linkDirectionalParticleSpeed(0.003)  // 减慢速度（原来 0.01）
          .linkDirectionalParticleColor(() => 'rgba(100, 200, 255, 0.8)')
          // 交互
          .enableNodeDrag(true)
          .enableNavigationControls(true)
          .showNavInfo(false)
          .onNodeClick((node) => {
            if (!loading && onNodeClick) onNodeClick(node.id);
          })
          .onNodeRightClick((node) => {
            if (!loading && onNodeRightClick) onNodeRightClick(node.id);
          })
          .onNodeHover(node => {
            fgContainerRef.current.style.cursor = node ? 'pointer' : 'default';
          });

        // 优化力导向布局
        Graph
          .d3Force('charge', d3.forceManyBody()
            .strength(-180)
            .distanceMax(300))
          .d3Force('link', d3.forceLink()
            .distance(link => {
              const baseDistance = 90;
              const strengthFactor = (10 - link.strength) * 6;
              return baseDistance + strengthFactor;
            })
            .strength(0.8))
          .d3Force('center', d3.forceCenter().strength(0.1))
          .d3Force('collision', d3.forceCollide()
            .radius(node => node.type === "center" ? 20 : 15)
            .strength(0.8))
          .d3AlphaDecay(0.01)
          .d3VelocityDecay(0.3)
          .warmupTicks(50)
          .cooldownTicks(100);

        // 场景设置
        const scene = Graph.scene();
        scene.children = scene.children.filter(child => !(child instanceof THREE.Light));
        
        // 环境光
        const ambientLight = new THREE.AmbientLight(0x404060, 1.2);
        scene.add(ambientLight);
        
        // 主光源
        const mainLight = new THREE.DirectionalLight(0xffffff, 1.5);
        mainLight.position.set(200, 200, 200);
        scene.add(mainLight);
        
        // 补光
        const fillLight1 = new THREE.DirectionalLight(0x6495ED, 0.8);
        fillLight1.position.set(-200, 100, -100);
        scene.add(fillLight1);
        
        const fillLight2 = new THREE.DirectionalLight(0xFF6B6B, 0.6);
        fillLight2.position.set(100, -100, 200);
        scene.add(fillLight2);
        
        // 动态点光源
        const pointLights = [];
        const colors = [0xFF6B6B, 0x4ECDC4, 0xF8B739, 0xBB8FCE];
        for (let i = 0; i < 4; i++) {
          const light = new THREE.PointLight(colors[i], 0.6, 400);
          const angle = (i / 4) * Math.PI * 2;
          light.position.set(
            Math.cos(angle) * 250,
            Math.sin(angle * 2) * 100,
            Math.sin(angle) * 250
          );
          scene.add(light);
          pointLights.push(light);
        }
        
        // 粒子星空背景
        const createStarField = () => {
          const geometry = new THREE.BufferGeometry();
          const vertices = [];
          const colors = [];
          
          for (let i = 0; i < 3000; i++) {
            const x = (Math.random() - 0.5) * 2000;
            const y = (Math.random() - 0.5) * 2000;
            const z = (Math.random() - 0.5) * 2000;
            vertices.push(x, y, z);
            
            const color = new THREE.Color();
            color.setHSL(Math.random() * 0.3 + 0.5, 0.5, 0.8);
            colors.push(color.r, color.g, color.b);
          }
          
          geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
          geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
          
          const material = new THREE.PointsMaterial({
            size: 2,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
          });
          
          return new THREE.Points(geometry, material);
        };
        
        const stars = createStarField();
        scene.add(stars);

        // 相机设置
        setTimeout(() => {
          try {
            const camera = Graph.camera();
            const controls = Graph.controls();
            
            if (camera) {
              const nodeCount = data.nodes.length;
              const distance = Math.max(350, Math.min(650, 350 + nodeCount * 5));
              
              // 设置相机位置：稍微偏上的角度
              camera.position.set(
                distance * 0.5,
                distance * 0.5,
                distance * 0.7
              );
              camera.lookAt(0, 0, 0);
              camera.updateProjectionMatrix();
            }
            
            if (controls) {
              controls.target.set(0, 0, 0);
              controls.enableDamping = true;
              controls.dampingFactor = 0.05;
              controls.rotateSpeed = 0.5;
              controls.zoomSpeed = 1.0;
              controls.minDistance = 150;
              controls.maxDistance = 1000;
              controls.update();
            }
          } catch (e) {
            console.warn("相机设置失败:", e);
          }
        }, 100);

        // 动画循环
        let animationId;
        let time = 0;
        const animate = () => {
          animationId = requestAnimationFrame(animate);
          time += 0.0008;  // 减慢动画速度
          
          // 点光源旋转
          pointLights.forEach((light, i) => {
            const angle = time + (i / pointLights.length) * Math.PI * 2;
            light.position.x = Math.cos(angle) * 250;
            light.position.z = Math.sin(angle) * 250;
            light.position.y = Math.sin(angle * 2) * 100;
          });
          
          // 星空缓慢旋转
          if (stars) {
            stars.rotation.y += 0.0001;
            stars.rotation.x += 0.00005;
          }
        };
        animate();

        fgInstanceRef.current = { graph: Graph, animationId };
      } catch (err) {
        console.error("加载 3D 图谱失败:", err);
      }
    };

    const destroy3D = () => {
      try {
        if (fgInstanceRef.current) {
          if (fgInstanceRef.current.animationId) {
            cancelAnimationFrame(fgInstanceRef.current.animationId);
          }
          if (fgContainerRef.current) {
            fgContainerRef.current.innerHTML = "";
          }
          if (fgInstanceRef.current.graph?.pauseAnimation) {
            fgInstanceRef.current.graph.pauseAnimation();
          }
          fgInstanceRef.current = null;
        }
      } catch (e) {}
    };

    init3D();
    return () => {
      mounted = false;
      destroy3D();
    };
  }, [data, loading, onNodeClick, onNodeRightClick]);

  return (
    <div className="graph-3d-wrapper">
      <div
        className="graph-3d-container"
        ref={fgContainerRef}
        style={{ height: "600px", width: "100%", position: "relative" }}
      />
      {loading && (
        <div className="graph-loading-overlay">
          <div className="graph-spinner"></div>
          <p>正在扩展节点...</p>
        </div>
      )}
    </div>
  );
}

export default GraphVisualization3D;
