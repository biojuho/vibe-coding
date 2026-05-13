
"use client";

import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import {
  Book, Code, Github, ExternalLink, RefreshCw, Smartphone,
  Search, FileText, PieChart, Layers, Shield, Clock, SquareActivity
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog";

import DashboardCharts from "../components/DashboardCharts";
import QaQcPanel, { type QaQcData } from "../components/QaQcPanel";
import ActivityTimeline from "../components/ActivityTimeline";
import ProductReadinessPanel, { type ProductReadinessData } from "../components/ProductReadinessPanel";

// ── Types ────────────────────────────────────────────
interface GithubRepo {
  id: number;
  name: string;
  description: string;
  html_url: string;
  language: string | null;
  stargazers_count: number;
  updated_at: string;
}

interface Source {
  id: string;
  title: string;
  type?: string;
}

interface Notebook {
  id: string;
  title: string;
  source_count: number;
  url: string;
  ownership: string;
  sources?: Source[];
}

interface SessionEntry {
  date: string;
  tool: string;
  summary: string;
  verdict?: string;
  files_changed?: number;
}

interface DashboardData {
  last_updated: string;
  github: GithubRepo[];
  notebooklm: Notebook[];
  qaqc?: QaQcData;
  readiness?: ProductReadinessData;
  sessions?: SessionEntry[];
}

type TabId = "operations" | "knowledge" | "qaqc" | "activity";

// Keep client-side API responses on a typed path before they reach render.
function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDashboardDataPayload(value: unknown): value is DashboardData {
  return (
    isObject(value) &&
    typeof value.last_updated === "string" &&
    Array.isArray(value.github) &&
    Array.isArray(value.notebooklm)
  );
}

function isQaQcPayload(value: unknown): value is QaQcData {
  return (
    isObject(value) &&
    typeof value.timestamp === "string" &&
    typeof value.verdict === "string" &&
    isObject(value.total)
  );
}

function isProductReadinessPayload(value: unknown): value is ProductReadinessData {
  return (
    isObject(value) &&
    typeof value.generated_at === "string" &&
    isObject(value.overall) &&
    Array.isArray(value.projects) &&
    Array.isArray(value.next_actions)
  );
}

function getApiErrorMessage(value: unknown, fallback: string) {
  if (isObject(value) && typeof value.error === "string") {
    return value.error;
  }

  return fallback;
}

const SESSION_REQUEST_TIMEOUT_MS = 10000;

async function requestSession(
  method: "POST" | "DELETE",
  body?: { apiKey: string },
): Promise<{ response: Response; payload: unknown }> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), SESSION_REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch("/api/auth/session", {
      method,
      cache: "no-store",
      signal: controller.signal,
      headers: body ? { "content-type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const payload = await response.json().catch(() => null);
    return { response, payload };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`Session request timed out after ${SESSION_REQUEST_TIMEOUT_MS}ms.`);
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function clearSession(fallbackMessage: string) {
  const { response, payload } = await requestSession("DELETE");
  if (!response.ok) {
    throw new Error(getApiErrorMessage(payload, fallbackMessage));
  }
}

// ── Tab Component ────────────────────────────────────
function TabBar({
  activeTab,
  onTabChange,
  data,
}: {
  activeTab: TabId;
  onTabChange: (t: TabId) => void;
  data: DashboardData | null;
}) {
  const tabs: { id: TabId; label: string; icon: React.ReactNode; count?: number }[] = [
    {
      id: "operations",
      label: "운영 콘솔",
      icon: <SquareActivity className="w-4 h-4" />,
      count: data?.readiness?.overall?.blocked_count,
    },
    {
      id: "knowledge",
      label: "지식 현황",
      icon: <Layers className="w-4 h-4" />,
      count: data ? (data.github.length + data.notebooklm.length) : 0,
    },
    {
      id: "qaqc",
      label: "QA/QC 현황",
      icon: <Shield className="w-4 h-4" />,
      count: data?.qaqc?.total?.passed,
    },
    {
      id: "activity",
      label: "활동 타임라인",
      icon: <Clock className="w-4 h-4" />,
      count: data?.sessions?.length,
    },
  ];

  return (
    <div className="flex gap-2 bg-slate-900/60 p-1.5 rounded-xl border border-white/5 backdrop-blur-sm">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
            activeTab === tab.id
              ? "bg-white/10 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
          }`}
        >
          {tab.icon}
          {tab.label}
          {tab.count !== undefined && tab.count > 0 && (
            <span className="ml-1 text-xs bg-slate-700/80 px-1.5 py-0.5 rounded-full">
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

// ── Main Dashboard ───────────────────────────────────
export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedNotebook, setSelectedNotebook] = useState<Notebook | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("operations");

  const [authError, setAuthError] = useState(false);
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sessionVersion, setSessionVersion] = useState(0);
  const deferredSearchTerm = useDeferredValue(searchTerm);

  useEffect(() => {
    let isActive = true;
    const controllers = new Set<AbortController>();
    startTransition(() => {
      setLoading(true);
      setLoadError(null);
    });

    // Treat transport errors and shape errors separately so the UI can
    // distinguish bad credentials from broken data.
    const fetchJson = async (url: string, timeoutMs = 15000) => {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
      controllers.add(controller);

      let response: Response;
      let payload: unknown = null;

      try {
        response = await fetch(url, { cache: "no-store", signal: controller.signal });
        payload = await response.json().catch(() => null);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          throw new Error(`Request timed out while loading ${url}.`);
        }

        throw error;
      } finally {
        window.clearTimeout(timeoutId);
        controllers.delete(controller);
      }

      if (response.status === 401) {
        throw new Error("Unauthorized");
      }

      if (!response.ok) {
        throw new Error(getApiErrorMessage(payload, `Request failed (${response.status})`));
      }

      return payload;
    };

    void (async () => {
      try {
        const dashboardPayload = await fetchJson("/api/data/dashboard");
        if (!isDashboardDataPayload(dashboardPayload)) {
          throw new Error("Dashboard payload is malformed.");
        }

        const nextData: DashboardData = { ...dashboardPayload };

        try {
          const qaqcPayload = await fetchJson("/api/data/qaqc");
          if (isQaQcPayload(qaqcPayload)) {
            nextData.qaqc = qaqcPayload;
          }
        } catch (error) {
          if (error instanceof Error && error.message === "Unauthorized") {
            throw error;
          }

          console.warn("QA/QC payload could not be loaded. Continuing without it.", error);
        }

        try {
          const readinessPayload = await fetchJson("/api/data/readiness");
          if (isProductReadinessPayload(readinessPayload)) {
            nextData.readiness = readinessPayload;
          }
        } catch (error) {
          if (error instanceof Error && error.message === "Unauthorized") {
            throw error;
          }

          console.warn("Product readiness payload could not be loaded. Continuing without it.", error);
        }

        if (!isActive) return;

        startTransition(() => {
          setData(nextData);
          setAuthError(false);
          setLoadError(null);
          setLoading(false);
        });
      } catch (error) {
        if (!isActive) return;

        const unauthorized = error instanceof Error && error.message === "Unauthorized";
        const message = error instanceof Error ? error.message : "Dashboard data could not be loaded.";

        startTransition(() => {
          setData(null);
          setAuthError(unauthorized);
          setLoadError(unauthorized ? null : message);
          setLoading(false);
        });
      }
    })();

    return () => {
      isActive = false;
      controllers.forEach((controller) => controller.abort());
      controllers.clear();
    };
  }, [sessionVersion]);

  // Smart Tagging Logic
  const getTags = (item: GithubRepo | Notebook) => {
    const text = 'name' in item
      ? `${item.name} ${item.description || ''} ${item.language || ''}`.toLowerCase()
      : `${item.title} ${item.sources?.map(s => s.title).join(' ') || ''}`.toLowerCase();

    const tags = [];
    if (text.includes('analysis') || text.includes('report') || text.includes('study') || text.includes('연구'))
      tags.push({ label: '연구 (Research)', color: 'bg-indigo-500/20 text-indigo-300' });
    if (text.includes('project') || text.includes('app') || text.includes('web') || text.includes('dev') || text.includes('코딩'))
      tags.push({ label: '개발 (Dev)', color: 'bg-emerald-500/20 text-emerald-300' });
    if (text.includes('meeting') || text.includes('plan') || text.includes('회의') || text.includes('기획'))
      tags.push({ label: '기획 (Plan)', color: 'bg-orange-500/20 text-orange-300' });
    if (text.includes('paper') || text.includes('pdf') || text.includes('논문'))
      tags.push({ label: '자료 (Docs)', color: 'bg-sky-500/20 text-sky-300' });
    return tags.slice(0, 3);
  };

  // Smart Search
  const filteredData = useMemo(() => {
    if (!data) return { github: [], notebooklm: [] };
    const lowerTerm = deferredSearchTerm.trim().toLowerCase();
    if (!lowerTerm) {
      return {
        github: data.github,
        notebooklm: data.notebooklm,
      };
    }

    return {
      github: data.github.filter(repo =>
        repo.name.toLowerCase().includes(lowerTerm) ||
        (repo.description && repo.description.toLowerCase().includes(lowerTerm)) ||
        (repo.language && repo.language.toLowerCase().includes(lowerTerm))
      ),
      notebooklm: data.notebooklm.filter(nb =>
        nb.title.toLowerCase().includes(lowerTerm)
      ),
    };
  }, [data, deferredSearchTerm]);

  // Stats Logic
  const stats = useMemo(() => {
    if (!data) return null;
    const languages: { [key: string]: number } = {};
    filteredData.github.forEach(repo => {
      if (repo.language) {
        languages[repo.language] = (languages[repo.language] || 0) + 1;
      }
    });
    const sortedLangs = Object.entries(languages).sort(([, a], [, b]) => b - a);
    const totalSources = filteredData.notebooklm.reduce((acc, curr) => acc + curr.source_count, 0);
    return { sortedLangs, totalSources };
  }, [data, filteredData]);

  const githubCount = filteredData.github.length;
  const notebookCount = filteredData.notebooklm.length;

  if (authError) {
    return (
      <div className="min-h-screen bg-[#0f172a] text-white flex items-center justify-center font-sans p-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-purple-600/20 blur-[120px] rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
        <Card className="w-full max-w-md bg-slate-900/60 border-white/10 backdrop-blur-md z-10 p-2">
          <CardContent className="pt-6 space-y-6">
            <div className="text-center space-y-2">
              <Shield className="w-12 h-12 text-blue-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold">인증이 필요합니다</h2>
              <p className="text-sm text-slate-400">
                대시보드 데이터를 조회하려면 API 키를 입력하세요.
              </p>
            </div>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                const apiKeyInput = String(fd.get("apiKey") ?? "").trim();
                if (!apiKeyInput) {
                  return;
                }

                setAuthSubmitting(true);
                setLoadError(null);

                try {
                  const { response, payload } = await requestSession("POST", { apiKey: apiKeyInput });

                  if (response.status === 401) {
                    setAuthError(true);
                    return;
                  }

                  if (!response.ok) {
                    setAuthError(false);
                    setLoadError(getApiErrorMessage(payload, "세션을 생성하지 못했습니다."));
                    return;
                  }

                  setAuthError(false);
                  setLoadError(null);
                  setLoading(true);
                  setSessionVersion((current) => current + 1);
                } catch (error) {
                  setAuthError(false);
                  setLoadError(error instanceof Error ? error.message : "?몄뀡???앹꽦?섏? 紐삵뻽?듬땲??");
                } finally {
                  setAuthSubmitting(false);
                }
              }}
              className="space-y-4"
            >
              <Input
                name="apiKey"
                type="password"
                placeholder="DASHBOARD_API_KEY 입력..."
                className="bg-slate-800/50 border-white/10 text-white"
                autoFocus
              />
              {authError && (
                <p className="text-sm text-red-400 text-center">인증에 실패했습니다. 키를 확인하세요.</p>
              )}
              <Button type="submit" className="w-full bg-blue-600 hover:bg-blue-500" disabled={authSubmitting}>
                인증 후 접속
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="min-h-screen bg-[#0f172a] text-white flex items-center justify-center font-sans p-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-blue-600/20 blur-[120px] rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
        <Card className="w-full max-w-lg bg-slate-900/60 border-white/10 backdrop-blur-md z-10 p-2">
          <CardContent className="pt-6 space-y-5">
            <div className="space-y-2 text-center">
              <Shield className="w-12 h-12 text-amber-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-white">데이터를 불러오지 못했습니다</h2>
              <p className="text-sm text-slate-400">
                인증은 통과했지만 대시보드 응답이 유효하지 않았습니다.
              </p>
            </div>
            <div className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm leading-6 text-amber-100">
              {loadError}
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                className="flex-1 bg-blue-600 hover:bg-blue-500"
                onClick={() => window.location.reload()}
              >
                다시 시도
              </Button>
              <Button
                variant="outline"
                className="flex-1 border-white/10 bg-white/5 hover:bg-white/10"
                onClick={async () => {
                  try {
                    await clearSession("?꾩〈 ?몄쬆 ?몃? 留덉?瑜??앹젣?섏? 紐삵뻽?듬땲??");
                    setLoadError(null);
                    setAuthError(true);
                  } catch (error) {
                    setLoadError(error instanceof Error ? error.message : "?몄쬆 ?몃? 珥덇린?붿뿉 ?ㅽ뙣?덉뒿?덈떎.");
                  }
                }}
              >
                키 다시 입력
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f172a] text-white p-8 relative overflow-hidden font-sans">
      {/* Background Gradients */}
      <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-purple-600/20 blur-[120px] rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-blue-600/20 blur-[120px] rounded-full translate-x-1/2 translate-y-1/2 pointer-events-none" />

      <main className="max-w-7xl mx-auto relative z-10 space-y-8">
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-linear-to-r from-blue-400 to-purple-400 mb-2">
              나만의 지식 관리 대시보드
            </h1>
            <p className="text-slate-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              연동 상태: 활성
              {data && (
                <span className="text-xs text-slate-500 ml-2">
                  (업데이트: {new Date(data.last_updated).toLocaleString()})
                  <button
                    onClick={async () => {
                      try {
                        await clearSession("?몄쬆 ?몃? 醫낅즺?섏? 紐삵뻽?듬땲??");
                        setData(null);
                        setLoadError(null);
                        setAuthError(true);
                      } catch (error) {
                        setLoadError(error instanceof Error ? error.message : "?몄쬆 ?몃? 醫낅즺?먯꽌 ?ㅽ뙣?덉뒿?덈떎.");
                      }
                    }}
                    className="ml-4 hover:underline"
                  >
                    로그아웃
                  </button>
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {activeTab === "knowledge" && (
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-4 w-4 text-slate-400 group-focus-within:text-blue-400 transition-colors" />
                </div>
                <Input
                  type="text"
                  placeholder="프로젝트나 노트북 검색..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-slate-800/50 border-white/10 w-64 placeholder:text-slate-500"
                />
              </div>
            )}
            <Button
              variant="outline"
              onClick={() => window.location.reload()}
              className="bg-white/5 hover:bg-white/10 border-white/10 backdrop-blur-md group"
            >
              <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
              새로고침
            </Button>
          </div>
        </header>

        {/* Tab Bar */}
        {!loading && <TabBar activeTab={activeTab} onTabChange={setActiveTab} data={data} />}

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
          </div>
        ) : (
          <>
            {activeTab === "operations" && (
              data?.readiness ? (
                <ProductReadinessPanel data={data.readiness} />
              ) : (
                <div className="text-center py-16 text-slate-500">
                  <SquareActivity className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p className="text-lg">제품 출시 점수 데이터가 아직 없습니다</p>
                  <p className="text-sm mt-2">
                    <code className="bg-slate-800 px-2 py-1 rounded text-xs">
                      python execution/product_readiness_score.py
                    </code>
                    를 실행해 최신 운영 데이터를 생성하세요.
                  </p>
                </div>
              )
            )}

            {/* ── TAB: 지식 현황 ──────────────── */}
            {activeTab === "knowledge" && (
              <>
                {stats && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <Card className="bg-linear-to-br from-slate-900 via-slate-900 to-slate-800">
                      <CardContent className="p-5 flex items-center gap-4">
                        <div className="p-3 bg-blue-500/20 rounded-xl text-blue-400">
                          <Layers className="w-6 h-6" />
                        </div>
                        <div>
                          <p className="text-slate-400 text-sm">연동된 자산</p>
                          <div className="flex items-baseline gap-2">
                            <span className="text-2xl font-bold text-white">{githubCount + notebookCount}</span>
                            <span className="text-xs text-slate-500">Items</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="bg-linear-to-br from-slate-900 via-slate-900 to-slate-800">
                      <CardContent className="p-5 flex flex-col justify-center gap-2">
                        <div className="flex items-center gap-2 mb-1">
                          <PieChart className="w-4 h-4 text-emerald-400" />
                          <p className="text-slate-400 text-sm">주요 언어 분포</p>
                        </div>
                        <div className="flex gap-2 h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                          {stats.sortedLangs.slice(0, 3).map(([lang, count]) => (
                            <div
                              key={lang}
                              className={`h-full ${getLanguageColor(lang)}`}
                              style={{ width: `${githubCount > 0 ? (count / githubCount) * 100 : 0}%` }}
                              title={`${lang}: ${count}`}
                            />
                          ))}
                        </div>
                        <div className="flex gap-3 text-xs text-slate-500">
                          {stats.sortedLangs.slice(0, 3).map(([lang]) => (
                            <span key={lang} className="flex items-center gap-1">
                              <div className={`w-1.5 h-1.5 rounded-full ${getLanguageColor(lang)}`} />
                              {lang}
                            </span>
                          ))}
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="bg-linear-to-br from-slate-900 via-slate-900 to-slate-800">
                      <CardContent className="p-5 flex items-center gap-4">
                        <div className="p-3 bg-purple-500/20 rounded-xl text-purple-400">
                          <FileText className="w-6 h-6" />
                        </div>
                        <div>
                          <p className="text-slate-400 text-sm">참조된 소스 파일</p>
                          <div className="flex items-baseline gap-2">
                            <span className="text-2xl font-bold text-white">{stats.totalSources}</span>
                            <span className="text-xs text-slate-500">Files</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {data && (
                  <DashboardCharts
                    githubData={filteredData.github}
                    notebookData={filteredData.notebooklm}
                    query={deferredSearchTerm}
                  />
                )}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* GitHub Section */}
                  <section className="space-y-6">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-3 bg-slate-800/50 rounded-xl border border-white/5">
                        <Github className="w-6 h-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h2 className="text-2xl font-semibold">코딩 프로젝트</h2>
                        <p className="text-sm text-slate-500">GitHub Repositories</p>
                      </div>
                      <Badge variant="secondary" className="bg-slate-800 text-slate-300 rounded-full">
                        {filteredData.github.length}
                      </Badge>
                    </div>

                    <div className="grid gap-4">
                      {filteredData.github.length > 0 ? (
                        filteredData.github.map((repo) => (
                          <div
                            key={repo.id}
                            className="group relative p-6 bg-slate-900/40 border border-white/5 hover:border-blue-500/30 rounded-2xl hover:bg-slate-800/40 transition-all duration-300 backdrop-blur-sm cursor-pointer"
                            onClick={() => window.open(repo.html_url, '_blank')}
                          >
                            <div className="flex justify-between items-start mb-4">
                              <div>
                                <h3 className="text-lg font-medium text-blue-100 group-hover:text-blue-400 transition-colors">
                                  {repo.name}
                                </h3>
                                {repo.language && (
                                  <div className="flex items-center gap-2 mt-2">
                                    <span className="text-xs bg-slate-800 px-2 py-0.5 rounded flex items-center gap-1.5 text-slate-300">
                                      <span className={`w-1.5 h-1.5 rounded-full ${getLanguageColor(repo.language)}`} />
                                      {repo.language}
                                    </span>
                                    {getTags(repo).map((tag, idx) => (
                                      <span key={idx} className={`text-xs px-2 py-0.5 rounded ${tag.color}`}>
                                        {tag.label}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <div className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors">
                                <ExternalLink className="w-4 h-4" />
                              </div>
                            </div>
                            <p className="text-slate-400 text-sm line-clamp-2 min-h-[40px]">
                              {repo.description || "설명이 없습니다."}
                            </p>
                          </div>
                        ))
                      ) : (
                        <div className="text-slate-500 text-center py-8 bg-slate-900/20 rounded-xl border border-white/5 border-dashed">
                          검색 결과가 없습니다.
                        </div>
                      )}
                    </div>
                  </section>

                  {/* NotebookLM Section */}
                  <section className="space-y-6">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-3 bg-slate-800/50 rounded-xl border border-white/5">
                        <Book className="w-6 h-6 text-purple-400" />
                      </div>
                      <div className="flex-1">
                        <h2 className="text-2xl font-semibold">지식 베이스</h2>
                        <p className="text-sm text-slate-500">NotebookLM Notebooks</p>
                      </div>
                      <Badge variant="secondary" className="bg-slate-800 text-slate-300 rounded-full">
                        {filteredData.notebooklm.length}
                      </Badge>
                    </div>

                    <div className="grid gap-4">
                      {filteredData.notebooklm.length > 0 ? (
                        filteredData.notebooklm.map((notebook) => (
                          <div
                            key={notebook.id}
                            className="group relative p-6 bg-slate-900/40 border border-white/5 hover:border-purple-500/30 rounded-2xl hover:bg-slate-800/40 transition-all duration-300 backdrop-blur-sm cursor-pointer"
                            onClick={() => setSelectedNotebook(notebook)}
                          >
                            <div className="flex justify-between items-start mb-2">
                              <div>
                                <h3 className="text-lg font-medium text-purple-100 group-hover:text-purple-400 transition-colors line-clamp-1">
                                  {notebook.title}
                                </h3>
                                <div className="flex gap-2 mt-2">
                                  {getTags(notebook).map((tag, idx) => (
                                    <span key={idx} className={`text-xs px-2 py-0.5 rounded ${tag.color}`}>
                                      {tag.label}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              <div className="p-2 text-slate-400 group-hover:text-white transition-colors opacity-0 group-hover:opacity-100">
                                <Search className="w-4 h-4" />
                              </div>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-slate-400 mt-3">
                              <div className="flex items-center gap-1.5">
                                <Code className="w-4 h-4" />
                                <span>{notebook.source_count}개 소스</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <Smartphone className="w-4 h-4" />
                                <span className="capitalize">{notebook.ownership === 'owned' ? '내 문서' : '공유됨'}</span>
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-slate-500 text-center py-8 bg-slate-900/20 rounded-xl border border-white/5 border-dashed">
                          검색 결과가 없습니다.
                        </div>
                      )}
                    </div>
                  </section>
                </div>
              </>
            )}

            {/* ── TAB: QA/QC 현황 ─────────────── */}
            {activeTab === "qaqc" && (
              data?.qaqc ? (
                <QaQcPanel data={data.qaqc} />
              ) : (
                <div className="text-center py-16 text-slate-500">
                  <Shield className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p className="text-lg">QA/QC 데이터가 아직 없습니다</p>
                  <p className="text-sm mt-2">
                    <code className="bg-slate-800 px-2 py-1 rounded text-xs">python workspace/execution/qaqc_runner.py</code>를 실행하세요
                  </p>
                </div>
              )
            )}

            {/* ── TAB: 활동 타임라인 ──────────── */}
            {activeTab === "activity" && (
              <ActivityTimeline sessions={data?.sessions || []} />
            )}
          </>
        )}
      </main>

      {/* Details Modal */}
      <Dialog open={!!selectedNotebook} onOpenChange={(open) => !open && setSelectedNotebook(null)}>
        {selectedNotebook && (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{selectedNotebook.title}</DialogTitle>
              <DialogDescription>
                <span className="font-mono text-xs text-slate-500">{selectedNotebook.id}</span>
                {getTags(selectedNotebook).length > 0 && (
                  <span className="ml-2">
                    {getTags(selectedNotebook).map((tag, idx) => (
                      <Badge key={idx} variant="outline" className={`${tag.color.replace('/20', '/10')} ml-1`}>
                        {tag.label}
                      </Badge>
                    ))}
                  </span>
                )}
              </DialogDescription>
            </DialogHeader>

            <div className="p-6 max-h-[60vh] overflow-y-auto">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                연결된 소스 파일 ({selectedNotebook.source_count})
              </h3>
              <div className="space-y-2">
                {selectedNotebook.sources && selectedNotebook.sources.length > 0 ? (
                  selectedNotebook.sources.map((source, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg border border-white/5">
                      <div className="p-2 bg-purple-500/20 rounded text-purple-400">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-200 truncate">{source.title}</p>
                        {source.type && <p className="text-xs text-slate-500">{source.type}</p>}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-500 italic">표시할 소스 정보가 없습니다.</p>
                )}
              </div>
            </div>

            <DialogFooter>
              <a href={selectedNotebook.url} target="_blank" rel="noreferrer">
                <Button className="bg-purple-600 hover:bg-purple-500">
                  NotebookLM에서 열기
                  <ExternalLink className="w-4 h-4" />
                </Button>
              </a>
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}

function getLanguageColor(lang: string) {
  const colors: { [key: string]: string } = {
    TypeScript: 'bg-blue-500',
    JavaScript: 'bg-yellow-400',
    Python: 'bg-green-500',
    HTML: 'bg-orange-500',
    CSS: 'bg-blue-300',
    Vue: 'bg-green-400',
    Unknown: 'bg-slate-600'
  };
  return colors[lang] || 'bg-slate-500';
}
