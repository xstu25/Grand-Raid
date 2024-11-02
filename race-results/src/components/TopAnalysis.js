import React, { useState, useMemo } from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';

export default function TopAnalysis() {
  const [selectedRace, setSelectedRace] = useState("Toutes les courses");

  // Calculer les meilleurs grimpeurs
  const topClimbers = useMemo(() => {
    let climbers = [];
    Object.values(window.raceData).forEach(runner => {
      if ((selectedRace === "Toutes les courses" || runner.infos.race_name === selectedRace) && runner.checkpoints) {
        let totalGain = 0;
        let totalTime = 0;

        runner.checkpoints.forEach((cp, index) => {
          if (index > 0 && cp.elevation_gain > 100) {
            totalGain += cp.elevation_gain;
            // Calculer le temps en heures
            try {
              const time1 = new Date(`2000/01/01 ${runner.checkpoints[index-1].race_time}`);
              const time2 = new Date(`2000/01/01 ${cp.race_time}`);
              totalTime += (time2 - time1) / 3600000; // Convertir en heures
            } catch (e) {}
          }
        });

        if (totalGain > 0 && totalTime > 0) {
          climbers.push({
            bib: runner.infos.bib_number,
            name: runner.infos.name,
            race: runner.infos.race_name,
            gain: totalGain,
            speed: totalGain / totalTime,
            time: totalTime
          });
        }
      }
    });

    return climbers.sort((a, b) => b.speed - a.speed).slice(0, 20);
  }, [selectedRace]);

  // Calculer les meilleures progressions
  const topProgressions = useMemo(() => {
    let progressions = [];
    Object.values(window.raceData).forEach(runner => {
      if ((selectedRace === "Toutes les courses" || runner.infos.race_name === selectedRace) && runner.checkpoints) {
        const checkpoints = runner.checkpoints;
        if (checkpoints.length >= 2) {
          let firstRank = null;
          let lastRank = null;

          for (let cp of checkpoints) {
            if (cp.rank) {
              const rank = parseInt(cp.rank);
              if (!firstRank) firstRank = rank;
              lastRank = rank;
            }
          }

          if (firstRank && lastRank) {
            progressions.push({
              bib: runner.infos.bib_number,
              name: runner.infos.name,
              race: runner.infos.race_name,
              start: firstRank,
              end: lastRank,
              progress: firstRank - lastRank
            });
          }
        }
      }
    });

    return progressions.sort((a, b) => b.progress - a.progress).slice(0, 20);
  }, [selectedRace]);

  return (
    <div className="p-8 max-w-[1600px] mx-auto">
      <h1 className="text-2xl font-bold mb-6">Top Analyses</h1>

      {/* Sélecteur de course */}
      <select
        className="mb-8 border rounded-lg px-4 py-2"
        value={selectedRace}
        onChange={(e) => setSelectedRace(e.target.value)}
      >
        <option value="Toutes les courses">Toutes les courses</option>
        <option value="Diagonale des Fous">Diagonale des Fous</option>
        <option value="Trail de Bourbon">Trail de Bourbon</option>
        <option value="Mascareignes">Mascareignes</option>
        <option value="Métiss Trail">Métiss Trail</option>
      </select>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Top Grimpeurs */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-4">Top 20 Grimpeurs</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-2 text-left">Rang</th>
                  <th className="px-4 py-2 text-left">Coureur</th>
                  <th className="px-4 py-2 text-left">Course</th>
                  <th className="px-4 py-2 text-left">D+</th>
                  <th className="px-4 py-2 text-left">Vitesse ascension</th>
                </tr>
              </thead>
              <tbody>
                {topClimbers.map((climber, index) => (
                  <tr key={climber.bib} className="border-t">
                    <td className="px-4 py-2">{index + 1}</td>
                    <td className="px-4 py-2">{climber.name}</td>
                    <td className="px-4 py-2">{climber.race}</td>
                    <td className="px-4 py-2">{climber.gain}m</td>
                    <td className="px-4 py-2">{Math.round(climber.speed)}m/h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Meilleures progressions */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-4">Top 20 Progressions</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-2 text-left">Rang</th>
                  <th className="px-4 py-2 text-left">Coureur</th>
                  <th className="px-4 py-2 text-left">Course</th>
                  <th className="px-4 py-2 text-left">Départ</th>
                  <th className="px-4 py-2 text-left">Arrivée</th>
                  <th className="px-4 py-2 text-left">Progression</th>
                </tr>
              </thead>
              <tbody>
                {topProgressions.map((progress, index) => (
                  <tr key={progress.bib} className="border-t">
                    <td className="px-4 py-2">{index + 1}</td>
                    <td className="px-4 py-2">{progress.name}</td>
                    <td className="px-4 py-2">{progress.race}</td>
                    <td className="px-4 py-2">{progress.start}</td>
                    <td className="px-4 py-2">{progress.end}</td>
                    <td className="px-4 py-2 flex items-center">
                      <ArrowUp className="h-4 w-4 text-green-500 mr-1" />
                      {progress.progress}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
