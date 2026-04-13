// src/components/common/SeverityBadge.jsx
import React from 'react';
import { getSeverityBadgeClass } from '../../utils/helpers';

export default function SeverityBadge({ severity }) {
  return (
    <span className={`badge ${getSeverityBadgeClass(severity)}`}>
      {severity}
    </span>
  );
}