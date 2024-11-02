import React, { useState, useMemo } from 'react';
import { Search } from 'lucide-react';

const raceData = {
  "Diagonale des Fous": "GRR",
  "Trail de Bourbon": "TDB",
  "Mascareignes": "MAS",
  "Métiss Trail": "MTR"
};

export default function RaceDashboard() {
  const [filters, setFilters] = useState({
    race: "Toutes les courses",
    state: "Tous les états",
    category: "Toutes les catégories"
  });
  const [searchTerm, setSearchTerm] = useState("");

  // Extraire les données uniques pour les filtres
  const filterOptions = useMemo(() => {
    const races = new Set(["Toutes les courses"]);
    const states = new Set(["Tous les états"]);
    const categories = new Set(["Toutes les catégories"]);
    
    Object.values(window.raceData).forEach(runner => {
      if (runner.infos) {
        races.add(runner.infos.race_name);
        states.add(runner.infos.state);
        categories.add(runner.infos.category);
      }
    });

    return {
      races: Array.from(races),
      states: Array.from(states),
      categories: Array.from(categories)
    };
  }, []);

  // Filtrer les données
  const filteredData = useMemo(() => {
    return Object.entries(window.raceData)
      .filter(([_, runner]) => {
        const matchesRace = filters.race === "Toutes les courses" || runner.infos.race_name === filters.race;
        const matchesState = filters.state === "Tous les états" || runner.infos.state === filters.state;
        const matchesCategory = filters.category === "Toutes les catégories" || runner.infos.category === filters.category;
        const matchesSearch = searchTerm === "" || 
          runner.infos.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          runner.infos.bib_number.toString().includes(searchTerm);
        
        return matchesRace && matchesState && matchesCategory && matchesSearch;
      });
  }, [filters, searchTerm]);

  return (
    <div className="p-8 max-w-[1600px] mx-auto">
      <h1 className="text-2xl font-bold mb-6">Résultats de courses</h1>
      
      {/* Filtres et recherche */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher par nom ou dossard..."
              className="w-full pl-10 pr-4 py-2 border rounded-lg"
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
        
        {/* Filtres déroulants */}
        {["race", "state", "category"].map((filterType) => (
          <select
            key={filterType}
            className="border rounded-lg px-4 py-2"
            value={filters[filterType]}
            onChange={(e) => setFilters({...filters, [filterType]: e.target.value})}
          >
            {filterOptions[filterType + "s"].map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        ))}
      </div>

      {/* Tableau des résultats */}
      <div className="overflow-x-auto shadow-sm rounded-lg">
        <table className="min-w-full table-auto">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-3 text-left">Dossard</th>
              <th className="px-4 py-3 text-left">Course</th>
              <th className="px-4 py-3 text-left">Nom</th>
              <th className="px-4 py-3 text-left">Catégorie</th>
              <th className="px-4 py-3 text-left">État</th>
              <th className="px-4 py-3 text-left">Temps</th>
              <th className="px-4 py-3 text-left">Class. Général</th>
              <th className="px-4 py-3 text-left">Dernier point</th>
            </tr>
          </thead>
          <tbody>
            {filteredData.map(([bib, runner]) => (
              <tr key={bib} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3">{runner.infos.bib_number}</td>
                <td className="px-4 py-3">{runner.infos.race_name}</td>
                <td className="px-4 py-3">{runner.infos.name}</td>
                <td className="px-4 py-3">{runner.infos.category}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-sm ${
                    runner.infos.state === "Finisher" ? "bg-green-100 text-green-800" :
                    runner.infos.state === "Abandon" ? "bg-red-100 text-red-800" :
                    runner.infos.state === "Non partant" ? "bg-gray-100 text-gray-800" :
                    "bg-yellow-100 text-yellow-800"
                  }`}>
                    {runner.infos.state}
                  </span>
                </td>
                <td className="px-4 py-3">{runner.infos.finish_time}</td>
                <td className="px-4 py-3">{runner.infos.overall_rank}</td>
                <td className="px-4 py-3">{runner.infos.last_checkpoint}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
