'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, Project } from '@/lib/api';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newQuery, setNewQuery] = useState('');
  const router = useRouter();

  const load = () => {
    setLoading(true);
    api.projects.list().then(setProjects).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!newName.trim() || !newQuery.trim()) return;
    await api.projects.create({ name: newName, query: newQuery });
    setNewName('');
    setNewQuery('');
    setShowCreate(false);
    load();
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this project?')) return;
    await api.projects.delete(id);
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-brand-600 text-white px-4 py-2 rounded-lg hover:bg-brand-700 text-sm font-medium"
        >
          New Project
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-lg border p-6 space-y-4">
          <h2 className="font-semibold">Create Project</h2>
          <input
            type="text"
            placeholder="Project name"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm"
          />
          <textarea
            placeholder="Search query (e.g. construction services Germany)"
            value={newQuery}
            onChange={e => setNewQuery(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm h-24"
          />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm">
              Create
            </button>
            <button onClick={() => setShowCreate(false)} className="text-gray-500 px-4 py-2 text-sm">
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No projects yet. Create one to get started.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map(p => (
            <div
              key={p.id}
              className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => router.push(`/projects/${p.id}`)}
            >
              <div className="flex items-start justify-between">
                <h3 className="font-semibold">{p.name}</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  p.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  {p.status}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-2 line-clamp-2">{p.query}</p>
              <div className="flex items-center gap-3 mt-3 text-xs text-gray-400">
                <span>{p.scoring_profile}</span>
                <span>Depth {p.max_discovery_depth}</span>
                <span>Max {p.max_sources} sources</span>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
                className="mt-3 text-xs text-red-500 hover:text-red-700"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
