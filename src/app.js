import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import RaceDashboard from './components/RaceDashboard';
import TopAnalysis from './components/TopAnalysis';
import RunnerDetails from './components/RunnerDetails';

function App() {
    return (
        <HashRouter>
            <div className="min-h-screen bg-gray-50">
                <nav className="bg-white shadow-sm">
                    {/* ... */}
                </nav>

                <main>
                    <Routes>
                        <Route path="/" element={<RaceDashboard />} />
                        <Route path="/analyses" element={<TopAnalysis />} />
                        <Route path="/runner/:bib" element={<RunnerDetails />} />
                    </Routes>
                </main>
            </div>
        </HashRouter>
    );
}

export default App;
