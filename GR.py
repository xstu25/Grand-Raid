import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import threading
from datetime import datetime
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import traceback
import json
import re
import os


class RaceDataScraper:
    def __init__(self):
        print("Initialisation du scraper...")
        self.chrome_options = Options()
        self.chrome_options.add_argument('--start-maximized')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')

        print("Installation du ChromeDriver...")
        self.service = Service(ChromeDriverManager().install())
        self.driver = None
        self.all_data = {}  # Stockage unique de toutes les données
        self.load_data()

    def load_data(self):
        """Charger les données depuis le fichier JSON"""
        try:
            if os.path.exists('race_data.json'):
                with open('race_data.json', 'r', encoding='utf-8') as f:
                    self.all_data = json.load(f)
                print(f"Données chargées pour {len(self.all_data)} coureurs")
        except Exception as e:
            print(f"Erreur lors du chargement des données: {e}")
            self.all_data = {}

    def save_data(self):
        """Sauvegarder les données dans le fichier JSON"""
        try:
            with open('race_data.json', 'w', encoding='utf-8') as f:
                json.dump(self.all_data, f, ensure_ascii=False, indent=4)
            print("Données sauvegardées avec succès")
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des données: {e}")

    def initialize_driver(self):
        if not self.driver:
            self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        return self.driver

    def close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def get_checkpoint_data(self, bib_number):
        """Extraire les données des points de passage pour un coureur"""
        try:
            # Attendre que la page soit complètement chargée
            try:
                # Attendre explicitement que tous les éléments de navigation soient présents
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "vues"))
                )

                # Attendre explicitement que tous les onglets soient présents
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "color"))
                )

                time.sleep(2)  # Attente supplémentaire pour s'assurer du chargement complet

                # Trouver tous les liens avec la classe 'color'
                links = self.driver.find_elements(By.CLASS_NAME, "color")
                tableau_link = None
                for link in links:
                    if link.text.strip() == "TABLEAU":
                        tableau_link = link
                        break

                if tableau_link:
                    # Utiliser JavaScript pour cliquer sur le lien
                    self.driver.execute_script("arguments[0].click();", tableau_link)
                    time.sleep(2)
                else:
                    print("Lien TABLEAU non trouvé")

            except Exception as e:
                print(f"Erreur lors du clic sur l'onglet TABLEAU: {e}")
                traceback.print_exc()

            # Attendre et trouver directement toutes les lignes du tableau
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "tr"))
            )

            checkpoints = []
            for row in rows[3:]:  # On commence déjà à l'index 3
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        # Vérifier si la ligne contient "Class." ou si toutes les valeurs sont "N/A"
                        if any("Class." in cell.text for cell in cells) or all("N/A" in cell.text for cell in cells):
                            continue

                        # Initialiser les valeurs par défaut
                        altitude = "N/A"
                        point_name = "N/A"
                        temps = "N/A"
                        vitesse = "N/A"
                        classement = "N/A"
                        passage = "N/A"

                        # Extraire l'altitude et le nom du point depuis la première cellule
                        try:
                            altitude_elements = cells[0].find_elements(By.CLASS_NAME, "rig")
                            if altitude_elements:
                                altitude_text = altitude_elements[0].text.strip()
                                altitude = altitude_text.replace(" ", "").replace("m", "")
                        except Exception:
                            pass

                        try:
                            point_name_elements = cells[0].find_elements(By.TAG_NAME, "a")
                            if point_name_elements:
                                point_name = point_name_elements[0].text.strip()
                        except Exception:
                            pass

                        # Extraire la vitesse
                        try:
                            vitesse_elements = cells[1].find_elements(By.CLASS_NAME, "rig")
                            if vitesse_elements:
                                vitesse = vitesse_elements[0].text.strip()
                        except Exception:
                            pass

                        # Extraire le classement
                        try:
                            classement_elements = cells[2].find_elements(By.CLASS_NAME, "rig")
                            if classement_elements:
                                classement = classement_elements[0].text.strip()
                        except Exception:
                            pass

                        # Extraire l'heure de passage
                        try:
                            passage = cells[3].text.strip()
                        except Exception:
                            pass

                        # Extraire le temps
                        try:
                            temps_elements = cells[4].find_elements(By.CLASS_NAME, "rig")
                            if temps_elements:
                                temps = temps_elements[0].text.strip()
                        except Exception:
                            pass

                        # Vérifier si nous avons au moins quelques données valides
                        if not all(val == "N/A" for val in
                                   [altitude, point_name, temps, vitesse, classement, passage]):
                            checkpoint = {
                                'temps': temps,
                                'altitude': altitude,
                                'point': point_name,
                                'vitesse': vitesse,
                                'classement': classement,
                                'passage': passage
                            }
                            checkpoints.append(checkpoint)

                except Exception as e:
                    print(f"Erreur lors du traitement d'une ligne: {e}")
                    continue

            return checkpoints

        except Exception as e:
            print(f"Erreur lors de l'extraction des points de passage: {e}")
            traceback.print_exc()
            return []

    def get_runner_data(self, bib_number):
        """Récupérer les données d'un coureur (depuis le cache ou le web)"""
        bib_str = str(bib_number)
        print(f"\nTraitement du dossard {bib_number}")

        # Vérifier si les données existent déjà et sont complètes
        if bib_str in self.all_data:
            print(f"Données trouvées en cache pour le dossard {bib_number}")
            return self.all_data[bib_str]

        print(f"Récupération des données en ligne pour le dossard {bib_number}")
        try:
            driver = self.initialize_driver()
            url = f"https://grandraid-reunion-oxybol.livetrail.run/coureur.php?rech={bib_number}"
            driver.get(url)

            # Attendre plus longtemps pour le chargement complet
            time.sleep(4)

            # Attendre explicitement que la page soit chargée
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "vues"))
            )

            # Extraction du nom
            try:
                first_name = driver.find_element(By.CLASS_NAME, "pnom").text.strip()
                last_name = driver.find_element(By.CLASS_NAME, "nom").text.strip()
                name = f"{first_name} {last_name}"
            except Exception as e:
                print(f"Erreur extraction nom: {e}")
                name = "Inconnu"

            # Extraction du nom de la course
            try:
                cat_div = driver.find_element(By.CLASS_NAME, "cat").text
                match = re.search(r'Dossard \d+\s+(.*?)\s*-', cat_div)
                race_name = match.group(1).strip() if match else ""
            except Exception as e:
                print(f"Erreur extraction course: {e}")
                race_name = ""

            # Initialisation des variables
            state = ""
            overall_rank = ""
            gender_rank = ""
            category = ""
            category_rank = ""
            last_checkpoint = ""
            finish_time = ""

            # Extraction des données de la table resume
            try:
                resume_table = driver.find_element(By.CLASS_NAME, "resume")
                cells = resume_table.find_elements(By.TAG_NAME, "td")

                for cell in cells:
                    try:
                        label_element = cell.find_element(By.TAG_NAME, "label")
                        label = label_element.text.strip()
                        value = cell.text.split('\n')[-1].strip()

                        if label == "Etat":
                            state = value
                            if state == "Arrêté":
                                state = "Abandon"
                        elif label == "Class.":
                            overall_rank = value
                        elif label in ["Class. H", "Class. F"]:
                            gender_rank = value
                        elif label.startswith("Class.") and len(label) > 8:
                            category = label.replace('Class. ', '')
                            category_rank = value
                        elif label == "Dernier point":
                            parts = value.split()
                            if len(parts) >= 4:
                                last_checkpoint = ' '.join(parts[2:])
                            else:
                                last_checkpoint = value
                        elif label == "Temps de course":
                            if state == "Contact":
                                finish_time = "Contact"
                            else:
                                try:
                                    time_parts = value.split(':')
                                    finish_time = f"{time_parts[0]}H{time_parts[1]}"
                                except:
                                    finish_time = value

                    except Exception as e:
                        print(f"Erreur traitement cellule: {e}")
                        continue

            except Exception as e:
                print(f"Erreur table resume: {e}")

            # Extraction des points de passage et construction des données
            runner_data = {
                'infos': {
                    'race_name': race_name,
                    'bib_number': bib_number,
                    'name': name,
                    'category': category,
                    'category_rank': category_rank,
                    'gender_rank': gender_rank,
                    'state': state,
                    'last_checkpoint': last_checkpoint if state == "Abandon" else "",
                    'finish_time': finish_time if finish_time != "Contact" else "Contact",
                    'overall_rank': overall_rank if state != "Contact" else ""
                },
                'checkpoints': self.get_checkpoint_data(bib_number)
            }

            # Stocker les données dans le dictionnaire global
            self.all_data[bib_str] = runner_data
            self.save_data()

            return runner_data

        except Exception as e:
            print(f"Erreur générale pour le dossard {bib_number}: {e}")
            traceback.print_exc()
            return None


