// RunnerDetails.js
import React from 'react';
import { useParams } from 'react-router-dom';

export function RunnerDetails() {
    const { bib } = useParams();
    const runner = window.raceData[bib];

    if (!runner) {
        return <div className="p-8">Coureur non trouvé</div>;
    }

    const { infos, checkpoints } = runner;

    return (
        <div className="p-8 max-w-[1600px] mx-auto">
            {/* En-tête avec les informations du coureur */}
            <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
                <h1 className="text-2xl font-bold mb-4">{infos.name}</h1>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                        <span className="text-gray-600">Dossard:</span>
                        <span className="ml-2 font-semibold">{infos.bib_number}</span>
                    </div>
                    <div>
                        <span className="text-gray-600">Course:</span>
                        <span className="ml-2 font-semibold">{infos.race_name}</span>
                    </div>
                    <div>
                        <span className="text-gray-600">Catégorie:</span>
                        <span className="ml-2 font-semibold">{infos.category}</span>
                    </div>
                    <div>
                        <span className="text-gray-600">État:</span>
                        <span className={`ml-2 px-2 py-1 rounded-full text-sm ${
                            infos.state === "Finisher" ? "bg-green-100 text-green-800" :
                            infos.state === "Abandon" ? "bg-red-100 text-red-800" :
                            "bg-gray-100 text-gray-800"
                        }`}>
                            {infos.state}
                        </span>
                    </div>
                    <div>
                        <span className="text-gray-600">Temps:</span>
                        <span className="ml-2 font-semibold">{infos.finish_time}</span>
                    </div>
                    <div>
                        <span className="text-gray-600">Class. Général:</span>
                        <span className="ml-2 font-semibold">{infos.overall_rank}</span>
                    </div>
                    <div>
                        <span className="text-gray-600">Class. Catégorie:</span>
                        <span className="ml-2 font-semibold">{infos.category_rank}</span>
                    </div>
                </div>
            </div>

            {/* Tableau des points de passage */}
            <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-xl font-semibold mb-4">Points de passage</h2>
                <div className="overflow-x-auto">
                    <table className="min-w-full">
                        <thead>
                            <tr className="bg-gray-50">
                                <th className="px-4 py-2 text-left">Point</th>
                                <th className="px-4 py-2 text-left">KM</th>
                                <th className="px-4 py-2 text-left">Heure</th>
                                <th className="px-4 py-2 text-left">Temps course</th>
                                <th className="px-4 py-2 text-left">Classement</th>
                                <th className="px-4 py-2 text-left">D+</th>
                                <th className="px-4 py-2 text-left">D-</th>
                                <th className="px-4 py-2 text-left">Vitesse</th>
                            </tr>
                        </thead>
                        <tbody>
                            {checkpoints.map((cp, index) => (
                                <tr key={index} className="border-t">
                                    <td className="px-4 py-2">{cp.point}</td>
                                    <td className="px-4 py-2">{cp.kilometer}</td>
                                    <td className="px-4 py-2">{cp.passage_time}</td>
                                    <td className="px-4 py-2">{cp.race_time}</td>
                                    <td className="px-4 py-2">
                                        {cp.rank}
                                        {cp.rank_evolution && (
                                            <span className={`ml-2 ${
                                                cp.rank_evolution > 0 ? "text-green-600" : 
                                                cp.rank_evolution < 0 ? "text-red-600" : ""
                                            }`}>
                                                {cp.rank_evolution > 0 ? `+${cp.rank_evolution}` : cp.rank_evolution}
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-4 py-2">{cp.elevation_gain}m</td>
                                    <td className="px-4 py-2">{cp.elevation_loss}m</td>
                                    <td className="px-4 py-2">{cp.speed}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
