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

        # Ajout du dictionnaire de correspondance des courses
        self.race_names = {
            "MAS": "Mascareignes",
            "GRR": "Diagonale des Fous",
            "TDB": "Trail de Bourbon",
            "MTR": "Métiss Trail",
            "ZEM": "Zembrocal"
        }

        print("Installation du ChromeDriver...")
        self.service = Service(ChromeDriverManager().install())
        self.driver = None
        self.all_data = {}
        self.load_data()

    def get_race_from_url(self, driver):
        """Récupère le code de la course depuis l'URL"""
        try:
            # Attendre que l'URL soit mise à jour avec le raceId avec un timeout plus court
            time.sleep(2)
            current_url = driver.current_url
            print(f"URL courante: {current_url}")

            # Chercher le paramètre raceId
            match = re.search(r'raceId=(\w+)', current_url)
            if match:
                race_code = match.group(1)
                race_name = self.race_names.get(race_code, "Course inconnue")
                print(f"Course trouvée: {race_name} ({race_code})")
                return race_name
            else:
                # Si pas de raceId dans l'URL, on peut essayer de déduire la course
                # depuis les informations de la page
                try:
                    race_info = driver.find_element(By.CLASS_NAME, "mui-oah8u0").text
                    for code, name in self.race_names.items():
                        if name.lower() in race_info.lower():
                            return name
                except:
                    pass
                print("Code course non trouvé dans l'URL")
                return "Course inconnue"
        except Exception as e:
            print(f"Erreur lors de la récupération du nom de la course: {e}")
            return "Course inconnue"

    def load_data(self):
        try:
            if os.path.exists('race_data.json'):
                with open('race_data.json', 'r', encoding='utf-8') as f:
                    self.all_data = json.load(f)
                print(f"Données chargées pour {len(self.all_data)} coureurs")
        except Exception as e:
            print(f"Erreur lors du chargement des données: {e}")
            self.all_data = {}

    def save_data(self):
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

    def extract_numeric_value(self, text):
        """Extrait la valeur numérique d'une chaîne de caractères"""
        if not text:
            return 0
        match = re.search(r'(-?\d+(?:\.\d+)?)', text.replace(',', '.'))
        return float(match.group(1)) if match else 0

    def extract_rank_info(self, element):
        """Extrait le classement et l'évolution du classement"""
        try:
            rank_text = element.find_element(By.CLASS_NAME, "mui-n2g1ua").text
            rank = int(rank_text)

            # Tenter d'extraire l'évolution du classement
            try:
                evolution_element = element.find_element(By.CLASS_NAME, "mui-1duggqj")
                evolution_text = evolution_element.text
                evolution = int(re.findall(r'[-+]?\d+', evolution_text)[0])
            except:
                evolution = 0

            return rank, evolution
        except:
            return None, None

    def get_checkpoint_data(self, driver):
        """Extraire les données des points de passage pour un coureur"""
        try:
            checkpoints = []
            rows = driver.find_elements(By.CLASS_NAME, "MuiTableRow-root")

            for row in rows:
                try:
                    cells = row.find_elements(By.CLASS_NAME, "MuiTableCell-root")
                    if len(cells) < 7:
                        continue

                    # Extraction du nom du point de passage
                    try:
                        point_name = row.find_element(By.CLASS_NAME, "mui-1v8uc0v").text.strip()
                    except:
                        continue

                    # Extraction du kilomètre
                    try:
                        km_element = row.find_elements(By.CLASS_NAME, "mui-o6szkf")[0]
                        kilometer = self.extract_numeric_value(km_element.text)
                    except:
                        kilometer = 0

                    # Extraction du temps de passage
                    try:
                        passage_time = row.find_element(By.CLASS_NAME, "mui-1g6ia2u").text.strip()
                    except:
                        passage_time = "N/A"

                    # Extraction du temps de course
                    try:
                        race_time = row.find_element(By.CLASS_NAME, "mui-193t7sq").text.strip()
                    except:
                        race_time = "N/A"

                    # Modification de l'extraction de la vitesse
                    try:
                        speed_cells = row.find_elements(By.CLASS_NAME, "mui-193t7sq")
                        speed = "N/A"
                        for cell in speed_cells:
                            cell_text = cell.text.strip()
                            if 'km/h' in cell_text:  # Vérifie si c'est bien une vitesse
                                speed = cell_text
                                break

                        # Récupération de la vitesse effort
                        effort_containers = row.find_elements(By.CLASS_NAME, "mui-1jkxyqi")
                        effort_speed = "N/A"
                        for container in effort_containers:
                            if "Vitesse effort" in container.text:
                                effort_speed_element = container.find_element(By.CLASS_NAME, "mui-vm42pa")
                                effort_speed = effort_speed_element.text.strip()
                                break
                    except Exception as e:
                        print(f"Erreur lors de l'extraction de la vitesse: {e}")
                        speed = "N/A"
                        effort_speed = "N/A"

                    # Extraction du dénivelé positif et négatif
                    try:
                        elevation_cells = row.find_elements(By.CLASS_NAME, "mui-vm42pa")
                        if len(elevation_cells) >= 2:
                            d_plus_text = elevation_cells[-2].text
                            d_minus_text = elevation_cells[-1].text

                            # Extraction des valeurs numériques sans les signes + ou -
                            d_plus = int(re.search(r'\d+', d_plus_text).group()) if re.search(r'\d+',
                                                                                              d_plus_text) else 0
                            d_minus = int(re.search(r'\d+', d_minus_text).group()) if re.search(r'\d+',
                                                                                                d_minus_text) else 0
                        else:
                            d_plus = 0
                            d_minus = 0
                    except:
                        d_plus = 0
                        d_minus = 0

                    # Extraction du classement et de son évolution
                    try:
                        rank_cells = row.find_elements(By.CLASS_NAME, "mui-ct9q29")
                        rank = None
                        evolution = None

                        for cell in rank_cells:
                            try:
                                # Extraction du classement
                                rank = cell.find_element(By.CLASS_NAME, "mui-n2g1ua").text.strip()

                                # Tentative d'extraction de l'évolution (positive ou négative)
                                try:
                                    evolution_element = None
                                    for class_name in ["mui-2e3q6l", "mui-1duggqj"]:
                                        try:
                                            evolution_element = cell.find_element(By.CLASS_NAME, class_name)
                                            break
                                        except:
                                            continue

                                    if evolution_element:
                                        evolution_text = evolution_element.text.strip()
                                        evolution_match = re.search(r'[+-]?\d+',
                                                                    evolution_text.replace('(', '').replace(')',
                                                                                                            ''))
                                        if evolution_match:
                                            evolution = int(evolution_match.group())
                                except:
                                    evolution = None
                                break
                            except:
                                continue
                    except Exception as e:
                        print(f"Erreur lors de l'extraction du classement: {e}")
                        rank = None
                        evolution = None

                    checkpoint = {
                        'point': point_name,
                        'kilometer': kilometer,
                        'passage_time': passage_time,
                        'race_time': race_time,
                        'speed': speed,
                        'effort_speed': effort_speed,
                        'elevation_gain': d_plus,
                        'elevation_loss': d_minus,
                        'rank': rank,
                        'rank_evolution': evolution
                    }
                    checkpoints.append(checkpoint)

                except Exception as e:
                    print(f"Erreur lors du traitement d'un point de passage: {e}")
                    continue

            return checkpoints

        except Exception as e:
            print(f"Erreur lors de l'extraction des points de passage: {e}")
            traceback.print_exc()
            return []

    def normalize_text(self, text):
        """Normalise le texte pour la comparaison (supprime accents et met en minuscules)"""
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                       if unicodedata.category(c) != 'Mn')

    def get_runner_data(self, bib_number):
        """Récupère les données complètes d'un coureur"""
        bib_str = str(bib_number)
        print(f"\nTraitement du dossard {bib_number}")

        # Vérifier si les données sont en cache
        if bib_str in self.all_data:
            print(f"Données trouvées en cache pour le dossard {bib_number}")
            return self.all_data[bib_str]

        print(f"Récupération des données en ligne pour le dossard {bib_number}")
        try:
            # Initialisation du driver et chargement de la page
            driver = self.initialize_driver()
            url = f"https://grandraid-reunion-oxybol.v3.livetrail.net/fr/2024/runners/{bib_number}"
            driver.get(url)
            time.sleep(1)

            # Initialisation des variables par défaut
            name = "Inconnu"
            category = "Inconnue"
            avg_speed = "N/A"
            state = "Inconnu"
            finish_time = "-"
            rankings = {"Général": "", "Sexe": "", "Catégorie": ""}

            # Récupération du nom de la course
            race_name = self.get_race_from_url(driver)

            # Récupération du nom du coureur
            try:
                name_element = driver.find_element(By.CLASS_NAME, "mui-oah8u0")
                name = name_element.text.strip()
            except:
                print(f"Erreur lors de la récupération du nom pour le dossard {bib_number}")

            # Récupération de la catégorie
            try:
                category_element = driver.find_element(By.CLASS_NAME, "mui-1vu7he5")
                category = category_element.text.strip()
            except:
                print(f"Erreur lors de la récupération de la catégorie pour le dossard {bib_number}")

            # Récupération de l'état et du temps
            try:
                print("Recherche de l'état du coureur...")
                raw_state = "Inconnu"

                # Chercher Finisher
                try:
                    state_container = driver.find_element(By.CLASS_NAME, "mui-w9oezj")
                    state_element = state_container.find_element(By.CSS_SELECTOR, "p.MuiTypography-noWrap")
                    raw_state = state_element.text.strip()
                    print(f"État trouvé dans mui-w9oezj: {raw_state}")
                except:
                    # Chercher Abandon ou Non partant
                    try:
                        state_container = driver.find_element(By.CLASS_NAME, "mui-gzldy9")
                        try:
                            state_element = state_container.find_element(By.CLASS_NAME, "mui-1xavr8a")
                            raw_state = state_element.text.strip()
                            print(f"État trouvé dans mui-gzldy9 (abandon): {raw_state}")
                        except:
                            state_element = state_container.find_element(By.CLASS_NAME, "mui-evvpi6")
                            raw_state = state_element.text.strip()
                            print(f"État trouvé dans mui-gzldy9 (non partant): {raw_state}")
                    except:
                        print("Aucun état trouvé dans les conteneurs connus")

                print(f"État brut trouvé: {raw_state}")
                normalized_state = raw_state.upper()

                # Traitement des non partants
                if "NON PARTANT" in normalized_state:
                    runner_data = {
                        'infos': {
                            'bib_number': bib_number,
                            'race_name': race_name,
                            'name': name,
                            'category': category,
                            'state': "Non partant",
                            'finish_time': "-",
                            'overall_rank': "-",
                            'gender_rank': "-",
                            'category_rank': "-",
                            'average_speed': "-",
                            'last_checkpoint': "-",
                            'total_elevation_gain': 0,
                            'total_elevation_loss': 0
                        },
                        'checkpoints': []
                    }
                    self.all_data[bib_str] = runner_data
                    self.save_data()
                    return runner_data

                # Détermination de l'état et du temps pour les autres cas
                if "ABANDON" in normalized_state:
                    state = "Abandon"
                elif "FINISHER" in normalized_state:
                    state = "Finisher"
                else:
                    state = "En course"

                # Récupération du temps si disponible
                if state in ["Abandon", "Finisher"]:
                    try:
                        time_element = state_container.find_element(By.CLASS_NAME, "mui-1vazesu")
                        finish_time = time_element.text.strip()
                        if ':' in finish_time:
                            hours, minutes, _ = finish_time.split(':')
                            finish_time = f"{hours}h{minutes}"
                    except:
                        finish_time = "-"
                else:
                    finish_time = "En course"

                print(f"État normalisé: {state}")

                # Récupération de la vitesse moyenne si le coureur n'est pas non partant
                try:
                    print("\nDébut extraction vitesse moyenne...")
                    main_container = driver.find_element(By.CLASS_NAME, "mui-14iziq5")
                    print("Conteneur principal trouvé")

                    info_sections = main_container.find_elements(By.CLASS_NAME, "mui-157h3i3")
                    print(f"Nombre de sections info trouvées: {len(info_sections)}")

                    if len(info_sections) >= 2:
                        info_section = info_sections[1]
                        print("Section info de vitesse trouvée, recherche des éléments...")

                        for element in info_section.find_elements(By.CLASS_NAME, "mui-8v90jo"):
                            try:
                                label_container = element.find_element(By.CLASS_NAME, "mui-ct9q29")
                                label = label_container.find_element(By.CLASS_NAME, "mui-wenrje").text.strip()
                                print(f"Label trouvé: '{label}'")

                                if "VIT. MOY." in label.upper():
                                    print("Label de vitesse moyenne trouvé!")
                                    speed_value = element.find_elements(By.TAG_NAME, "p")[-1].text.strip()
                                    print(f"Valeur de vitesse trouvée: '{speed_value}'")
                                    avg_speed = speed_value
                                    break
                            except Exception as e:
                                print(f"Erreur lors de l'analyse d'un élément: {str(e)}")
                                continue
                except Exception as e:
                    print(f"Erreur lors de la récupération de la vitesse moyenne: {str(e)}")
                    avg_speed = "N/A"

                # Récupération des classements
                print("\nDébut récupération des classements")
                try:
                    print("Recherche des containers de classement...")
                    ranking_section = driver.find_element(By.CLASS_NAME, "mui-157h3i3")
                    rank_elements = ranking_section.find_elements(By.CLASS_NAME, "mui-4ae55t")
                    print(f"Nombre d'éléments de classement trouvés: {len(rank_elements)}")

                    for element in rank_elements:
                        try:
                            type_text = element.find_element(By.CLASS_NAME, "mui-280lq").text.strip().upper()
                            value_text = element.find_element(By.CLASS_NAME, "mui-17rj2i9").text.strip()
                            print(f"Trouvé: {type_text} = {value_text}")

                            if "GÉNÉRAL" in type_text or "GENERAL" in type_text:
                                rankings["Général"] = value_text
                            elif "SEXE" in type_text:
                                rankings["Sexe"] = value_text
                            elif "CATÉGORIE" in type_text or "CATEGORIE" in type_text:
                                rankings["Catégorie"] = value_text
                        except Exception as e:
                            print(f"Erreur lors de l'extraction d'un élément de classement: {str(e)}")

                    print("État final des classements:", rankings)
                except Exception as e:
                    print(f"Erreur lors de la récupération des classements: {str(e)}")

                # Récupération des points de passage
                checkpoints = self.get_checkpoint_data(driver)

                # Détermination du dernier point
                last_checkpoint = ""
                if checkpoints:
                    last_cp = checkpoints[-1]
                    last_checkpoint = last_cp['point']

                # Construction des données du coureur
                runner_data = {
                    'infos': {
                        'bib_number': bib_number,
                        'race_name': race_name,
                        'name': name,
                        'category': category,
                        'state': state,
                        'finish_time': finish_time,
                        'overall_rank': rankings['Général'],
                        'gender_rank': rankings['Sexe'],
                        'category_rank': rankings['Catégorie'],
                        'average_speed': avg_speed,
                        'last_checkpoint': last_checkpoint,
                        'total_elevation_gain': sum(cp['elevation_gain'] for cp in checkpoints) if checkpoints else 0,
                        'total_elevation_loss': sum(cp['elevation_loss'] for cp in checkpoints) if checkpoints else 0
                    },
                    'checkpoints': checkpoints
                }

                # Sauvegarde des données
                self.all_data[bib_str] = runner_data
                self.save_data()
                return runner_data

            except Exception as e:
                print(f"Erreur lors de la récupération de l'état: {str(e)}")
                state = "Inconnu"
                finish_time = "-"
                print("État inconnu assigné suite à une erreur")
                return None

        except Exception as e:
            print(f"Erreur générale pour le dossard {bib_number}: {str(e)}")
            traceback.print_exc()
            return None

