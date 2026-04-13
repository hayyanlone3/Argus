// src/components/whitelist/TierSelector.jsx
import React from 'react';

export default function TierSelector({ value, onChange }) {
  const tiers = [
    {
      tier: 1,
      name: 'Tier 1: Path Only',
      desc: 'Path-only matching (lowest false positives)',
      color: 'border-green-500',
    },
    {
      tier: 2,
      name: 'Tier 2: Path + Hash',
      desc: 'Path AND hash match required',
      color: 'border-blue-500',
    },
    {
      tier: 3,
      name: 'Tier 3: Hash Only',
      desc: 'Hash-only matching (file moved)',
      color: 'border-purple-500',
    },
  ];

  return (
    <div className="space-y-3">
      <label className="form-label">Whitelist Tier</label>
      {tiers.map((tier) => (
        <label
          key={tier.tier}
          className={`border-2 rounded-lg p-3 cursor-pointer transition-all ${
            value === tier.tier ? tier.color + ' bg-gray-50' : 'border-gray-300'
          }`}
        >
          <input
            type="radio"
            value={tier.tier}
            checked={value === tier.tier}
            onChange={(e) => onChange(parseInt(e.target.value))}
            className="mr-2"
          />
          <strong>{tier.name}</strong>
          <p className="text-xs text-gray-600 ml-6">{tier.desc}</p>
        </label>
      ))}
    </div>
  );
}