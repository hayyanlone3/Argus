// src/components/whitelist/WhitelistManager.jsx
import React, { useEffect, useState } from 'react';
import { whitelistService } from '../../services/whitelistService';
import LoadingSpinner from '../common/LoadingSpinner';
import { formatDate } from '../../utils/formatters';

export default function WhitelistManager() {
  const [whitelist, setWhitelist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTier, setSelectedTier] = useState(null);

  useEffect(() => {
    const fetchWhitelist = async () => {
      try {
        setLoading(true);
        const data = await whitelistService.getWhitelist(selectedTier);
        setWhitelist(data.whitelist || []);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchWhitelist();
  }, [selectedTier]);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="card border border-red-600 text-red-600">Error: {error}</div>;

  const tierColors = {
    1: 'bg-green-50',
    2: 'bg-blue-50',
    3: 'bg-purple-50',
  };

  return (
    <div className="card">
      <h3 className="font-bold text-lg mb-4">✅ Whitelist Management</h3>

      <div className="flex gap-2 mb-4">
        {[null, 1, 2, 3].map((tier) => (
          <button
            key={tier}
            onClick={() => setSelectedTier(tier)}
            className={`px-3 py-1 rounded text-sm transition-all ${
              selectedTier === tier
                ? 'bg-red-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {tier ? `Tier ${tier}` : 'All'}
          </button>
        ))}
      </div>

      {!whitelist.length ? (
        <p className="text-gray-500 text-center py-8">No whitelist entries</p>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {whitelist.map((entry) => (
            <div key={entry.id} className={`p-3 rounded-lg ${tierColors[entry.tier] || 'bg-gray-50'}`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="font-mono text-xs mb-1">{entry.path}</p>
                  {entry.hash_sha256 && (
                    <p className="font-mono text-xs text-gray-600 mb-1">{entry.hash_sha256.substring(0, 16)}...</p>
                  )}
                  <p className="text-xs text-gray-600">{entry.reason}</p>
                </div>
                <div className="text-right text-xs">
                  <p className="badge">Tier {entry.tier}</p>
                  <p className="text-gray-600 mt-1">{formatDate(entry.added_at)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}