class CheckpointWindow:
    def __init__(self, parent, bib_number, runner_data, checkpoint_data):
        self.window = ctk.CTkToplevel(parent)
        self.window.title(f"Détails du coureur {bib_number}")
        self.window.state('zoomed')  # Pour Windows

        # En-tête avec les informations du coureur
        header_frame = ctk.CTkFrame(self.window)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        # Diviser l'en-tête en deux colonnes
        left_info = ctk.CTkFrame(header_frame)
        left_info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        right_info = ctk.CTkFrame(header_frame)
        right_info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Informations coureur - Colonne gauche
        left_info_text = (
            f"Course: {runner_data['race_name']}\n"  # Ajout de la course
            f"Dossard: {bib_number}\n"
            f"Nom: {runner_data['name']}\n"
            f"Catégorie: {runner_data['category']}\n"
            f"État: {runner_data['state']}\n"
            f"Dernier point: {runner_data['last_checkpoint']}"
        )
        ctk.CTkLabel(left_info, text=left_info_text, justify="left").pack(padx=10, pady=10)

        # Informations coureur - Colonne droite
        right_info_text = (
            f"Classement général: {runner_data['overall_rank']}\n"
            f"Classement sexe: {runner_data['gender_rank']}\n"
            f"Classement catégorie: {runner_data['category_rank']}\n"
            f"Vitesse moyenne: {runner_data['average_speed']}\n"
            f"Dénivelé: {runner_data['total_elevation_gain']}m / {runner_data['total_elevation_loss']}m"
        )

        ctk.CTkLabel(right_info, text=right_info_text, justify="left").pack(padx=10, pady=10)

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

        # Tableau des points de passage
        columns = (
            "point", "kilometer", "passage_time", "race_time", "speed", "effort_speed",  # Ajout de effort_speed
            "elevation_gain", "elevation_loss", "rank", "rank_evolution"
        )

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Checkpoint.Treeview"
        )

        # Configuration des colonnes
        headers = {
            "point": "Point de passage",
            "kilometer": "KM",
            "passage_time": "Heure passage",
            "race_time": "Temps course",
            "speed": "Vitesse",
            "effort_speed": "Vitesse effort",
            "elevation_gain": "D+",
            "elevation_loss": "D-",
            "rank": "Class.",
            "rank_evolution": "Évolution"
        }

        widths = {
            "point": 250,
            "kilometer": 70,
            "passage_time": 120,
            "race_time": 120,
            "speed": 100,
            "effort_speed": 100,  # Ajout de la largeur pour effort_speed
            "elevation_gain": 80,
            "elevation_loss": 80,
            "rank": 80,
            "rank_evolution": 100
        }

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="center")

        # Remplir le tableau
        for checkpoint in checkpoint_data:
            elevation_gain = f"{checkpoint['elevation_gain']}m" if checkpoint['elevation_gain'] else "-"
            elevation_loss = f"{checkpoint['elevation_loss']}m" if checkpoint['elevation_loss'] else "-"

            rank_evolution = checkpoint['rank_evolution']
            if rank_evolution:
                if rank_evolution > 0:
                    evolution_text = f"+{rank_evolution}"
                else:
                    evolution_text = str(rank_evolution)
            else:
                evolution_text = "-"

            self.tree.insert('', 'end', values=(
                checkpoint['point'],
                f"{checkpoint['kilometer']:.1f}",
                checkpoint['passage_time'],
                checkpoint['race_time'],
                checkpoint['speed'],
                checkpoint['effort_speed'],
                elevation_gain,
                elevation_loss,
                checkpoint['rank'] if checkpoint['rank'] else "-",
                evolution_text
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
        # Maximiser la fenêtre
        self.root.state('zoomed')

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
        style.map("Treeview", background=[('selected', '#22559b')])

        self.scraper = RaceDataScraper()
        self.checkpoint_windows = {}
        self.create_widgets()
        self.load_cached_data()

    def create_widgets(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Frame de saisie
        input_frame = ctk.CTkFrame(self.main_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        ctk.CTkLabel(input_frame, text="Numéros de dossard (séparés par des virgules):").pack(side=tk.LEFT, padx=5)
        self.bib_entry = ctk.CTkEntry(input_frame, width=400)
        self.bib_entry.pack(side=tk.LEFT, padx=5)

        self.scan_button = ctk.CTkButton(input_frame, text="Scanner", command=self.start_scanning)
        self.scan_button.pack(side=tk.LEFT, padx=5)

        # Frame de progression
        progress_frame = ctk.CTkFrame(self.main_frame)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        self.progress_label = ctk.CTkLabel(progress_frame, text="")
        self.progress_label.pack(side=tk.LEFT, padx=5)

        # Configuration du tableau principal avec toutes les colonnes
        columns = (
            "race_name", "bib", "name", "category", "overall_rank", "gender_rank",  # Ajout de race_name
            "category_rank", "average_speed", "state", "last_checkpoint",
            "finish_time", "total_elevation_gain", "total_elevation_loss"
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
            "race_name": "Course",  # Ajout de l'en-tête pour la course
            "bib": "Dossard",
            "name": "Nom",
            "category": "Catégorie",
            "overall_rank": "Class. Général",
            "gender_rank": "Class. Sexe",
            "category_rank": "Class. Catégorie",
            "average_speed": "Vitesse moy.",
            "state": "État",
            "last_checkpoint": "Dernier Point",
            "finish_time": "Temps",
            "total_elevation_gain": "D+ Total",
            "total_elevation_loss": "D- Total"
        }

        widths = {
            "race_name": 150,  # Ajout de la largeur pour la colonne course
            "bib": 80,
            "name": 200,
            "category": 100,
            "overall_rank": 100,
            "gender_rank": 100,
            "category_rank": 120,
            "average_speed": 100,
            "state": 100,
            "last_checkpoint": 200,
            "finish_time": 100,
            "total_elevation_gain": 100,
            "total_elevation_loss": 100
        }

        for col in columns:
            self.tree.heading(
                col,
                text=headers[col],
                command=lambda c=col: self.treeview_sort_column(c, False)
            )
            self.tree.column(col, width=widths[col], anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind('<Double-1>', self.show_checkpoint_details)

        # Frame pour les filtres
        filter_frame = ctk.CTkFrame(self.main_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        ctk.CTkLabel(filter_frame, text="Filtres:").pack(side=tk.LEFT, padx=5)

        self.race_filter = ctk.CTkComboBox(filter_frame, values=["Toutes les courses"])
        self.race_filter.pack(side=tk.LEFT, padx=5)
        self.race_filter.bind('<<ComboboxSelected>>', self.apply_filters)

        self.state_filter = ctk.CTkComboBox(filter_frame, values=["Tous les états"])
        self.state_filter.pack(side=tk.LEFT, padx=5)
        self.state_filter.bind('<<ComboboxSelected>>', self.apply_filters)

        # Nouveau filtre pour les catégories
        self.category_filter = ctk.CTkComboBox(filter_frame, values=["Toutes les catégories"])
        self.category_filter.pack(side=tk.LEFT, padx=5)
        self.category_filter.bind('<<ComboboxSelected>>', self.apply_filters)

    def scanning_complete(self, scanned, cached):
        """Finalise le processus de scan"""
        self.scan_button.configure(state="normal")
        if scanned + cached > 0:
            self.progress_label.configure(
                text=f"Scan terminé ! ({cached} depuis le cache, {scanned} nouveaux scans)"
            )
        else:
            self.progress_label.configure(text="Scan terminé !")

    def show_checkpoint_details(self, event):
        """Affiche la fenêtre des détails pour un coureur"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.tree.item(item)['values']
        if not values:
            return

        bib_number = str(values[1])  # Le dossard est maintenant la deuxième colonne (index 1)

        if bib_number in self.scraper.all_data:
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

    def treeview_sort_column(self, col, reverse):
        """Trie le tableau selon une colonne"""
        try:
            # Récupérer toutes les données du tableau
            data = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]

            # Fonction pour extraire la valeur numérique d'une chaîne
            def extract_number(text):
                try:
                    # Enlever les unités (m, km/h, etc.) et convertir en nombre
                    return float(''.join(c for c in text if c.isdigit() or c in '.-'))
                except:
                    return text

            # Trier les données
            try:
                # Essayer de trier numériquement
                data.sort(key=lambda x: extract_number(x[0]) if x[0] else float('-inf'), reverse=reverse)
            except:
                # Si échec, trier alphabétiquement
                data.sort(reverse=reverse)

            # Réorganiser les items dans le tableau
            for idx, (val, item) in enumerate(data):
                self.tree.move(item, '', idx)

            # Inverser le sens de tri pour le prochain clic
            self.tree.heading(col, command=lambda: self.treeview_sort_column(col, not reverse))

        except Exception as e:
            print(f"Erreur lors du tri de la colonne {col}: {e}")


    def add_runner_to_tree(self, data):
        """Ajoute un coureur au tableau principal avec toutes les nouvelles données"""
        if data and 'infos' in data:
            info = data['infos']
            self.tree.insert('', 'end', values=(
                info['race_name'],  # Ajout du nom de la course
                info['bib_number'],
                info['name'],
                info['category'],
                info['overall_rank'],
                info['gender_rank'],
                info['category_rank'],
                info['average_speed'],
                info['state'],
                info['last_checkpoint'],
                info['finish_time'],
                f"{info['total_elevation_gain']}m",
                f"{info['total_elevation_loss']}m"
            ))

    def update_filters(self):
        """Mise à jour des listes de filtres incluant les catégories"""
        categories = set()
        states = set()
        races = set()

        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values:
                races.add(values[0])  # Course (index 0)
                categories.add(values[3])  # Catégorie (index 3)
                states.add(values[8])  # État (index 8)

        self.category_filter.configure(values=["Toutes les catégories"] + sorted(list(categories)))
        self.state_filter.configure(values=["Tous les états"] + sorted(list(states)))
        self.race_filter.configure(values=["Toutes les courses"] + sorted(list(races)))

    def apply_filters(self, event=None):
        """Application des filtres incluant le filtre de catégorie"""
        selected_category = self.category_filter.get()
        selected_state = self.state_filter.get()
        selected_race = self.race_filter.get()

        all_items = [(self.tree.item(item), item) for item in self.tree.get_children()]
        self.tree.delete(*self.tree.get_children())

        for item_data, item_id in all_items:
            values = item_data['values']
            show_item = True

            if selected_category != "Toutes les catégories" and values[3] != selected_category:
                show_item = False
            if selected_state != "Tous les états" and values[8] != selected_state:
                show_item = False
            if selected_race != "Toutes les courses" and values[0] != selected_race:
                show_item = False

            if show_item:
                self.tree.insert('', 'end', values=values)


    def load_cached_data(self):
        if self.scraper.all_data:
            cached_bibs = list(self.scraper.all_data.keys())
            print(f"Chargement automatique de {len(cached_bibs)} dossards")
            for bib in cached_bibs:
                data = self.scraper.all_data[bib]
                self.add_runner_to_tree(data)
            self.update_filters()
            self.progress_label.configure(text=f"{len(cached_bibs)} dossards chargés depuis le cache")

    def scan_bibs(self, bib_numbers):
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
        self.root.after(0, self.update_filters)

    def start_scanning(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        bib_text = self.bib_entry.get().strip()
        if not bib_text:
            messagebox.showwarning("Attention", "Veuillez entrer des numéros de dossard!")
            return

        try:
            bib_numbers = [int(x.strip()) for x in bib_text.split(',')]
        except ValueError:
            messagebox.showerror("Erreur", "Format de numéro de dossard invalide!")
            return

        self.scan_button.configure(state="disabled")
        thread = threading.Thread(target=self.scan_bibs, args=(bib_numbers,))
        thread.daemon = True
        thread.start()

    def run(self):
        self.root.mainloop()

    def __del__(self):
        if hasattr(self, 'scraper'):
            self.scraper.close_driver()


class TopAnalysisWindow:
    def __init__(self, parent, scraper, bibs):
        self.window = ctk.CTkToplevel(parent)
        self.window.title("TOP Analyses")
        self.window.geometry("1400x800")
        self.scraper = scraper
        self.bibs = bibs

        # Frame principal
        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Créer des onglets
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill=tk.BOTH, expand=True)

        # Ajouter les onglets
        self.tab_progress = self.tabview.add("Progression")
        self.tab_elevation = self.tabview.add("Dénivelés")
        self.tab_speed = self.tabview.add("Vitesses")

        # Remplir les onglets
        self.fill_progress_tab()
        self.fill_elevation_tab()
        self.fill_speed_tab()

    def create_table(self, parent, columns, headers, data, height=10):
        tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=height
        )

        for col in columns:
            tree.heading(col, text=headers[col])
            tree.column(col, width=100, anchor="center")

        for row in data:
            tree.insert("", "end", values=row)

        return tree

    def fill_progress_tab(self):
        frame = ctk.CTkFrame(self.tab_progress)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Meilleurs progressions
        progression_frame = ctk.CTkFrame(frame)
        progression_frame.pack(fill=tk.X, padx=5, pady=5)
        ctk.CTkLabel(progression_frame, text="Meilleures progressions", font=("Arial", 16, "bold")).pack(pady=5)

        # Calculer les progressions
        progressions = []
        for bib in self.bibs:
            if bib in self.scraper.all_data:
                data = self.scraper.all_data[bib]
                checkpoints = data['checkpoints']

                # Chercher la plus grande progression entre deux points
                max_progression = 0
                progression_points = ("", "")
                previous_rank = None

                for cp in checkpoints:
                    if cp['rank'] is not None:
                        if previous_rank is not None:
                            progression = previous_rank - cp['rank']
                            if progression > max_progression:
                                max_progression = progression
                                progression_points = (previous_point, cp['point'])
                        previous_rank = cp['rank']
                        previous_point = cp['point']

                if max_progression > 0:
                    progressions.append((
                        max_progression,
                        bib,
                        data['infos']['name'],
                        progression_points[0],
                        progression_points[1]
                    ))

        # Trier et afficher les meilleures progressions
        progressions.sort(reverse=True)
        columns = ["rank", "bib", "name", "from_point", "to_point", "places"]
        headers = {
            "rank": "Pos",
            "bib": "Dossard",
            "name": "Nom",
            "from_point": "De",
            "to_point": "À",
            "places": "Places gagnées"
        }

        data = [(i + 1, *prog[1:], f"+{prog[0]}") for i, prog in enumerate(progressions[:10])]
        tree = self.create_table(progression_frame, columns, headers, data)
        tree.pack(fill=tk.X, padx=5, pady=5)

    def fill_elevation_tab(self):
        frame = ctk.CTkFrame(self.tab_elevation)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Meilleurs grimpeurs (vitesse ascensionnelle)
        climbing_frame = ctk.CTkFrame(frame)
        climbing_frame.pack(fill=tk.X, padx=5, pady=5)
        ctk.CTkLabel(climbing_frame, text="Meilleurs grimpeurs", font=("Arial", 16, "bold")).pack(pady=5)

        climbers = []
        for bib in self.bibs:
            if bib in self.scraper.all_data:
                data = self.scraper.all_data[bib]
                checkpoints = data['checkpoints']

                # Calculer la vitesse ascensionnelle moyenne
                total_elevation = 0
                total_time = 0

                for i in range(len(checkpoints) - 1):
                    if checkpoints[i]['elevation_gain'] > 0:
                        try:
                            time1 = datetime.strptime(checkpoints[i]['race_time'], "%H:%M:%S")
                            time2 = datetime.strptime(checkpoints[i + 1]['race_time'], "%H:%M:%S")
                            segment_time = (time2 - time1).total_seconds() / 3600  # en heures
                            if segment_time > 0:
                                total_elevation += checkpoints[i]['elevation_gain']
                                total_time += segment_time
                        except:
                            continue

                if total_time > 0:
                    climbing_speed = total_elevation / total_time
                    climbers.append((
                        climbing_speed,
                        bib,
                        data['infos']['name'],
                        total_elevation,
                        f"{climbing_speed:.1f}"
                    ))

        # Trier et afficher les meilleurs grimpeurs
        climbers.sort(reverse=True)
        columns = ["rank", "bib", "name", "elevation", "speed"]
        headers = {
            "rank": "Pos",
            "bib": "Dossard",
            "name": "Nom",
            "elevation": "D+ Total",
            "speed": "Vitesse (m/h)"
        }

        data = [(i + 1, *climb[1:]) for i, climb in enumerate(climbers[:10])]
        tree = self.create_table(climbing_frame, columns, headers, data)
        tree.pack(fill=tk.X, padx=5, pady=5)

    def fill_speed_tab(self):
        frame = ctk.CTkFrame(self.tab_speed)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Plus grandes variations de vitesse
        speed_frame = ctk.CTkFrame(frame)
        speed_frame.pack(fill=tk.X, padx=5, pady=5)
        ctk.CTkLabel(speed_frame, text="Plus grandes variations de vitesse", font=("Arial", 16, "bold")).pack(pady=5)

        speed_variations = []
        for bib in self.bibs:
            if bib in self.scraper.all_data:
                data = self.scraper.all_data[bib]
                checkpoints = data['checkpoints']

                speeds = []
                for cp in checkpoints:
                    try:
                        speed = float(cp['speed'].replace('km/h', '').strip())
                        speeds.append(speed)
                    except:
                        continue

                if speeds:
                    min_speed = min(speeds)
                    max_speed = max(speeds)
                    variation = max_speed - min_speed
                    avg_speed = sum(speeds) / len(speeds)

                    speed_variations.append((
                        variation,
                        bib,
                        data['infos']['name'],
                        f"{min_speed:.1f}",
                        f"{max_speed:.1f}",
                        f"{avg_speed:.1f}"
                    ))

        # Trier et afficher les variations de vitesse
        speed_variations.sort(reverse=True)
        columns = ["rank", "bib", "name", "min_speed", "max_speed", "avg_speed", "variation"]
        headers = {
            "rank": "Pos",
            "bib": "Dossard",
            "name": "Nom",
            "min_speed": "Min (km/h)",
            "max_speed": "Max (km/h)",
            "avg_speed": "Moy (km/h)",
            "variation": "Variation (km/h)"
        }

        data = [(i + 1, *var[1:], f"{var[0]:.1f}") for i, var in enumerate(speed_variations[:10])]
        tree = self.create_table(speed_frame, columns, headers, data)
        tree.pack(fill=tk.X, padx=5, pady=5)

        # Meilleure régularité
        regularity_frame = ctk.CTkFrame(frame)
        regularity_frame.pack(fill=tk.X, padx=5, pady=15)
        ctk.CTkLabel(regularity_frame, text="Coureurs les plus réguliers", font=("Arial", 16, "bold")).pack(pady=5)

        regularities = []
        for bib in self.bibs:
            if bib in self.scraper.all_data:
                data = self.scraper.all_data[bib]
                checkpoints = data['checkpoints']

                speeds = []
                for cp in checkpoints:
                    try:
                        speed = float(cp['speed'].replace('km/h', '').strip())
                        speeds.append(speed)
                    except:
                        continue

                if len(speeds) > 2:
                    avg_speed = sum(speeds) / len(speeds)
                    variations = [abs(s - avg_speed) for s in speeds]
                    avg_variation = sum(variations) / len(variations)
                    variation_percentage = (avg_variation / avg_speed) * 100

                    regularities.append((
                        variation_percentage,
                        bib,
                        data['infos']['name'],
                        f"{avg_speed:.1f}",
                        f"{variation_percentage:.1f}"
                    ))

        # Trier et afficher les coureurs les plus réguliers
        regularities.sort()  # Plus petite variation en premier
        columns = ["rank", "bib", "name", "avg_speed", "variation"]
        headers = {
            "rank": "Pos",
            "bib": "Dossard",
            "name": "Nom",
            "avg_speed": "Vitesse moy (km/h)",
            "variation": "Variation (%)"
        }

        data = [(i + 1, *reg[1:]) for i, reg in enumerate(regularities[:10])]
        tree = self.create_table(regularity_frame, columns, headers, data)
        tree.pack(fill=tk.X, padx=5, pady=5)


if __name__ == "__main__":
    app = RaceTrackerApp()
    app.run()