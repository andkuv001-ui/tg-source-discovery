'use client';

import { useEffect, useState } from 'react';
import { api, Stats } from '@/lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.stats.get().then(setStats).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Total Sources" value={stats?.total_sources ?? 0} color="blue" />
        <StatCard title="Projects" value={stats?.total_projects ?? 0} color="green" />
        <StatCard title="Discovery Runs" value={stats?.total_runs ?? 0} color="purple" />
        <StatCard title="Avg Score" value={stats?.avg_score ?? 0} color="yellow" isFloat />
      </div>

      {stats && Object.keys(stats.sources_by_status).length > 0 && (
        <div className="bg-white rounded-lg border p-6">
          <h2 className="text-lg font-semibold mb-4">Sources by Status</h2>
          <div className="space-y-2">
            {Object.entries(stats.sources_by_status).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between">
                <span className="text-sm capitalize">{status.replace(/_/g, ' ')}</span>
                <div className="flex items-center gap-3">
                  <div className="w-48 bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-brand-500 h-2 rounded-full"
                      style={{ width: `${Math.min((count / (stats.total_sources || 1)) * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium w-12 text-right">{count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <a
        href="/projects"
        className="inline-block bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 transition-colors text-sm font-medium"
      >
        Go to Projects
      </a>
    </div>
  );
}

function StatCard({ title, value, color, isFloat }: { title: string; value: number; color: string; isFloat?: boolean }) {
  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    purple: 'bg-purple-50 text-purple-700',
    yellow: 'bg-yellow-50 text-yellow-700',
  };
  return (
    <div className="bg-white rounded-lg border p-4">
      <p className="text-sm text-gray-500">{title}</p>
      <p className={`text-2xl font-bold mt-1 ${colorMap[color] || ''}`}>
        {isFloat ? value.toFixed(1) : value}
      </p>
    </div>
  );
}
