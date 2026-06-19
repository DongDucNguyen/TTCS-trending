import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { Activity, Network, FileText, TrendingUp, ChevronDown, ChevronUp, ZoomIn, ZoomOut, Maximize, Minimize, Crosshair } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import './index.css';

// Mock Data từ Backend
const mockData = {
  leaderboard: [
    { 
      topic: "Large Language Models", paper_count: 4, growth_rate: 10.35,
      papers: ["A new LLM outperforms GPT-4", "Autonomous Multi-Agent System", "LLM Hallucinations solution", "Prompt Engineering Techniques"]
    },
    { 
      topic: "Reinforcement Learning", paper_count: 3, growth_rate: 10.31,
      papers: ["RL in Robotics", "PPO Agent continuous control", "Q-Learning analysis"]
    },
    { 
      topic: "Agentic AI", paper_count: 3, growth_rate: 11.1,
      papers: ["Agentic Workflow with LLMs", "Autonomous Agents for Web", "Language Agents survey"]
    },
    { 
      topic: "Computer Vision", paper_count: 1, growth_rate: 11.73,
      papers: ["Vision Transformer architecture"]
    }
  ],
  graph: {
    // Dữ liệu mô phỏng từ khóa từ c-TF-IDF
    nodes: [
      { id: "LLM", name: "LLM", size: 32, group: 1 },
      { id: "Reasoning", name: "Reasoning", size: 24, group: 1 },
      { id: "Transformers", name: "Transformers", size: 18, group: 1 },
      { id: "Agentic", name: "Agentic", size: 28, group: 2 },
      { id: "Autonomy", name: "Autonomy", size: 20, group: 2 },
      { id: "RLHF", name: "RLHF", size: 30, group: 3 },
      { id: "PPO", name: "PPO", size: 22, group: 3 },
      { id: "Vision", name: "Vision", size: 20, group: 4 },
      { id: "Segmentation", name: "Segmentation", size: 14, group: 4 },
    ],
    edges: [
      { source: "LLM", target: "Reasoning", weight: 0.8 },
      { source: "LLM", target: "Transformers", weight: 0.6 },
      { source: "LLM", target: "Agentic", weight: 0.4 },
      { source: "Agentic", target: "Autonomy", weight: 0.7 },
      { source: "RLHF", target: "PPO", weight: 0.9 },
      { source: "LLM", target: "RLHF", weight: 0.5 },
      { source: "Vision", target: "Segmentation", weight: 0.8 },
      { source: "Transformers", target: "Vision", weight: 0.3 }
    ]
  }
};

