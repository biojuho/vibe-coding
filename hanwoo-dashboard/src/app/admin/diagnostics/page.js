
'use client';

import { useState, useEffect } from 'react';
import { getSystemDiagnostics, getRawData } from '@/lib/actions';
import { useRouter } from 'next/navigation';

export default function DiagnosticsPage() {
  const router = useRouter();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState('cattle');
  const [rawData, setRawData] = useState(null);
  const [dataLoading, setDataLoading] = useState(false);

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    loadData(selectedModel);
  }, [selectedModel]);

  const loadStats = async () => {
    setLoading(true);
    const res = await getSystemDiagnostics();
    setStats(res);
    setLoading(false);
  };

  const loadData = async (model) => {
    setDataLoading(true);
    const res = await getRawData(model);
    if(res.success) setRawData(res.data);
    else alert("데이터 로드 실패");
    setDataLoading(false);
  };

  if (loading) return <div className="p-8 text-center text-gray-500">시스템 진단 중...</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto text-gray-800">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">🛠️ 시스템 진단 (System Diagnostics)</h1>
        <button onClick={() => router.push('/')} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 transition">
          ← 대시보드로 돌아가기
        </button>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <StatusCard 
          title="Database Status" 
          value={stats.database.status} 
          sub={stats.database.latency}
          status={stats.success ? 'good' : 'bad'} 
        />
        <StatusCard 
          title="Node.js Runtime" 
          value={stats.nodeVersion} 
          sub={`Uptime: ${Math.floor(stats.uptime / 60)}m`}
          status="neutral" 
        />
        <StatusCard 
          title="Memory Usage" 
          value={`${Math.round(stats.memory.heapUsed / 1024 / 1024)} MB`} 
          sub={`Total: ${Math.round(stats.memory.heapTotal / 1024 / 1024)} MB`}
          status="neutral" 
        />
      </div>

      {/* Database Record Counts */}
      <div className="bg-white p-6 rounded-lg shadow-sm border mb-10">
        <h2 className="text-xl font-bold mb-4">📊 데이터베이스 레코드 현황</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.database.recordCounts && Object.entries(stats.database.recordCounts).map(([key, val]) => (
            <div key={key} className="bg-gray-50 p-4 rounded text-center">
              <div className="text-gray-500 uppercase text-xs font-bold">{key}</div>
              <div className="text-2xl font-black text-blue-600">{val}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Raw Data Viewer */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">🔍 Raw Data Inspector (Top 50)</h2>
          <select 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            className="p-2 border rounded bg-gray-50"
          >
            <option value="cattle">Cattle (소)</option>
            <option value="salesRecord">Sales (판매)</option>
            <option value="feedRecord">Feed (급여)</option>
            <option value="scheduleEvent">Schedule (일정)</option>
            <option value="inventoryItem">Inventory (재고)</option>
            <option value="building">Buildings (축사)</option>
            <option value="farmSettings">Settings (설정)</option>
          </select>
        </div>

        {dataLoading ? (
          <div className="text-center py-10 text-gray-400">데이터 로딩 중...</div>
        ) : (
          <div className="bg-gray-900 text-green-400 p-4 rounded overflow-auto h-96 font-mono text-sm shadow-inner">
            <pre>{JSON.stringify(rawData, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusCard({ title, value, sub, status }) {
    const colors = {
        good: 'bg-green-50 text-green-700 border-green-200',
        bad: 'bg-red-50 text-red-700 border-red-200',
        neutral: 'bg-blue-50 text-blue-700 border-blue-200'
    };
    
    return (
        <div className={`p-6 rounded-xl border ${colors[status] || colors.neutral}`}>
            <div className="text-sm font-semibold opacity-70 mb-1">{title}</div>
            <div className="text-3xl font-bold mb-1">{value}</div>
            <div className="text-xs opacity-80">{sub}</div>
        </div>
    );
}