class CheckpointWindow:
    def __init__(self, parent, bib_number, runner_data, checkpoint_data):
        self.window = ctk.CTkToplevel(parent)
        self.window.title(f"Détails du coureur {bib_number}")
        self.window.geometry("1200x800")

        # En-tête avec les informations du coureur
        header_frame = ctk.CTkFrame(self.window)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        # Informations coureur
        info_text = (
            f"Dossard: {bib_number}\n"
            f"Nom: {runner_data['name']}\n"
            f"Course: {runner_data['race_name']}\n"
            f"État: {runner_data['state']}\n"
            f"Classement général: {runner_data['overall_rank']}\n"
            f"Classement catégorie ({runner_data['category']}): {runner_data['category_rank']}\n"
            f"Classement sexe: {runner_data['gender_rank']}\n"
            f"Temps: {runner_data['finish_time']}"
        )
        ctk.CTkLabel(header_frame, text=info_text, justify="left").pack(padx=10, pady=10)

        # Configuration du style du tableau
        style = ttk.Style()
        style.configure(
            "Checkpoint.Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b"
        )
        style.configure(
            "Checkpoint.Treeview.Heading",
            background="#2b2b2b",
            foreground="white"
        )

        # Tableau des points de passage
        tree_frame = ttk.Frame(self.window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Modification de l'ordre des colonnes pour mettre le temps en premier
        columns = ("temps", "altitude", "point", "vitesse", "classement", "passage")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Checkpoint.Treeview"
        )

        # Configuration des colonnes
        headers = {
            "temps": "Temps de course",
            "altitude": "Altitude (m)",
            "point": "Point de passage",
            "vitesse": "Vitesse",
            "classement": "Classement",
            "passage": "Heure de passage"
        }

        widths = {
            "temps": 150,
            "altitude": 100,
            "point": 250,
            "vitesse": 100,
            "classement": 100,
            "passage": 150
        }

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col])

        # Remplir le tableau
        for checkpoint in checkpoint_data:
            self.tree.insert('', 'end', values=(
                checkpoint['temps'],
                checkpoint['altitude'],
                checkpoint['point'],
                checkpoint['vitesse'],
                checkpoint['classement'],
                checkpoint['passage']
            ))

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)


class RaceTrackerApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Suivi Grand Raid")
        self.root.geometry("1400x800")

        # Configuration du style
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="white",
            rowheight=25,
            fieldbackground="#2b2b2b"
        )
        style.configure(
            "Treeview.Heading",
            background="#2b2b2b",
            foreground="white",
            relief="flat"
        )
        style.map(
            "Treeview",
            background=[('selected', '#22559b')]
        )

        self.create_widgets()
        self.scraper = RaceDataScraper()
        self.checkpoint_windows = {}



    def create_widgets(self):
        # Frame principal
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Frame de saisie
        input_frame = ctk.CTkFrame(self.main_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        ctk.CTkLabel(
            input_frame,
            text="Numéros de dossard (séparés par des virgules):"
        ).pack(side=tk.LEFT, padx=5)

        self.bib_entry = ctk.CTkEntry(input_frame, width=400)
        self.bib_entry.pack(side=tk.LEFT, padx=5)

        self.scan_button = ctk.CTkButton(
            input_frame,
            text="Scanner",
            command=self.start_scanning
        )
        self.scan_button.pack(side=tk.LEFT, padx=5)

        # Frame de progression
        progress_frame = ctk.CTkFrame(self.main_frame)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_label = ctk.CTkLabel(progress_frame, text="")
        self.progress_label.pack(side=tk.LEFT, padx=5)

        # Configuration du tableau
        columns = (
            "race_name", "bib", "name", "category", "category_rank",
            "gender_rank", "state", "last_checkpoint", "finish_time", "overall_rank"
        )

        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings"
        )

        # Configuration des colonnes
        headers = {
            "race_name": "Course",
            "bib": "Dossard",
            "name": "Nom",
            "category": "Catégorie",
            "category_rank": "Class. Cat.",
            "gender_rank": "Class. Sexe",
            "state": "État",
            "last_checkpoint": "Dernier Point",
            "finish_time": "Temps",
            "overall_rank": "Class. Général"
        }

        widths = {
            "race_name": 150,
            "bib": 70,
            "name": 200,
            "category": 100,
            "category_rank": 100,
            "gender_rank": 100,
            "state": 100,
            "last_checkpoint": 200,
            "finish_time": 100,
            "overall_rank": 120
        }

        for col in columns:
            self.tree.heading(
                col,
                text=headers[col],
                command=lambda c=col: self.treeview_sort_column(c, False),
                anchor="center"
            )
            self.tree.column(col, width=widths[col], anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Ajouter le gestionnaire d'événements pour le double-clic
        self.tree.bind('<Double-1>', self.show_checkpoint_details)

        # Ajouter un frame pour les filtres
        filter_frame = ctk.CTkFrame(self.main_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        # Filtres
        ctk.CTkLabel(filter_frame, text="Filtres:").pack(side=tk.LEFT, padx=5)

        # Filtre par course
        self.race_filter = ctk.CTkComboBox(filter_frame, values=["Toutes les courses"])
        self.race_filter.pack(side=tk.LEFT, padx=5)
        self.race_filter.bind('<<ComboboxSelected>>', self.apply_filters)

        # Filtre par état
        self.state_filter = ctk.CTkComboBox(filter_frame, values=["Tous les états"])
        self.state_filter.pack(side=tk.LEFT, padx=5)
        self.state_filter.bind('<<ComboboxSelected>>', self.apply_filters)

        # Ajouter le bouton TOP dans le filter_frame
        self.top_button = ctk.CTkButton(
            filter_frame,
            text="TOP Analyses",
            command=self.show_top_analysis
        )
        self.top_button.pack(side=tk.RIGHT, padx=5)

    def show_top_analysis(self):
        """Affiche la fenêtre d'analyse TOP"""
        TopAnalysisWindow(self.root, self.scraper)



    def update_filters(self):
        """Mettre à jour les listes de filtres"""
        races = set()
        states = set()

        for values in [self.tree.item(item)['values'] for item in self.tree.get_children()]:
            if values:
                races.add(values[0])  # Course
                states.add(values[6])  # État

        self.race_filter.configure(values=["Toutes les courses"] + sorted(list(races)))
        self.state_filter.configure(values=["Tous les états"] + sorted(list(states)))

    def apply_filters(self, event=None):
        """Appliquer les filtres sélectionnés"""
        selected_race = self.race_filter.get()
        selected_state = self.state_filter.get()

        # Stocker tous les items dans une liste temporaire
        all_items = [(self.tree.item(item), item) for item in self.tree.get_children()]

        # Effacer tous les items de l'arbre
        self.tree.delete(*self.tree.get_children())

        # Réinsérer uniquement les items qui correspondent aux critères
        for item_data, item_id in all_items:
            values = item_data['values']

            # Vérifier si l'item correspond aux filtres sélectionnés
            show_item = True

            # Vérifier le filtre de course
            if selected_race != "Toutes les courses" and values[0] != selected_race:
                show_item = False

            # Vérifier le filtre d'état
            if selected_state != "Tous les états" and values[6] != selected_state:
                show_item = False

            # Réinsérer l'item s'il correspond aux critères
            if show_item:
                self.tree.insert('', 'end', values=values)

    def show_checkpoint_details(self, event):
        """Affiche la fenêtre des détails pour un coureur"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.tree.item(item)['values']
        if not values:
            return

        bib_number = str(values[1])  # Conversion en string pour la cohérence

        if bib_number in self.scraper.all_data and self.scraper.all_data[bib_number]['checkpoints']:
            # Créer une nouvelle fenêtre ou mettre à jour l'existante
            if bib_number in self.checkpoint_windows:
                self.checkpoint_windows[bib_number].window.destroy()

            # Récupérer les données du coureur
            runner_data = self.scraper.all_data[bib_number]['infos']

            # Créer la nouvelle fenêtre
            self.checkpoint_windows[bib_number] = CheckpointWindow(
                self.root,
                bib_number,
                runner_data,
                self.scraper.all_data[bib_number]['checkpoints']
            )
        else:
            messagebox.showwarning(
                "Données non disponibles",
                f"Pas de données de points de passage pour le dossard {bib_number}"
            )

    def add_runner_to_tree(self, data):
        """Ajoute un coureur au tableau principal"""
        if data and 'infos' in data:
            info = data['infos']
            self.tree.insert('', 'end', values=(
                info['race_name'],
                info['bib_number'],
                info['name'],
                info['category'],
                info['category_rank'],
                info['gender_rank'],
                info['state'],
                info['last_checkpoint'],
                info['finish_time'],
                info['overall_rank']
            ))



    def scan_bibs(self, bib_numbers):
        """Scan les dossards et met à jour le tableau"""
        total = len(bib_numbers)
        scanned = 0
        cached = 0

        for i, bib in enumerate(bib_numbers, 1):
            bib_str = str(bib)
            if bib_str in self.scraper.all_data:
                self.progress_label.configure(
                    text=f"Récupération du cache pour le dossard {bib} ({i}/{total})..."
                )
                data = self.scraper.all_data[bib_str]
                cached += 1
            else:
                self.progress_label.configure(
                    text=f"Scan du dossard {bib} ({i}/{total})..."
                )
                data = self.scraper.get_runner_data(bib)
                scanned += 1

            if data:
                self.root.after(0, self.add_runner_to_tree, data)
            time.sleep(1)

        self.root.after(0, lambda: self.scanning_complete(scanned, cached))
        self.root.after(0, self.update_filters)  # Mettre à jour les filtres après le scan

    def start_scanning(self):
        """Démarre le processus de scan des dossards"""
        # Nettoyer le tableau
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Récupérer et valider les numéros de dossard
        bib_text = self.bib_entry.get().strip()
        if not bib_text:
            messagebox.showwarning(
                "Attention",
                "Veuillez entrer des numéros de dossard !"
            )
            return

        try:
            bib_numbers = [int(x.strip()) for x in bib_text.split(',')]
        except ValueError:
            messagebox.showerror(
                "Erreur",
                "Format de numéro de dossard invalide !"
            )
            return

        self.scan_button.configure(state="disabled")
        thread = threading.Thread(target=self.scan_bibs, args=(bib_numbers,))
        thread.daemon = True
        thread.start()




    def treeview_sort_column(self, col, reverse):
        """Trie le tableau selon une colonne"""
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            # Essayer de trier numériquement
            l.sort(key=lambda t: float(t[0]) if t[0] != "" else float('inf'), reverse=reverse)
        except ValueError:
            # Si échec, trier alphabétiquement
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(
            col,
            command=lambda: self.treeview_sort_column(col, not reverse)
        )

    def run(self):
        """Lance l'application"""
        self.root.mainloop()

    def scanning_complete(self, scanned, cached):
        """Finalise le processus de scan"""
        self.scan_button.configure(state="normal")
        if scanned + cached > 0:
            self.progress_label.configure(
                text=f"Scan terminé ! ({cached} depuis le cache, {scanned} nouveaux scans)"
            )
        else:
            self.progress_label.configure(text="Scan terminé !")

    def __del__(self):
        """Nettoyage à la fermeture"""
        if hasattr(self, 'scraper'):
            self.scraper.close_driver()


class TopAnalysisWindow:
    def __init__(self, parent, scraper):
        self.window = ctk.CTkToplevel(parent)
        self.window.title("TOP Analyses")
        self.window.geometry("1400x800")
        self.scraper = scraper

        # Frame principal avec défilement
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Création des onglets
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill=tk.BOTH, expand=True)

        # Ajout des onglets
        self.tab_general = self.tabview.add("Général")
        self.tab_segments = self.tabview.add("Segments")
        self.tab_special = self.tabview.add("Spécial")

        # Remplissage des onglets
        self.fill_general_tab()
        self.fill_segments_tab()
        self.fill_special_tab()

    def create_top_list(self, parent, title, data, headers):
        """Crée une liste TOP avec un titre"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill=tk.X, padx=5, pady=5)

        # Titre
        ctk.CTkLabel(frame, text=title, font=("Arial", 16, "bold")).pack(pady=5)

        # Création du tableau
        tree = ttk.Treeview(frame, columns=headers.keys(), show="headings", height=7)
        for key, text in headers.items():
            tree.heading(key, text=text)
            tree.column(key, width=100, anchor="center")

        # Ajout des données
        for row in data:
            tree.insert("", "end", values=row)

        tree.pack(fill=tk.X, padx=5, pady=5)
        return frame

    def fill_general_tab(self):
        """Remplit l'onglet général avec les tops par course"""
        data = self.analyze_race_data()

        for race_name, race_data in data.items():
            # TOP 7 Hommes
            headers_h = {"rank": "Rang", "bib": "Dossard", "name": "Nom", "time": "Temps"}
            self.create_top_list(
                self.tab_general,
                f"TOP 7 Hommes - {race_name}",
                race_data['top_men'],
                headers_h
            )

            # TOP 7 Femmes
            headers_f = {"rank": "Rang", "bib": "Dossard", "name": "Nom", "time": "Temps"}
            self.create_top_list(
                self.tab_general,
                f"TOP 7 Femmes - {race_name}",
                race_data['top_women'],
                headers_f
            )

    def fill_segments_tab(self):
        """Remplit l'onglet segments avec les analyses de portions"""
        segments_data = self.analyze_segments()

        for segment_name, segment_data in segments_data.items():
            # Plus rapides
            headers = {
                "rank": "Rang",
                "bib": "Dossard",
                "name": "Nom",
                "speed": "Vitesse",
                "time": "Temps"
            }
            self.create_top_list(
                self.tab_segments,
                f"TOP 7 Plus Rapides - {segment_name}",
                segment_data['fastest'],
                headers
            )

            # Plus lents
            self.create_top_list(
                self.tab_segments,
                f"TOP 7 Plus Lents - {segment_name}",
                segment_data['slowest'],
                headers
            )

    def fill_special_tab(self):
        """Remplit l'onglet spécial avec des statistiques particulières"""
        special_data = self.analyze_special_stats()

        # Meilleurs grimpeurs
        headers_climb = {
            "rank": "Rang",
            "bib": "Dossard",
            "name": "Nom",
            "speed": "Vitesse",
            "elevation": "D+"
        }
        self.create_top_list(
            self.tab_special,
            "TOP 7 Grimpeurs",
            special_data['best_climbers'],
            headers_climb
        )

        # Meilleurs descendeurs
        self.create_top_list(
            self.tab_special,
            "TOP 7 Descendeurs",
            special_data['best_descenders'],
            headers_climb
        )

        # Plus réguliers
        headers_regular = {
            "rank": "Rang",
            "bib": "Dossard",
            "name": "Nom",
            "var": "Variation"
        }
        self.create_top_list(
            self.tab_special,
            "TOP 7 Plus Réguliers",
            special_data['most_regular'],
            headers_regular
        )

    def analyze_race_data(self):
        """Analyse les données par course"""
        races = {}

        for bib, data in self.scraper.all_data.items():
            info = data['infos']
            race_name = info['race_name']

            if race_name not in races:
                races[race_name] = {
                    'top_men': [],
                    'top_women': []
                }

            # Vérifier si le coureur a un classement et un temps
            if info['overall_rank'] and info['finish_time']:
                runner = (
                    int(info['overall_rank']),
                    bib,
                    info['name'],
                    info['finish_time']
                )

                # Déterminer le genre basé sur la catégorie
                if "F" in info['category']:
                    races[race_name]['top_women'].append(runner)
                else:
                    races[race_name]['top_men'].append(runner)

        # Trier et limiter à 7
        for race in races.values():
            race['top_men'] = sorted(race['top_men'])[:7]
            race['top_women'] = sorted(race['top_women'])[:7]

        return races

    def analyze_segments(self):
        """Analyse les segments entre les points de passage"""
        segments = {}

        for bib, data in self.scraper.all_data.items():
            checkpoints = data['checkpoints']

            # Analyser chaque paire de points de passage consécutifs
            for i in range(len(checkpoints) - 1):
                cp1 = checkpoints[i]
                cp2 = checkpoints[i + 1]

                segment_name = f"{cp1['point']} → {cp2['point']}"

                if segment_name not in segments:
                    segments[segment_name] = {
                        'fastest': [],
                        'slowest': []
                    }

                try:
                    # Calculer le temps entre les points
                    time1 = datetime.strptime(cp1['temps'], "%H:%M:%S")
                    time2 = datetime.strptime(cp2['temps'], "%H:%M:%S")
                    delta = time2 - time1

                    # Calculer la vitesse moyenne
                    speed = cp2['vitesse']

                    runner = (
                        int(data['infos']['overall_rank']),
                        bib,
                        data['infos']['name'],
                        speed,
                        str(delta)
                    )

                    segments[segment_name]['fastest'].append(runner)
                    segments[segment_name]['slowest'].append(
                        (delta.total_seconds(), bib, data['infos']['name'], speed, str(delta))
                    )
                except:
                    continue

        # Trier et limiter à 7
        for segment in segments.values():
            segment['fastest'] = sorted(segment['fastest'], key=lambda x: x[3], reverse=True)[:7]
            segment['slowest'] = sorted(segment['slowest'])[:7]

        return segments

    def analyze_special_stats(self):
        """Analyse des statistiques spéciales"""
        special_stats = {
            'best_climbers': [],
            'best_descenders': [],
            'most_regular': []
        }

        for bib, data in self.scraper.all_data.items():
            checkpoints = data['checkpoints']
            speeds = []
            climbs = []
            descents = []

            for i in range(len(checkpoints) - 1):
                cp1 = checkpoints[i]
                cp2 = checkpoints[i + 1]

                try:
                    alt1 = float(cp1['altitude'])
                    alt2 = float(cp2['altitude'])
                    speed = float(cp2['vitesse'].replace('km/h', ''))

                    speeds.append(speed)

                    if alt2 > alt1:
                        climbs.append((speed, alt2 - alt1))
                    else:
                        descents.append((speed, alt1 - alt2))
                except:
                    continue

            if speeds:
                # Calcul des moyennes
                avg_climb = sum(s for s, _ in climbs) / len(climbs) if climbs else 0
                avg_descent = sum(s for s, _ in descents) / len(descents) if descents else 0
                speed_variation = max(speeds) - min(speeds) if speeds else float('inf')

                # Ajouter aux statistiques
                special_stats['best_climbers'].append(
                    (avg_climb, bib, data['infos']['name'], f"{avg_climb:.1f}", sum(d for _, d in climbs))
                )
                special_stats['best_descenders'].append(
                    (avg_descent, bib, data['infos']['name'], f"{avg_descent:.1f}", sum(d for _, d in descents))
                )
                special_stats['most_regular'].append(
                    (speed_variation, bib, data['infos']['name'], f"{speed_variation:.1f}")
                )

        # Trier et limiter à 7
        special_stats['best_climbers'] = sorted(
            special_stats['best_climbers'],
            key=lambda x: x[0],
            reverse=True
        )[:7]
        special_stats['best_descenders'] = sorted(
            special_stats['best_descenders'],
            key=lambda x: x[0],
            reverse=True
        )[:7]
        special_stats['most_regular'] = sorted(special_stats['most_regular'])[:7]

        return special_stats

if __name__ == "__main__":
    app = RaceTrackerApp()
    app.run()