// src/components/common/Sidebar.jsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Shield, 
  Network, 
  Activity, 
  Waypoints, 
  Zap, 
  BrainCircuit,
  Eye
} from 'lucide-react';

export default function Sidebar() {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  // Icons meticulously chosen to match the exact function of each layer
  const navItems = [
    { path: '/', label: 'Overview', icon: LayoutDashboard },
    { path: '/layer0', label: 'Layer 0: Bouncer', icon: Shield },         
    { path: '/layer1', label: 'Layer 1: Graph', icon: Network }, 
    { path: '/layer2', label: 'Layer 2: Scoring', icon: Activity },        
    { path: '/layer3', label: 'Layer 3: Correlator', icon: Waypoints },
    { path: '/layer4', label: 'Layer 4: Response', icon: Zap },
    { path: '/layer5', label: 'Layer 5: Learning', icon: BrainCircuit },   
  ];

  return (
    <aside className="w-72 bg-slate-900 min-h-screen flex flex-col border-r border-slate-800 transition-all font-sans z-10">
      
      {/* Header / Logo Area */}
      <div className="h-20 flex items-center px-6 border-b border-slate-800">
        <div className="flex items-center gap-3">
          
          <div className="flex flex-col justify-center">
            <span className="text-xl font-black text-white tracking-widest leading-none mb-1">ARGUS</span>
            <span className="text-[9px] font-bold text-slate-400 tracking-widest uppercase leading-none">Security Platform</span>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-1.5">
        {navItems.map((item) => {
          const active = isActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`group flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 ${
                active
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
              }`}
            >
              <item.icon 
                className={`w-5 h-5 transition-colors ${
                  active ? 'text-white' : 'text-slate-500 group-hover:text-slate-300'
                }`} 
              />
              <span className={`text-sm tracking-wide ${active ? 'font-semibold' : 'font-medium'}`}>
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>

    </aside>
  );
}