// App.js
(function() {
    const { HashRouter, Routes, Route, Link } = ReactRouterDOM;

    function App() {
        return (
            <HashRouter>
                <div className="min-h-screen bg-gray-50">
                    <nav className="bg-white shadow-sm">
                        <div className="max-w-7xl mx-auto px-4">
                            <div className="flex justify-between h-16">
                                <div className="flex">
                                    <div className="flex space-x-8">
                                        <Link
                                            to="/"
                                            className="inline-flex items-center px-1 pt-1 text-gray-900"
                                        >
                                            Résultats
                                        </Link>
                                        <Link
                                            to="/analyses"
                                            className="inline-flex items-center px-1 pt-1 text-gray-900"
                                        >
                                            Analyses
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        </div>
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

    // Exposez le composant App en tant que variable globale
    window.App = App;
})();
