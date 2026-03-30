"use client";

import { useMemo, useCallback } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

interface GithubRepo {
    language: string | null;
}

interface NotebookItem {
    title: string;
    source_count: number;
}

interface PieDatum {
    name: string;
    value: number;
}

interface NotebookBarDatum {
    name: string;
    sources: number;
    fullTitle: string;
}

interface DashboardChartsProps {
    githubData: GithubRepo[];
    notebookData: NotebookItem[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];
const BAR_COLORS = ['#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe'];

const tooltipStyle = { backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' };

export default function DashboardCharts({ githubData, notebookData }: DashboardChartsProps) {
    const pieData: PieDatum[] = useMemo(() => {
        const langs: { [key: string]: number } = {};
        githubData.forEach(repo => {
            if (repo.language) {
                langs[repo.language] = (langs[repo.language] || 0) + 1;
            }
        });
        return Object.entries(langs)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 6)
            .map(([name, value]) => ({ name, value }));
    }, [githubData]);

    const barData: NotebookBarDatum[] = useMemo(() => {
        return notebookData
            .sort((a, b) => b.source_count - a.source_count)
            .slice(0, 5)
            .map(nb => ({
                name: nb.title.length > 12 ? nb.title.substring(0, 12) + '…' : nb.title,
                sources: nb.source_count,
                fullTitle: nb.title,
            }));
    }, [notebookData]);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const renderPieLabel = useCallback(({ name, percent }: any) => {
        return `${name} ${(percent * 100).toFixed(0)}%`;
    }, []);

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Pie Chart: Language Distribution */}
            <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <span className="w-2 h-6 bg-blue-500 rounded-sm"></span>
                    언어 분포 (GitHub)
                </h3>
                <div className="h-[250px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={pieData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                fill="#8884d8"
                                paddingAngle={5}
                                dataKey="value"
                                label={renderPieLabel}
                            >
                                {pieData.map((_entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={tooltipStyle}
                                itemStyle={{ color: '#f8fafc' }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Bar Chart: Content Density */}
            <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6 backdrop-blur-sm">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <span className="w-2 h-6 bg-purple-500 rounded-sm"></span>
                    지식 밀도 Top 5 (노트북별 소스 수)
                </h3>
                <div className="h-[250px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={barData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#334155" />
                            <XAxis type="number" stroke="#94a3b8" />
                            <YAxis dataKey="name" type="category" width={100} stroke="#94a3b8" tick={{ fontSize: 12 }} />
                            <Tooltip
                                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                            />
                            <Bar dataKey="sources" fill="#8b5cf6" radius={[0, 4, 4, 0]}>
                                {barData.map((_entry, index) => (
                                    <Cell key={`cell-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}