function App() {
  const graphRef = useRef(null);
  const [expandedTopic, setExpandedTopic] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [selectedKeyword, setSelectedKeyword] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 700, height: 500 });

  // Precompute cross-links for hover effect
  const forceGraphData = useMemo(() => {
    const data = {
      nodes: mockData.graph.nodes.map(n => ({ ...n })),
      links: mockData.graph.edges.map(e => ({ ...e }))
    };
    data.links.forEach(link => {
      const a = data.nodes.find(n => n.id === link.source);
      const b = data.nodes.find(n => n.id === link.target);
      if (a && b) {
        !a.neighbors && (a.neighbors = new Set());
        !b.neighbors && (b.neighbors = new Set());
        a.neighbors.add(b.id);
        b.neighbors.add(a.id);
      }
    });
    return data;
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (let entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (graphRef.current) {
      setTimeout(() => {
        graphRef.current.d3Force('charge').strength(-400); // Đẩy các node xa nhau ra
        graphRef.current.zoomToFit(400, 50);
      }, 500);
    }
  }, []);

  const getColorByGroup = (group) => {
    const colors = {
      1: '#10b981', // Emerald
      2: '#06b6d4', // Cyan
      3: '#f59e0b', // Amber
      4: '#ec4899', // Pink
    };
    return colors[group] || '#e6edf3';
  };

  const handleZoomIn = () => graphRef.current.zoom(graphRef.current.zoom() * 1.5, 400);
  const handleZoomOut = () => graphRef.current.zoom(graphRef.current.zoom() / 1.5, 400);
  const handleFit = () => graphRef.current.zoomToFit(400, 50);

  if (selectedKeyword) {
    return (
      <div className="app-container">
        <header className="header" style={{ marginBottom: '3rem', textAlign: 'left', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <button 
            onClick={() => setSelectedKeyword(null)}
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-glass)', color: '#e6edf3', padding: '10px 16px', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s ease', fontWeight: 500 }}
            onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
            onMouseOut={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
          >
            ← Back to Dashboard
          </button>
          <div>
            <h1 className="title" style={{ fontSize: '2rem', margin: 0, background: 'none', WebkitTextFillColor: 'initial', color: getColorByGroup(selectedKeyword.group) }}>
              {selectedKeyword.name}
            </h1>
            <p className="subtitle" style={{ fontSize: '1rem', margin: '4px 0 0 0' }}>Showing {Math.max(4, Math.floor(selectedKeyword.size / 2))} related papers from recent publications</p>
          </div>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '1.5rem' }}>
          {Array.from({ length: Math.max(4, Math.floor(selectedKeyword.size / 5)) }).map((_, i) => (
            <div key={i} className="glass-card" style={{ padding: '1.5rem', cursor: 'pointer', display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                <span style={{ fontSize: '0.8rem', color: getColorByGroup(selectedKeyword.group), fontWeight: 600, letterSpacing: '0.5px', textTransform: 'uppercase' }}>RESEARCH PAPER</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>June {20 - i}, 2026</span>
              </div>
              <h3 style={{ fontSize: '1.2rem', marginBottom: '12px', lineHeight: 1.4, color: '#ffffff' }}>
                {i === 0 ? `A novel approach using ${selectedKeyword.name}` : 
                 i === 1 ? `Analyzing the impact of ${selectedKeyword.name} in modern AI architectures` : 
                 i === 2 ? `Optimizing performance with ${selectedKeyword.name} integration` : 
                 `Future directions and challenges for ${selectedKeyword.name} research`}
              </h3>
              <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '20px', flex: 1 }}>
                This paper explores the intricate details of {selectedKeyword.name.toLowerCase()} and its applications in various domains. The authors propose a new methodology that significantly improves upon existing baselines by 15% on standard benchmarks...
              </p>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ background: 'rgba(255,255,255,0.05)', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem', color: '#e6edf3' }}>Artificial Intelligence</span>
                <span style={{ background: `rgba(${parseInt(getColorByGroup(selectedKeyword.group).slice(1,3), 16)}, ${parseInt(getColorByGroup(selectedKeyword.group).slice(3,5), 16)}, ${parseInt(getColorByGroup(selectedKeyword.group).slice(5,7), 16)}, 0.15)`, padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem', color: getColorByGroup(selectedKeyword.group) }}>{selectedKeyword.name}</span>
                {i % 2 === 0 && <span style={{ background: 'rgba(255,255,255,0.05)', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem', color: '#e6edf3' }}>Deep Learning</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="app-container" style={isFullscreen ? { padding: 0 } : {}}>
      <header className="header">
        <h1 className="title">AI Research News</h1>
        <p className="subtitle">Emergent Topics & Knowledge Graph Discovery</p>
      </header>

      <div className="dashboard-grid">
        {/* Cột 1: Leaderboard */}
        <div className="glass-card">
          <div className="card-header">
            <TrendingUp size={24} color="#10b981" />
            <h2 className="card-title">Trending Topics (Zero-Shot)</h2>
          </div>
          
          <div className="leaderboard-list">
            {mockData.leaderboard.map((item, idx) => (
              <div 
                key={idx} 
                className={`leaderboard-item ${expandedTopic === item.topic ? 'expanded' : ''}`}
                onClick={() => setExpandedTopic(expandedTopic === item.topic ? null : item.topic)}
                style={{ cursor: 'pointer' }}
              >
                <div className="topic-header" style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                  <div className="topic-info">
                    <h3>{item.topic}</h3>
                    <div className="topic-stats">
                      <span className="flex items-center gap-1">
                        <FileText size={14} /> {item.paper_count} papers
                      </span>
                      <span className="growth-positive flex items-center gap-1">
                        <Activity size={14} /> +{item.growth_rate}%
                      </span>
                    </div>
                  </div>
                  <div className="expand-icon" style={{ color: 'var(--text-secondary)' }}>
                    {expandedTopic === item.topic ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </div>
                </div>
                
                {expandedTopic === item.topic && (
                  <div className="paper-list" style={{ marginTop: '1rem', borderTop: '1px solid var(--border-glass)', paddingTop: '1rem' }}>
                    {item.papers.map((paper, pIdx) => (
                      <div key={pIdx} className="paper-item" style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '0.5rem', padding: '0.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '6px' }}>
                        • {paper}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Cột 2: Semantic Word Graph */}
        <div className="glass-card" style={isFullscreen ? { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 100, borderRadius: 0, border: 'none', padding: 0 } : {}}>
          {!isFullscreen && (
            <div className="card-header">
              <Network size={24} color="#06b6d4" />
              <h2 className="card-title">Emergent Keywords Graph</h2>
            </div>
          )}
          
          <div style={{ display: 'flex', height: isFullscreen ? '100vh' : '500px', width: '100%', overflow: 'hidden' }}>
            
            <div className="graph-container" ref={containerRef} style={{ flex: 1, position: 'relative', height: '100%' }}>
              
              {/* Control Toolbar */}
              <div style={{ position: 'absolute', top: 16, left: 16, zIndex: 10, display: 'flex', gap: '8px', background: 'rgba(0,0,0,0.5)', padding: '8px', borderRadius: '8px', backdropFilter: 'blur(4px)' }}>
                <button onClick={handleZoomIn} style={{ background: 'transparent', border: 'none', color: '#e6edf3', cursor: 'pointer' }} title="Zoom In"><ZoomIn size={20} /></button>
                <button onClick={handleZoomOut} style={{ background: 'transparent', border: 'none', color: '#e6edf3', cursor: 'pointer' }} title="Zoom Out"><ZoomOut size={20} /></button>
                <button onClick={handleFit} style={{ background: 'transparent', border: 'none', color: '#e6edf3', cursor: 'pointer' }} title="Fit Screen"><Crosshair size={20} /></button>
                <button onClick={() => setIsFullscreen(!isFullscreen)} style={{ background: 'transparent', border: 'none', color: '#e6edf3', cursor: 'pointer' }} title="Toggle Fullscreen">
                  {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
                </button>
              </div>
              {mockData.graph.nodes.length > 0 ? (
                <ForceGraph2D
                  ref={graphRef}
                  graphData={forceGraphData}
                  nodeRelSize={1}
                  onNodeHover={node => setHoverNode(node)}
                  onNodeClick={node => setSelectedKeyword(node)}
                  linkColor={link => {
                    if (!hoverNode) return 'rgba(255,255,255,0.1)';
                    const isLinkHovered = link.source.id === hoverNode.id || link.target.id === hoverNode.id;
                    return isLinkHovered ? getColorByGroup(hoverNode.group) : 'rgba(255,255,255,0.02)';
                  }}
                  linkWidth={link => {
                    if (!hoverNode) return link.weight * 2;
                    const isLinkHovered = link.source.id === hoverNode.id || link.target.id === hoverNode.id;
                    return isLinkHovered ? link.weight * 4 : link.weight * 1;
                  }}
                  width={dimensions.width}
                  height={dimensions.height}
                  backgroundColor="#161b22"
                  nodePointerAreaPaint={(node, color, ctx, globalScale) => {
                    const label = node.name;
                    const isHovered = hoverNode && hoverNode.id === node.id;
                    const baseSize = isHovered ? node.size * 2.0 : node.size * 1.5;
                    const fontSize = baseSize / globalScale;
                    ctx.font = `600 ${fontSize}px Inter, Sans-Serif`;
                    const textWidth = ctx.measureText(label).width;
                    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.5);
                    
                    ctx.fillStyle = color;
                    ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
                  }}
                  nodeCanvasObject={(node, ctx, globalScale) => {
                    const label = node.name;
                    const isHovered = hoverNode && hoverNode.id === node.id;
                    const isNeighbor = hoverNode && hoverNode.neighbors && hoverNode.neighbors.has(node.id);
                    const isFaded = hoverNode && !isHovered && !isNeighbor;
                    
                    const baseSize = isHovered ? node.size * 2.0 : node.size * 1.5;
                    const fontSize = baseSize / globalScale;
                    ctx.font = `600 ${fontSize}px Inter, Sans-Serif`;
                    
                    ctx.globalAlpha = isFaded ? 0.2 : 1.0;
                    
                    if (!isFaded) {
                      ctx.shadowColor = getColorByGroup(node.group);
                      ctx.shadowBlur = isHovered ? 15 : 8;
                    }
                    
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = isHovered ? '#ffffff' : getColorByGroup(node.group);
                    ctx.fillText(label, node.x, node.y);
                    
                    ctx.shadowBlur = 0;
                    ctx.globalAlpha = 1.0;
                  }}
                />
              ) : (
                <div className="empty-state">
                  <p>No clusters detected.</p>
                </div>
              )}
            </div>

            {/* Keyword Details Side Panel */}
            <div style={{
              width: hoverNode ? '320px' : '0px',
              opacity: hoverNode ? 1 : 0,
              background: 'rgba(13, 17, 23, 0.4)',
              borderLeft: hoverNode ? '1px solid rgba(255,255,255,0.05)' : 'none',
              padding: hoverNode ? '20px' : '0px',
              color: '#e6edf3',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              overflowY: 'auto',
              overflowX: 'hidden'
            }}>
              {hoverNode && (
                <div style={{ width: '280px' }}> {/* Inner container to prevent content wrapping during transition */}
                  <h3 style={{ margin: '0 0 4px 0', fontSize: '1.4rem', color: getColorByGroup(hoverNode.group), whiteSpace: 'nowrap' }}>
                    {hoverNode.name}
                  </h3>
                  <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Activity size={14} /> Tần suất: {hoverNode.size}
                  </div>
                  
                  <div style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', whiteSpace: 'nowrap' }}>
                    Bài báo liên quan ({Math.floor(hoverNode.size / 5)} bài)
                  </div>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', fontSize: '0.85rem', lineHeight: '1.4' }}>
                      <div style={{ color: getColorByGroup(hoverNode.group), fontWeight: 600, marginBottom: '4px' }}>Mới nhất</div>
                      Khám phá ứng dụng thực tiễn của <strong>{hoverNode.name}</strong> trong các bài toán phức tạp.
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', fontSize: '0.85rem', lineHeight: '1.4' }}>
                      <div style={{ color: getColorByGroup(hoverNode.group), fontWeight: 600, marginBottom: '4px' }}>Top Đánh Giá</div>
                      Tối ưu hóa kiến trúc AI sử dụng <strong>{hoverNode.name}</strong> để đạt SOTA benchmark.
                    </div>
                    {hoverNode.size > 20 && (
                      <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', fontSize: '0.85rem', lineHeight: '1.4' }}>
                        <div style={{ color: getColorByGroup(hoverNode.group), fontWeight: 600, marginBottom: '4px' }}>Đang Trending</div>
                        Tại sao <strong>{hoverNode.name}</strong> đang trở thành xu hướng thay thế cấu trúc truyền thống?
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
