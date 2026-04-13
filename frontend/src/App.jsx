import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import IncidentDetail from './pages/IncidentDetail';
import Layer0Dashboard from './pages/Layer0Dashboard';
import Layer1Dashboard from './pages/Layer1Dashboard';
import Layer2Dashboard from './pages/Layer2Dashboard';
import Layer3Dashboard from './pages/Layer3Dashboard';
import Layer4Dashboard from './pages/Layer4Dashboard';
import Layer5Dashboard from './pages/Layer5Dashboard';

function App() {
  return (
    <Router>
      <MainLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/incident/:sessionId" element={<IncidentDetail />} />
          <Route path="/layer0" element={<Layer0Dashboard />} />
          <Route path="/layer1" element={<Layer1Dashboard />} />
          <Route path="/layer2" element={<Layer2Dashboard />} />
          <Route path="/layer3" element={<Layer3Dashboard />} />
          <Route path="/layer4" element={<Layer4Dashboard />} />
          <Route path="/layer5" element={<Layer5Dashboard />} />
        </Routes>
      </MainLayout>
    </Router>
  );
}

export default App;