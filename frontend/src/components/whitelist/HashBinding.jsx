// src/components/whitelist/HashBinding.jsx
import React from 'react';
import { validateHash } from '../../utils/validators';

export default function HashBinding({ value, onChange, tier }) {
  const isRequired = tier === 2 || tier === 3;
  const isValid = !value || validateHash(value);

  return (
    <div className="form-group">
      <label className="form-label">
        SHA256 Hash {isRequired && <span className="text-critical">*</span>}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`form-input ${!isValid ? 'border-critical' : ''}`}
        placeholder="64-character SHA256 hash"
        required={isRequired}
      />
      {value && !isValid && (
        <p className="text-critical text-xs mt-1">Invalid SHA256 hash format</p>
      )}
      <p className="text-gray-600 text-xs mt-1">
        {tier === 1 && '(Optional for Tier 1)'}
        {tier === 2 && '(Required for Tier 2 - path + hash binding)'}
        {tier === 3 && '(Required for Tier 3 - hash-only matching)'}
      </p>
    </div>
  );
}