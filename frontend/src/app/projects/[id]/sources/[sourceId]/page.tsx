'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api, Source, SourceWithScore } from '@/lib/api';

export default function SourceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const sourceId = params.sourceId as string;

  const [source, setSource] = useState<Source | null>(null);
  const [scoreData, setScoreData] = useState<{ total: number; breakdown: Record<string, number> } | null>(null);
  const [related, setRelated] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sourceId || !projectId) return;
    setLoading(true);
    Promise.all([
      api.sources.get(sourceId),
      api.sources.getScore(sourceId, projectId).catch(() => null),
      api.sources.getRelated(sourceId).catch(() => []),
    ]).then(([s, sc, r]) => {
      setSource(s);
      setScoreData(sc);
      setRelated(r);
    }).finally(() => setLoading(false));
  }, [sourceId, projectId]);

  const handleReview = async (action: 'approve' | 'reject') => {
    await api.sources.review(sourceId, projectId, action);
    router.push(`/projects/${projectId}`);
  };

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;
  if (!source) return <div className="text-center py-12 text-gray-500">Source not found</div>;

  const topic = source.topic_analysis as Record<string, any> | undefined;
  const geo = source.geography_analysis as Record<string, any> | undefined;
  const lang = source.language_analysis as Record<string, any> | undefined;
  const intent = source.intent_analysis as Record<string, any> | undefined;
  const audience = source.audience_analysis as Record<string, any> | undefined;
  const activity = source.activity_analysis as Record<string, any> | undefined;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => router.push(`/projects/${projectId}`)} className="text-sm text-gray-500 hover:text-gray-700 mb-1">
            &larr; Back to project
          </button>
          <h1 className="text-2xl font-bold">{source.title || source.username || 'Unknown Source'}</h1>
          {source.username && <p className="text-gray-500 text-sm">@{source.username}</p>}
        </div>
        <div className="flex gap-2">
          <button onClick={() => handleReview('approve')} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700">
            Approve
          </button>
          <button onClick={() => handleReview('reject')} className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-700">
            Reject
          </button>
          {source.username && (
            <a
              href={`https://t.me/${source.username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="border px-4 py-2 rounded-lg text-sm hover:bg-gray-50"
            >
              Open in Telegram
            </a>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <InfoBox label="Type" value={source.source_type || '-'} />
        <InfoBox label="Members" value={source.member_count?.toLocaleString() || '-'} />
        <InfoBox label="Status" value={source.status} />
        <InfoBox label="First Seen" value={new Date(source.first_seen_at).toLocaleDateString()} />
      </div>

      {source.description && (
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold text-sm mb-2">Description</h3>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{source.description}</p>
        </div>
      )}

      {scoreData && (
        <div className="bg-white rounded-lg border p-6">
          <h3 className="font-semibold mb-4">Score Breakdown</h3>
          <div className="flex items-center mb-4">
            <span className="text-3xl font-bold">{scoreData.total.toFixed(1)}</span>
            <span className="text-sm text-gray-500 ml-2">/ 100</span>
          </div>
          <div className="space-y-2">
            {Object.entries(scoreData.breakdown).map(([factor, value]) => (
              <div key={factor} className="flex items-center gap-3">
                <span className="text-sm text-gray-600 w-24 capitalize">{factor}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${value >= 70 ? 'bg-green-500' : value >= 40 ? 'bg-yellow-500' : 'bg-red-400'}`}
                    style={{ width: `${value}%` }}
                  />
                </div>
                <span className="text-sm font-medium w-10 text-right">{value.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {topic && (
          <AnalysisCard title="Topic" data={[
            { label: 'Primary', value: topic.primary_topic },
            { label: 'Relevance', value: `${(topic.relevance_to_query * 100).toFixed(0)}%` },
            { label: 'Consistency', value: `${(topic.topic_consistency * 100).toFixed(0)}%` },
            { label: 'Keywords', value: (topic.keywords || []).join(', ') },
          ]} />
        )}

        {geo && (
          <AnalysisCard title="Geography" data={[
            { label: 'Countries', value: (geo.countries || []).join(', ') || 'Unknown' },
            { label: 'Cities', value: (geo.cities || []).join(', ') || '-' },
            { label: 'Specificity', value: geo.specificity },
            { label: 'Confidence', value: `${(geo.confidence * 100).toFixed(0)}%` },
          ]} />
        )}

        {lang && (
          <AnalysisCard title="Language" data={[
            { label: 'Primary', value: lang.primary_language || '-' },
            { label: 'Distribution', value: Object.entries(lang.distribution || {}).map(([l, r]) => `${l}: ${(r as number * 100).toFixed(0)}%`).join(', ') },
            { label: 'Supported', value: lang.supported ? 'Yes' : 'No' },
          ]} />
        )}

        {intent && (
          <AnalysisCard title="Intent" data={[
            { label: 'Primary', value: intent.primary_intent },
            { label: 'Commercial', value: `${(intent.commercial_intent_score * 100).toFixed(0)}%` },
            { label: 'Lead Potential', value: `${(intent.lead_potential * 100).toFixed(0)}%` },
            { label: 'Engagement', value: intent.engagement_type },
          ]} />
        )}

        {audience && (
          <AnalysisCard title="Audience" data={[
            { label: 'Type', value: audience.audience_type },
            { label: 'Expertise', value: audience.expertise_level || '-' },
            { label: 'Engagement', value: audience.engagement_level || '-' },
            { label: 'Professions', value: (audience.professions || []).join(', ') || '-' },
          ]} />
        )}

        {activity && (
          <AnalysisCard title="Activity" data={[
            { label: 'Messages/Day', value: String(activity.messages_per_day || 0) },
            { label: 'Unique Posters', value: String(activity.unique_posters || 0) },
            { label: 'Freshness', value: activity.freshness || '-' },
            { label: 'Trend', value: activity.activity_trend || '-' },
            { label: 'Last Message', value: activity.last_message_age_days != null ? `${activity.last_message_age_days}d ago` : '-' },
          ]} />
        )}
      </div>

      {related.length > 0 && (
        <div className="bg-white rounded-lg border p-6">
          <h3 className="font-semibold mb-4">Related Sources ({related.length})</h3>
          <div className="space-y-2">
            {related.slice(0, 10).map(r => (
              <div key={r.id} className="flex items-center justify-between py-2 border-b last:border-0 text-sm">
                <div>
                  <span className="font-medium">{r.title || r.username || 'Unknown'}</span>
                  {r.username && <span className="text-gray-400 ml-2">@{r.username}</span>}
                </div>
                <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{r.source_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function InfoBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-lg border p-3">
      <div className="text-gray-500 text-xs">{label}</div>
      <div className="font-medium mt-0.5">{value}</div>
    </div>
  );
}

function AnalysisCard({ title, data }: { title: string; data: Array<{ label: string; value: string }> }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <h4 className="font-semibold text-sm mb-3">{title}</h4>
      <div className="space-y-1.5">
        {data.map(d => (
          <div key={d.label} className="flex justify-between text-sm">
            <span className="text-gray-500">{d.label}</span>
            <span className="font-medium text-right max-w-[60%] truncate">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
