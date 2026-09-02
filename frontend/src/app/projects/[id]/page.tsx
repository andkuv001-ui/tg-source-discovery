'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api, Project, DiscoveryRun, SourceWithScore } from '@/lib/api';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [runs, setRuns] = useState<DiscoveryRun[]>([]);
  const [sources, setSources] = useState<SourceWithScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [p, r, s] = await Promise.all([
        api.projects.get(projectId),
        api.discovery.listRuns(projectId),
        api.sources.listForProject(projectId, { limit: 100 }),
      ]);
      setProject(p);
      setRuns(r);
      setSources(s);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (projectId) load(); }, [projectId]);

  const startDiscovery = async () => {
    setDiscovering(true);
    try {
      await api.discovery.start(projectId);
      load();
    } finally {
      setDiscovering(false);
    }
  };

  const exportData = async (format: 'json' | 'csv') => {
    const data = await api.export.sources(projectId, format);
    const blob = new Blob(
      [format === 'csv' ? data.csv : JSON.stringify(data, null, 2)],
      { type: format === 'csv' ? 'text/csv' : 'application/json' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sources_${projectId.slice(0, 8)}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;
  if (!project) return <div className="text-center py-12 text-gray-500">Project not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => router.push('/projects')} className="text-sm text-gray-500 hover:text-gray-700 mb-1">
            &larr; Projects
          </button>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <p className="text-gray-500 text-sm mt-1">{project.query}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={startDiscovery}
            disabled={discovering}
            className="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium disabled:opacity-50"
          >
            {discovering ? 'Starting...' : 'Start Discovery'}
          </button>
          <button onClick={() => exportData('json')} className="border px-4 py-2 rounded-lg text-sm hover:bg-gray-50">
            Export JSON
          </button>
          <button onClick={() => exportData('csv')} className="border px-4 py-2 rounded-lg text-sm hover:bg-gray-50">
            Export CSV
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
        <Info label="Profile" value={project.scoring_profile} />
        <Info label="Depth" value={String(project.max_discovery_depth)} />
        <Info label="Max Sources" value={String(project.max_sources)} />
        <Info label="Languages" value={(project.languages || []).join(', ') || 'All'} />
      </div>

      {runs.length > 0 && (
        <div className="bg-white rounded-lg border p-6">
          <h2 className="font-semibold mb-4">Discovery Runs</h2>
          <div className="space-y-2">
            {runs.slice(0, 5).map(run => (
              <div key={run.id} className="flex items-center justify-between text-sm py-2 border-b last:border-0">
                <div className="flex items-center gap-3">
                  <StatusBadge status={run.status} />
                  <span className="text-gray-600">{run.current_stage || 'pending'}</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-24 bg-gray-100 rounded-full h-1.5">
                    <div className="bg-brand-500 h-1.5 rounded-full" style={{ width: `${run.progress * 100}%` }} />
                  </div>
                  <span className="text-gray-400 w-10 text-right">{Math.round(run.progress * 100)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {sources.length > 0 && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <div className="px-6 py-4 border-b">
            <h2 className="font-semibold">Sources ({sources.length})</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-6 py-3 font-medium text-gray-500">Source</th>
                <th className="text-left px-6 py-3 font-medium text-gray-500">Type</th>
                <th className="text-left px-6 py-3 font-medium text-gray-500">Members</th>
                <th className="text-left px-6 py-3 font-medium text-gray-500">Score</th>
                <th className="text-left px-6 py-3 font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sources.map(s => (
                <tr key={s.source.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3">
                    <div>
                      <div className="font-medium">{s.source.title || s.source.username || 'Unknown'}</div>
                      {s.source.username && (
                        <div className="text-gray-400 text-xs">@{s.source.username}</div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-3">
                    <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{s.source.source_type || '-'}</span>
                  </td>
                  <td className="px-6 py-3 text-gray-600">{s.source.member_count?.toLocaleString() || '-'}</td>
                  <td className="px-6 py-3">
                    <ScoreBadge score={s.score.total} />
                  </td>
                  <td className="px-6 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => api.sources.review(s.source.id, projectId, 'approve')}
                        className="text-xs text-green-600 hover:text-green-800"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => api.sources.review(s.source.id, projectId, 'reject')}
                        className="text-xs text-red-600 hover:text-red-800"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => router.push(`/projects/${projectId}/sources/${s.source.id}`)}
                        className="text-xs text-brand-600 hover:text-brand-800"
                      >
                        Detail
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sources.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          No sources found yet. Start a discovery run to find sources.
        </div>
      )}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-lg border p-3">
      <div className="text-gray-500 text-xs">{label}</div>
      <div className="font-medium mt-0.5">{value || '-'}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-600',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-yellow-100 text-yellow-700',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${colors[status] || 'bg-gray-100 text-gray-500'}`}>
      {status}
    </span>
  );
}

function ScoreBadge({ score }: { score: number }) {
  let color = 'text-red-600 bg-red-50';
  if (score >= 80) color = 'text-green-700 bg-green-50';
  else if (score >= 60) color = 'text-yellow-700 bg-yellow-50';
  else if (score >= 40) color = 'text-orange-600 bg-orange-50';
  return (
    <span className={`text-sm font-semibold px-2 py-0.5 rounded ${color}`}>
      {score.toFixed(1)}
    </span>
  );
}
