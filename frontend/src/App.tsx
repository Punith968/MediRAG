import React, { useState, useRef, useCallback, useEffect } from 'react';
import axios from 'axios';
import * as d3 from 'd3';
import {
  Upload, Loader2, Send, X, FileText, Image, Music,
  CheckCircle2, AlertCircle, Activity, Brain, Zap,
  ChevronDown, ChevronUp, Cpu, Database
} from 'lucide-react';

const API = import.meta.env.VITE_API_URL || "/api";

interface FileStatus {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  message?: string;
}
interface QueryImageAttachment { file: File; preview: string; }

interface GraphNode {
  id: string;
  label: string;
}

interface GraphEdge {
  source: string;
  target: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ── helpers ─────────────────────────────────────────────────────────────────
const SUPPORTED_EXT = ['pdf', 'png', 'jpg', 'jpeg', 'mp3', 'wav', 'm4a'];

function fmtSize(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

function fileIcon(name: string) {
  const e = name.split('.').pop()?.toLowerCase() ?? '';
  if (e === 'pdf') return <FileText className="w-4 h-4" />;
  if (['png','jpg','jpeg'].includes(e)) return <Image className="w-4 h-4" />;
  if (['mp3','wav','m4a'].includes(e)) return <Music className="w-4 h-4" />;
  return <FileText className="w-4 h-4" />;
}
function fileLabel(name: string) {
  const e = name.split('.').pop()?.toLowerCase() ?? '';
  if (e === 'pdf') return 'PDF';
  if (['png','jpg','jpeg'].includes(e)) return 'Image';
  if (['mp3','wav','m4a'].includes(e)) return 'Audio';
  return 'File';
}

const DISCLAIMER_PREFIX = "This is an AI-generated analysis and is not a substitute for professional medical advice, diagnosis, or treatment. Please consult a qualified clinician.";

function parseResponse(text: string) {
  if (!text) return { mainText: '', disclaimer: '' };
  const idx = text.indexOf(DISCLAIMER_PREFIX);
  if (idx !== -1) {
    return {
      mainText: text.substring(0, idx).trim(),
      disclaimer: text.substring(idx).trim()
    };
  }
  return { mainText: text, disclaimer: '' };
}

// ── sub-components ───────────────────────────────────────────────────────────


function ContextPanel({ title, icon, content, accent }: {
  title: string; icon: React.ReactNode; content: string; accent: string;
}) {
  const [open, setOpen] = useState(false);
  if (!content) return null;
  return (
    <div className={`rounded-xl border ${accent} glass overflow-hidden`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold hover:bg-white/5 transition-colors"
      >
        <span className="flex items-center gap-2">{icon}{title}</span>
        {open ? <ChevronUp className="w-4 h-4 opacity-50" /> : <ChevronDown className="w-4 h-4 opacity-50" />}
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-white/5">
          <pre className="mt-3 text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-mono max-h-64 overflow-y-auto">
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}

function KnowledgeGraph() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/graph`)
      .then(res => {
        setGraphData(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load graph:', err);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!graphData || !svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = 400;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const conditionIds = new Set(graphData.edges.map(e => e.target));
    const isSymptom = (id: string) => !conditionIds.has(id);

    interface SimNode extends d3.SimulationNodeDatum {
      id: string;
      label: string;
    }

    const nodes: SimNode[] = graphData.nodes.map(d => ({ ...d }));
    const nodeById = new Map(nodes.map(n => [n.id, n]));

    const links = graphData.edges
      .filter(e => nodeById.has(e.source) && nodeById.has(e.target))
      .map(d => ({ source: d.source, target: d.target }));

    const simulation = d3.forceSimulation<SimNode>(nodes)
      .force('link', d3.forceLink<SimNode, d3.SimulationLinkDatum<SimNode>>(links).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(20));

    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#9ca3af')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 1.5);

    const node = svg.append('g')
      .selectAll<SVGGElement, SimNode>('g')
      .data(nodes)
      .join('g')
      .call(d3.drag<SVGGElement, SimNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }));

    node.append('circle')
      .attr('r', d => isSymptom(d.id) ? 10 : 7)
      .attr('fill', d => isSymptom(d.id) ? '#60a5fa' : '#34d399');

    node.append('text')
      .attr('x', 14)
      .attr('y', 4)
      .attr('fill', '#e2e8f0')
      .attr('font-size', '11px')
      .attr('font-family', 'system-ui, sans-serif')
      .text(d => d.label);

    simulation.on('tick', () => {
      link.each(function(d) {
        const linkEl = d3.select(this);
        const s = d.source as unknown as { x?: number; y?: number };
        const t = d.target as unknown as { x?: number; y?: number };
        linkEl.attr('x1', s.x || 0).attr('y1', s.y || 0).attr('x2', t.x || 0).attr('y2', t.y || 0);
      });

      node.attr('transform', d => `translate(${d.x || 0},${d.y || 0})`);
    });
  }, [graphData]);

  if (loading) {
    return (
      <div className="glass rounded-xl p-6 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-sky-400 mr-2" />
        <span className="text-slate-400">Loading knowledge graph...</span>
      </div>
    );
  }

  return (
    <section className="glass rounded-xl p-6">
      <h2 className="text-lg font-bold flex items-center gap-2 text-violet-300 mb-4">
        <Activity className="w-5 h-5" /> Knowledge Graph
      </h2>
      <div ref={containerRef} className="w-full">
        <svg ref={svgRef} width="100%" height="400" />
      </div>
      <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-sky-400" /> Symptom
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-emerald-400" /> Condition
        </span>
      </div>
    </section>
  );
}

// ── main component ───────────────────────────────────────────────────────────
export default function App() {
  const [files, setFiles]               = useState<FileStatus[]>([]);
  const [uploadSummary, setUploadSummary] = useState('');
  const [query, setQuery]               = useState('');
  const [queryImage, setQueryImage]     = useState<QueryImageAttachment | null>(null);
  const [response, setResponse]         = useState<any>(null);
  const [uploading, setUploading]       = useState(false);
  const [querying, setQuerying]         = useState(false);
  const [dragActive, setDragActive]     = useState(false);
  const fileInputRef      = useRef<HTMLInputElement>(null);
  const queryImageRef     = useRef<HTMLInputElement>(null);

  // ── file management ────────────────────────────────────────────────────────
  const addFiles = useCallback((incoming: FileList | File[]) => {
    const arr = Array.from(incoming);
    const valid = arr.filter(f => SUPPORTED_EXT.includes(f.name.split('.').pop()?.toLowerCase() ?? ''));
    const skipped = arr.length - valid.length;
    if (skipped > 0) setUploadSummary(`${skipped} file(s) skipped — unsupported format.`);
    setFiles(prev => [...prev, ...valid.map(f => ({ file: f, status: 'pending' as const }))]);
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setDragActive(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  };

  const removeFile = (i: number) => setFiles(prev => prev.filter((_, idx) => idx !== i));
  const clearAll   = () => { setFiles([]); setUploadSummary(''); };

  const handleQueryImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (!f) return;
    if (queryImage?.preview) URL.revokeObjectURL(queryImage.preview);
    setQueryImage({ file: f, preview: URL.createObjectURL(f) });
    e.target.value = '';
  };
  const removeQueryImage = () => {
    if (queryImage?.preview) URL.revokeObjectURL(queryImage.preview);
    setQueryImage(null);
  };

  // ── upload ─────────────────────────────────────────────────────────────────
  const handleUpload = async () => {
    const pending = files.filter(f => f.status === 'pending' || f.status === 'error');
    if (!pending.length) return;
    setUploading(true); setUploadSummary('');
    setFiles(prev => prev.map(f =>
      f.status === 'pending' || f.status === 'error' ? { ...f, status: 'uploading' as const } : f
    ));
    const fd = new FormData();
    pending.forEach(f => fd.append('files', f.file));
    try {
      const { data } = await axios.post(`${API}/upload-batch`, fd);
      setFiles(prev => {
        const u = [...prev];
        for (const r of (data.results ?? []) as any[]) {
          const idx = u.findIndex(f => f.file.name === r.filename && f.status === 'uploading');
          if (idx !== -1) u[idx] = { ...u[idx], status: r.status === 'success' ? 'success' : 'error', message: r.message };
        }
        return u;
      });
      setUploadSummary(data.summary);
    } catch (err: any) {
      setFiles(prev => prev.map(f =>
        f.status === 'uploading' ? { ...f, status: 'error' as const, message: 'Upload failed.' } : f
      ));
      setUploadSummary(err.response?.data?.detail ?? 'Batch upload failed.');
    } finally { setUploading(false); }
  };

  // ── query ──────────────────────────────────────────────────────────────────
  const handleQuery = async () => {
    if (!query.trim()) return;
    setQuerying(true); setResponse(null);
    const imageToUpload = queryImage;
    if (queryImage) removeQueryImage();

    const fd = new FormData();
    fd.append('query_text', query);
    if (imageToUpload) fd.append('image', imageToUpload.file);
    try {
      const { data } = await axios.post(`${API}/query`, fd);
      setResponse(data);
    } catch (err: any) {
      setResponse({
        error: true,
        response: err.response?.data?.detail ?? 'Analysis failed. Ensure the backend is running.',
        vector_context: '', graph_context: '',
        hit_counts: { text_audio: 0, image: 0, graph: 0 },
        image_context_enabled: false,
      });
    } finally { setQuerying(false); }
  };

  const pendingCount = files.filter(f => f.status === 'pending' || f.status === 'error').length;
  const successCount = files.filter(f => f.status === 'success').length;

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen text-slate-100" style={{ background: 'linear-gradient(135deg, #080d1a 0%, #0d1b33 50%, #080d1a 100%)' }}>

      {/* Ambient blobs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden -z-10">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full opacity-20" style={{ background: 'radial-gradient(circle, #0ea5e9, transparent 70%)' }} />
        <div className="absolute top-1/2 -right-40 w-96 h-96 rounded-full opacity-15" style={{ background: 'radial-gradient(circle, #818cf8, transparent 70%)' }} />
        <div className="absolute -bottom-40 left-1/3 w-80 h-80 rounded-full opacity-10" style={{ background: 'radial-gradient(circle, #34d399, transparent 70%)' }} />
      </div>

      <div className="max-w-4xl mx-auto px-4 py-10 space-y-6">

        {/* ── Header ── */}
        <header className="text-center pb-4">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #0ea5e9, #818cf8)' }}>
              <Brain className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-5xl font-extrabold tracking-tight" style={{ background: 'linear-gradient(135deg, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              MediRAG
            </h1>
          </div>
          <p className="text-slate-400 text-lg">Multi-Modal Graph-Based RAG for Medical Diagnostics</p>
          <div className="flex items-center justify-center gap-4 mt-4 text-xs text-slate-500">
            <span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-sky-400" />Whisper ASR</span>
            <span className="w-1 h-1 rounded-full bg-slate-600" />
            <span className="flex items-center gap-1.5"><Database className="w-3.5 h-3.5 text-violet-400" />Pinecone</span>
            <span className="w-1 h-1 rounded-full bg-slate-600" />
            <span className="flex items-center gap-1.5"><Zap className="w-3.5 h-3.5 text-emerald-400" />Gemini 2.0 Flash</span>
            <span className="w-1 h-1 rounded-full bg-slate-600" />
            <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5 text-amber-400" />NetworkX Graph</span>
          </div>
        </header>

        {/* ── Ingestion ── */}
        <section className="glass rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-bold flex items-center gap-2 text-sky-300">
              <Upload className="w-5 h-5" /> Knowledge Ingestion
            </h2>
            {files.length > 0 && (
              <button onClick={clearAll} className="text-xs text-slate-500 hover:text-red-400 transition-colors">Clear all</button>
            )}
          </div>

          {/* Drop zone */}
          <div
            onDragEnter={handleDrag} onDragLeave={handleDrag}
            onDragOver={handleDrag} onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300 ${
              dragActive
                ? 'border-sky-400 bg-sky-500/10 scale-[1.01]'
                : 'border-slate-600 hover:border-sky-600 hover:bg-sky-500/5'
            }`}
          >
            <input ref={fileInputRef} type="file" multiple onChange={e => { if (e.target.files?.length) { addFiles(e.target.files); e.target.value = ''; } }} accept=".pdf,.png,.jpg,.jpeg,.mp3,.wav,.m4a" className="hidden" />
            <Upload className={`w-10 h-10 mx-auto mb-3 transition-colors ${dragActive ? 'text-sky-400' : 'text-slate-600'}`} />
            <p className="text-sm text-slate-400">
              <span className="font-semibold text-sky-400">Click to browse</span> or drag & drop
            </p>
            <p className="text-xs text-slate-600 mt-1">PDF • PNG • JPG • MP3 • WAV • M4A</p>
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-500 px-1">
                <span>{files.length} file{files.length > 1 ? 's' : ''}</span>
                {successCount > 0 && <span className="text-emerald-400">{successCount} ingested</span>}
              </div>
              <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1">
                {files.map((f, i) => (
                  <div key={`${f.file.name}-${i}`} className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm border transition-all duration-300 ${
                    f.status === 'success'   ? 'bg-emerald-900/20 border-emerald-700/30' :
                    f.status === 'error'     ? 'bg-red-900/20 border-red-700/30' :
                    f.status === 'uploading' ? 'bg-sky-900/20 border-sky-700/30' :
                                               'bg-slate-800/40 border-slate-700/30'
                  }`}>
                    <span className={`flex-shrink-0 ${f.status === 'success' ? 'text-emerald-400' : f.status === 'error' ? 'text-red-400' : f.status === 'uploading' ? 'text-sky-400' : 'text-slate-500'}`}>
                      {f.status === 'uploading' ? <Loader2 className="w-4 h-4 animate-spin" /> :
                       f.status === 'success'   ? <CheckCircle2 className="w-4 h-4" /> :
                       f.status === 'error'     ? <AlertCircle className="w-4 h-4" /> :
                       fileIcon(f.file.name)}
                    </span>
                    <span className="truncate flex-1 text-slate-200 font-medium">{f.file.name}</span>
                    <span className="text-xs text-slate-500 flex-shrink-0">{fmtSize(f.file.size)}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 font-semibold ${
                      f.status === 'pending'   ? 'bg-slate-700 text-slate-400' :
                      f.status === 'uploading' ? 'bg-sky-900/60 text-sky-300' :
                      f.status === 'success'   ? 'bg-emerald-900/60 text-emerald-300' :
                                                 'bg-red-900/60 text-red-300'
                    }`}>{fileLabel(f.file.name)}</span>
                    {(f.status === 'pending' || f.status === 'error') && (
                      <button onClick={e => { e.stopPropagation(); removeFile(i); }} className="text-slate-600 hover:text-red-400 transition-colors flex-shrink-0">
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <button
                onClick={handleUpload}
                disabled={uploading || pendingCount === 0}
                className="w-full mt-2 py-2.5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: pendingCount > 0 && !uploading ? 'linear-gradient(135deg, #0ea5e9, #6366f1)' : undefined, backgroundColor: (pendingCount === 0 || uploading) ? '#1e293b' : undefined }}
              >
                {uploading ? <><Loader2 className="w-4 h-4 animate-spin" />Processing...</> : <><Upload className="w-4 h-4" />Ingest {pendingCount} file{pendingCount > 1 ? 's' : ''}</>}
              </button>
            </div>
          )}

          {uploadSummary && (
            <p className={`mt-3 text-sm font-medium ${uploadSummary.toLowerCase().includes('failed') || uploadSummary.includes('skipped') ? 'text-amber-400' : 'text-emerald-400'}`}>
              {uploadSummary}
            </p>
          )}
        </section>

        {/* ── Query ── */}
        <section className="glass rounded-2xl p-6">
          <h2 className="text-lg font-bold flex items-center gap-2 text-violet-300 mb-5">
            <Send className="w-5 h-5" /> Diagnostic Query
          </h2>

          {queryImage && (
            <div className="mb-3 flex items-center gap-3 rounded-xl border border-slate-700/50 bg-slate-800/40 p-2.5">
              <img src={queryImage.preview} alt="Attached" className="h-14 w-14 rounded-lg object-cover border border-slate-700" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-200">{queryImage.file.name}</p>
                <p className="text-xs text-slate-500">Attached for visual analysis</p>
              </div>
              <button onClick={removeQueryImage} className="text-slate-600 hover:text-red-400 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text" value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleQuery()}
              placeholder="Describe symptoms, ask about a report, paste findings…"
              className="flex-1 px-4 py-2.5 rounded-xl text-sm bg-slate-800/60 border border-slate-700 text-slate-100 placeholder-slate-500 outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/40 transition-all"
            />
            <input ref={queryImageRef} type="file" accept="image/png,image/jpeg" onChange={handleQueryImageChange} className="hidden" />
            <button
              onClick={() => queryImageRef.current?.click()}
              className="px-4 py-2.5 rounded-xl text-sm font-medium border border-slate-700 text-slate-300 hover:border-violet-500 hover:text-violet-300 flex items-center gap-2 transition-all whitespace-nowrap"
            >
              <Image className="w-4 h-4" />
              {queryImage ? 'Change image' : 'Attach image'}
            </button>
            <button
              onClick={handleQuery}
              disabled={querying || !query.trim()}
              className="px-6 py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: !querying && query.trim() ? 'linear-gradient(135deg, #6366f1, #0ea5e9)' : '#1e293b' }}
            >
              {querying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              {querying ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
        </section>

        {/* ── Response ── */}
        {response && (
          <section className="glass rounded-2xl p-6 space-y-5 animate-in fade-in slide-in-from-bottom-3 duration-500">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'linear-gradient(135deg, #0ea5e9, #6366f1)' }}>
                <Brain className="w-4 h-4 text-white" />
              </div>
              <h2 className="text-lg font-bold text-slate-100">Analysis Report</h2>
              <div className="ml-auto flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${(response.hit_counts?.text_audio ?? 0) > 0 ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                  {response.hit_counts?.text_audio ?? 0} text/audio
                </span>
                <span className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${(response.hit_counts?.image ?? 0) > 0 ? 'bg-sky-400' : 'bg-slate-600'}`} />
                  {response.hit_counts?.image ?? 0} image
                </span>
                <span className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${(response.hit_counts?.graph ?? 0) > 0 ? 'bg-violet-400' : 'bg-slate-600'}`} />
                  graph
                </span>
              </div>
            </div>

            {/* Main response */}
            <div className={`glass-hi rounded-xl p-5 ${response.error ? 'border-red-500/50 bg-red-900/20' : ''}`}>
              <p className={`whitespace-pre-wrap leading-relaxed text-sm ${response.error ? 'text-red-200' : 'text-slate-200'}`}>
                {parseResponse(response.response).mainText}
              </p>
            </div>

            {parseResponse(response.response).disclaimer && !response.error && (
              <div className="rounded-xl border border-amber-500/50 bg-amber-900/20 p-4 flex gap-3 mt-4 items-start shadow-lg">
                <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-amber-200 text-sm leading-relaxed font-medium">
                  {parseResponse(response.response).disclaimer}
                </p>
              </div>
            )}

            {/* Collapsible context panels */}
            <div className="space-y-3 mt-4">
              {response.vector_context && response.vector_context.trim() !== '' && (
                <ContextPanel
                  title="Vector Context (Pinecone)"
                  icon={<Database className="w-4 h-4 text-sky-400" />}
                  content={response.vector_context}
                  accent="border-sky-700/30"
                />
              )}
              {response.graph_context && response.graph_context.trim() !== '' && (
                <ContextPanel
                  title="Graph Context (NetworkX)"
                  icon={<Activity className="w-4 h-4 text-violet-400" />}
                  content={response.graph_context}
                  accent="border-violet-700/30"
                />
              )}
              {response.image_analysis && response.image_analysis.trim() !== '' && (
                <ContextPanel
                  title="Image Analysis (Gemini Vision)"
                  icon={<Image className="w-4 h-4 text-emerald-400" />}
                  content={response.image_analysis}
                  accent="border-emerald-700/30"
                />
              )}
            </div>
          </section>
        )}

        <KnowledgeGraph />

      </div>
    </div>
  );
}
