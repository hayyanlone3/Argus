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

  const [newPath, setNewPath] = useState('');
  const [newTier, setNewTier] = useState(2);
  const [newReason, setNewReason] = useState('');
  const [isAdding, setIsAdding] = useState(false);

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

  useEffect(() => {
    fetchWhitelist();
  }, [selectedTier]);

  const handleAddEntry = async (e) => {
    e.preventDefault();
    if (!newPath) return;
    try {
      setIsAdding(true);
      await whitelistService.addWhitelist({
        path: newPath,
        tier: parseInt(newTier),
        reason: newReason || 'Manually added by Analyst'
      });
      setNewPath('');
      setNewReason('');
      fetchWhitelist();
    } catch (err) {
      alert("Failed to add whitelist: " + err.message);
    } finally {
      setIsAdding(false);
    }
  };

  if (loading && whitelist.length === 0) return <LoadingSpinner />;

  const tierColors = {
    1: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    2: 'bg-blue-50 text-blue-700 border-blue-100',
    3: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  };

  return (
    <div className="space-y-6">
      {/* Reputation Bias Form */}
      <div className="bg-slate-900 border border-indigo-500/20 rounded-xl p-5 shadow-2xl relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 blur-3xl -mr-16 -mt-16"></div>
        
        <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-indigo-400 mb-4 flex items-center gap-2">
           <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></span> Anomaly Score Suppression
        </h4>

        <form onSubmit={handleAddEntry} className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-2">
             <input 
               className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm font-mono text-slate-200 placeholder:text-slate-600 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
               placeholder="Target Object (Path or Hash)"
               value={newPath}
               onChange={e => setNewPath(e.target.value)}
             />
          </div>
          <select 
            className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm font-bold text-slate-300 outline-none focus:border-indigo-500 cursor-pointer"
            value={newTier}
            onChange={e => setNewTier(e.target.value)}
          >
            <option value={1}>Tier 1: Location Trust</option>
            <option value={2}>Tier 2: Version Trust (+Hash)</option>
            <option value={3}>Tier 3: Universal Trust (Hash Only)</option>
          </select>
          <button 
            type="submit" 
            disabled={isAdding || !newPath}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-black text-[10px] uppercase tracking-widest px-4 py-2 rounded-lg transition-all shadow-lg active:scale-95"
          >
            {isAdding ? 'Applying...' : 'Apply Bias'}
          </button>
        </form>
      </div>

      {/* Filter Chips */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div className="flex gap-2">
          {[null, 1, 2, 3].map((tier) => (
            <button
              key={tier}
              onClick={() => setSelectedTier(tier)}
              className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest transition-all border ${
                selectedTier === tier
                  ? 'bg-slate-800 text-white border-slate-800 shadow-md'
                  : 'bg-white text-slate-500 border-slate-200 hover:border-slate-400'
              }`}
            >
              {tier ? `Tier ${tier}` : 'All Rules'}
            </button>
          ))}
        </div>
        <div className="text-[10px] font-bold text-slate-400">{whitelist.length} Entrie(s)</div>
      </div>

      {!whitelist.length && !loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-center opacity-40">
           <div className="text-4xl mb-4"></div>
           <div className="max-w-[200px] text-xs font-bold leading-relaxed">No trust rules defined. Your system is currently in Maximum Security mode.</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
          {whitelist.map((entry) => (
            <div key={entry.id} className={`p-4 rounded-xl border transition-all hover:shadow-md ${tierColors[entry.tier] || 'bg-slate-50 border-slate-200'}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-[9px] font-black uppercase tracking-[0.2em] opacity-60">Path</span>
                    <div className="h-px bg-current opacity-10 flex-grow"></div>
                  </div>
                  <p className="font-mono text-xs truncate font-bold">{entry.path}</p>
                  
                  <div className="mt-3 flex flex-wrap gap-4 items-center">
                    <div>
                      <span className="text-[9px] font-black uppercase tracking-[0.2em] opacity-40 block mb-0.5">Reason</span>
                      <p className="text-[11px] font-medium italic opacity-80">{entry.reason}</p>
                    </div>
                  </div>
                </div>
                
                <div className="text-right flex-shrink-0">
                  <span className="inline-block px-2 py-0.5 rounded-full border border-current text-[9px] font-black tracking-widest mb-2 uppercase">
                    Tier {entry.tier}
                  </span>
                  <div className="text-[9px] font-bold opacity-40">{formatDate(entry.added_at)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}