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
            time.sleep(1)
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

                    # Extraction du temps de passage (première cellule mui-1g6ia2u)
                    try:
                        passage_time = row.find_element(By.CLASS_NAME, "mui-1g6ia2u").text.strip()
                    except:
                        passage_time = "N/A"

                    # Extraction du temps de course (modification)
                    try:
                        # Trouver toutes les cellules qui pourraient contenir le temps de course
                        time_cells = cells[4].find_elements(By.CLASS_NAME, "mui-193t7sq")
                        # Prendre le premier élément qui est directement dans la cellule
                        # (pas dans une structure imbriquée avec temps de repos)
                        race_time = None
                        for time_cell in time_cells:
                            # Vérifier si l'élément parent n'a pas la classe mui-1jkxyqi
                            # (qui est utilisée pour le temps de repos)
                            parent = time_cell.find_element(By.XPATH, "..")
                            if "mui-1jkxyqi" not in parent.get_attribute("class"):
                                race_time = time_cell.text.strip()
                                break

                        if not race_time:
                            race_time = "N/A"
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
                                                                    evolution_text.replace('(', '').replace(')', ''))
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

        # Ajout du bouton TOP Analyses
        self.analysis_button = ctk.CTkButton(
            input_frame,
            text="TOP Analyses",
            command=self.show_top_analysis
        )
        self.analysis_button.pack(side=tk.LEFT, padx=5)

    def show_top_analysis(self):
        # Récupérer tous les dossards actuellement affichés dans le tableau
        bibs = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values:
                bibs.append(values[1])  # L'index 1 correspond à la colonne du dossard

        if not bibs:
            messagebox.showwarning(
                "Attention",
                "Aucun coureur n'est actuellement affiché dans le tableau!"
            )
            return

        # Créer la fenêtre d'analyse
        TopAnalysisWindow(self.root, self.scraper, bibs)

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
        """Trie le tableau selon une colonne avec gestion spéciale des classements"""
        try:
            # Récupérer toutes les données du tableau
            data = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]

            # Fonction pour extraire la valeur numérique d'une chaîne
            def extract_number(text):
                try:
                    # Si c'est un classement (colonnes spécifiques)
                    if col in ["overall_rank", "gender_rank", "category_rank"]:
                        # Extraire uniquement les chiffres, ignorer les autres caractères
                        return int(''.join(filter(str.isdigit, text))) if text.strip() else float('inf')

                    # Pour les autres colonnes numériques
                    if any(c.isdigit() for c in text):
                        # Enlever les unités (m, km/h, etc.) et convertir en nombre
                        num = ''.join(c for c in text if c.isdigit() or c in '.-')
                        return float(num) if num else float('inf')
                    return text  # Retourner le texte tel quel si pas de nombre
                except:
                    return text  # En cas d'erreur, retourner le texte original

            # Trier les données
            try:
                # Essayer de trier numériquement
                data.sort(
                    key=lambda x: (
                        float('inf') if extract_number(x[0]) == '' else extract_number(x[0])
                        if isinstance(extract_number(x[0]), (int, float))
                        else x[0].lower()
                    ),
                    reverse=reverse
                )
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

        # Frame principal avec défilement
        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Frame pour les filtres en haut
        self.filter_frame = ctk.CTkFrame(self.main_frame)
        self.filter_frame.pack(fill=tk.X, padx=5, pady=5)

        # Sélecteur de course
        ctk.CTkLabel(self.filter_frame, text="Course:").pack(side=tk.LEFT, padx=5)
        self.race_values = self.get_unique_races()
        self.race_selector = ctk.CTkComboBox(
            self.filter_frame,
            values=self.race_values,
            command=self.on_race_selected
        )
        self.race_selector.pack(side=tk.LEFT, padx=5)
        self.race_selector.set("Toutes les courses")

        # Sélecteur de section (visible uniquement pour l'onglet sections)
        self.section_frame = ctk.CTkFrame(self.filter_frame)
        self.section_selector = None

        # Créer les onglets
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill=tk.BOTH, expand=True, pady=10)

        # Ajouter les onglets
        self.tab_progress = self.tabview.add("Progression")
        self.tab_elevation = self.tabview.add("Dénivelés")
        self.tab_speed = self.tabview.add("Vitesses")
        self.tab_sections = self.tabview.add("Sections")

        # Créer les sous-onglets pour chaque catégorie principale
        self.create_progression_subtabs()
        self.create_elevation_subtabs()
        self.create_speed_subtabs()
        self.create_sections_subtabs()

        # Initialiser l'affichage
        self.update_displays()

    def get_unique_races(self):
        races = set()
        races.add("Toutes les courses")
        for bib in self.bibs:
            if str(bib) in self.scraper.all_data:
                race_name = self.scraper.all_data[str(bib)]['infos']['race_name']
                races.add(race_name)
        return sorted(list(races))

    def create_progression_subtabs(self):
        self.progress_tabs = ctk.CTkTabview(self.tab_progress)
        self.progress_tabs.pack(fill=tk.BOTH, expand=True)

        self.progress_global = self.progress_tabs.add("Progression globale")
        self.progress_sections = self.progress_tabs.add("Entre points")

        # Ajouter ScrollArea pour chaque sous-onglet
        self.progress_global_scroll = ctk.CTkScrollableFrame(self.progress_global)
        self.progress_global_scroll.pack(fill=tk.BOTH, expand=True)

        self.progress_sections_scroll = ctk.CTkScrollableFrame(self.progress_sections)
        self.progress_sections_scroll.pack(fill=tk.BOTH, expand=True)

    def create_elevation_subtabs(self):
        self.elevation_tabs = ctk.CTkTabview(self.tab_elevation)
        self.elevation_tabs.pack(fill=tk.BOTH, expand=True)

        self.elevation_climbers = self.elevation_tabs.add("Grimpeurs")
        self.elevation_descenders = self.elevation_tabs.add("Descendeurs")

        self.climbers_scroll = ctk.CTkScrollableFrame(self.elevation_climbers)
        self.climbers_scroll.pack(fill=tk.BOTH, expand=True)

        self.descenders_scroll = ctk.CTkScrollableFrame(self.elevation_descenders)
        self.descenders_scroll.pack(fill=tk.BOTH, expand=True)

    def create_speed_subtabs(self):
        self.speed_tabs = ctk.CTkTabview(self.tab_speed)
        self.speed_tabs.pack(fill=tk.BOTH, expand=True)

        self.speed_avg = self.speed_tabs.add("Vitesse moyenne")
        self.speed_effort = self.speed_tabs.add("Vitesse effort")
        self.speed_sections = self.speed_tabs.add("Entre points")

        self.speed_avg_scroll = ctk.CTkScrollableFrame(self.speed_avg)
        self.speed_avg_scroll.pack(fill=tk.BOTH, expand=True)

        self.speed_effort_scroll = ctk.CTkScrollableFrame(self.speed_effort)
        self.speed_effort_scroll.pack(fill=tk.BOTH, expand=True)

        self.speed_sections_scroll = ctk.CTkScrollableFrame(self.speed_sections)
        self.speed_sections_scroll.pack(fill=tk.BOTH, expand=True)

    def create_sections_subtabs(self):
        self.sections_frame = ctk.CTkFrame(self.tab_sections)
        self.sections_frame.pack(fill=tk.BOTH, expand=True)

        # Ajouter le sélecteur de sections
        self.section_frame.pack(side=tk.LEFT, padx=20)
        ctk.CTkLabel(self.section_frame, text="Section:").pack(side=tk.LEFT, padx=5)
        self.section_selector = ctk.CTkComboBox(
            self.section_frame,
            values=[],
            command=self.on_section_selected
        )
        self.section_selector.pack(side=tk.LEFT, padx=5)

        # Frame pour les résultats de section avec scroll
        self.section_results_scroll = ctk.CTkScrollableFrame(self.sections_frame)
        self.section_results_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def on_race_selected(self, selection):
        # Mettre à jour les sections disponibles
        self.update_section_selector(selection)
        # Mettre à jour tous les affichages
        self.update_displays()

    def on_section_selected(self, selection):
        # Mettre à jour l'affichage des performances de la section
        self.update_section_display()

    def update_section_selector(self, race):
        """Mettre à jour la liste des sections avec les dénivelés corrects"""
        sections = {}  # Utiliser un dictionnaire pour stocker les infos de section
        for bib in self.bibs:
            if str(bib) in self.scraper.all_data:
                data = self.scraper.all_data[str(bib)]
                if race == "Toutes les courses" or data['infos']['race_name'] == race:
                    checkpoints = data['checkpoints']
                    for i in range(len(checkpoints) - 1):
                        section_name = f"{checkpoints[i]['point']} → {checkpoints[i + 1]['point']}"
                        sections[section_name] = {
                            'distance': checkpoints[i + 1]['kilometer'] - checkpoints[i]['kilometer'],
                            'elevation_gain': checkpoints[i + 1]['elevation_gain'],
                            # Prendre le dénivelé du point d'arrivée
                            'elevation_loss': checkpoints[i + 1]['elevation_loss']
                            # Prendre le dénivelé du point d'arrivée
                        }

        self.section_selector.configure(values=sorted(list(sections.keys())))
        if sections:
            self.section_selector.set(sorted(list(sections.keys()))[0])

        # Stocker les informations des sections pour les utiliser plus tard
        self.sections_info = sections

    def update_displays(self):
        """Mettre à jour tous les affichages en fonction de la course sélectionnée"""
        self.clear_all_displays()
        selected_race = self.race_selector.get()

        # Mettre à jour les progressions
        self.update_progression_displays(selected_race)

        # Mettre à jour les dénivelés
        self.update_elevation_displays(selected_race)

        # Mettre à jour les vitesses
        self.update_speed_displays(selected_race)

        # Mettre à jour l'affichage des sections
        self.update_section_display()

    def clear_all_displays(self):
        """Effacer tous les affichages existants"""
        for widget in self.progress_global_scroll.winfo_children():
            widget.destroy()
        for widget in self.progress_sections_scroll.winfo_children():
            widget.destroy()
        for widget in self.climbers_scroll.winfo_children():
            widget.destroy()
        for widget in self.descenders_scroll.winfo_children():
            widget.destroy()
        for widget in self.speed_avg_scroll.winfo_children():
            widget.destroy()
        for widget in self.speed_effort_scroll.winfo_children():
            widget.destroy()
        for widget in self.speed_sections_scroll.winfo_children():
            widget.destroy()
        for widget in self.section_results_scroll.winfo_children():
            widget.destroy()

    def create_table(self, parent, columns, headers, data, height=10, tooltips=None):
        """Créer un tableau personnalisé avec style uniforme et infobulles"""
        style = ttk.Style()
        style.configure(
            "Custom.Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=30
        )
        style.configure(
            "Custom.Treeview.Heading",
            background="#2b2b2b",
            foreground="white"
        )

        tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=height,
            style="Custom.Treeview"
        )

        # Création des infobulles
        tooltip = None
        if tooltips:
            from tkinter import messagebox
            def show_tooltip(event):
                column = tree.identify_column(event.x)
                col_id = int(column.replace('#', '')) - 1
                if col_id < len(columns) and columns[col_id] in tooltips:
                    messagebox.showinfo("Information", tooltips[columns[col_id]])

            tree.bind('<Button-3>', show_tooltip)  # Clic droit pour afficher l'infobulle

        for col in columns:
            header_text = headers[col]
            if tooltips and col in tooltips:
                header_text += " (❓)"  # Ajouter un indicateur visuel
            tree.heading(col, text=header_text)
            tree.column(col, width=headers.get(f"{col}_width", 100), anchor="center")

        # Ajouter les données
        for row in data:
            tree.insert("", "end", values=row)

        return tree

    def create_section_info_card(self, parent, section_info):
        """Créer une carte d'information pour une section avec infobulles"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill=tk.X, padx=5, pady=5)

        title = ctk.CTkLabel(
            frame,
            text=section_info['name'],
            font=("Arial", 16, "bold")
        )
        title.pack(pady=5)

        # Création d'un frame pour les informations avec infobulles
        info_frame = ctk.CTkFrame(frame)
        info_frame.pack(pady=5)

        # Distance
        distance_frame = ctk.CTkFrame(info_frame)
        distance_frame.pack(side=tk.LEFT, padx=10)
        distance_label = ctk.CTkLabel(
            distance_frame,
            text=f"Distance: {section_info['distance']:.1f}km"
        )
        distance_label.pack(side=tk.LEFT)

        def show_distance_info():
            messagebox.showinfo("Information",
                                "Distance horizontale entre les deux points de la section.")

        distance_info = ctk.CTkButton(
            distance_frame,
            text="❓",
            width=20,
            command=show_distance_info
        )
        distance_info.pack(side=tk.LEFT, padx=2)

        # Dénivelé positif
        dplus_frame = ctk.CTkFrame(info_frame)
        dplus_frame.pack(side=tk.LEFT, padx=10)
        dplus_label = ctk.CTkLabel(
            dplus_frame,
            text=f"D+: {section_info['elevation_gain']}m"
        )
        dplus_label.pack(side=tk.LEFT)

        def show_dplus_info():
            messagebox.showinfo("Information",
                                "Dénivelé positif accumulé sur la section.\n"
                                "Représente la somme des montées uniquement.")

        dplus_info = ctk.CTkButton(
            dplus_frame,
            text="❓",
            width=20,
            command=show_dplus_info
        )
        dplus_info.pack(side=tk.LEFT, padx=2)

        # Dénivelé négatif
        dminus_frame = ctk.CTkFrame(info_frame)
        dminus_frame.pack(side=tk.LEFT, padx=10)
        dminus_label = ctk.CTkLabel(
            dminus_frame,
            text=f"D-: {section_info['elevation_loss']}m"
        )
        dminus_label.pack(side=tk.LEFT)

        def show_dminus_info():
            messagebox.showinfo("Information",
                                "Dénivelé négatif accumulé sur la section.\n"
                                "Représente la somme des descentes uniquement.")

        dminus_info = ctk.CTkButton(
            dminus_frame,
            text="❓",
            width=20,
            command=show_dminus_info
        )
        dminus_info.pack(side=tk.LEFT, padx=2)

        return frame


    def update_progression_displays(self, selected_race):
        """Mettre à jour les affichages de progression"""
        # Progression globale
        global_progressions = []
        for bib in self.bibs:
            if str(bib) in self.scraper.all_data:
                data = self.scraper.all_data[str(bib)]
                if selected_race == "Toutes les courses" or data['infos']['race_name'] == selected_race:
                    checkpoints = data['checkpoints']
                    if len(checkpoints) >= 2:
                        first_rank = None
                        last_rank = None

                        for cp in checkpoints:
                            if cp['rank'] is not None:
                                try:
                                    rank = int(cp['rank'])
                                    if first_rank is None:
                                        first_rank = rank
                                    last_rank = rank
                                except ValueError:
                                    continue

                        if first_rank is not None and last_rank is not None:
                            progression = first_rank - last_rank
                            global_progressions.append({
                                'progression': progression,
                                'bib': bib,
                                'name': data['infos']['name'],
                                'race': data['infos']['race_name'],
                                'start_pos': first_rank,
                                'end_pos': last_rank
                            })

        # Trier et afficher les meilleures progressions
        global_progressions.sort(key=lambda x: x['progression'], reverse=True)

        columns = ["rank", "bib", "name", "race", "start_pos", "end_pos", "progression"]
        headers = {
            "rank": "Position",
            "rank_width": 80,
            "bib": "Dossard",
            "bib_width": 80,
            "name": "Nom",
            "name_width": 200,
            "race": "Course",
            "race_width": 150,
            "start_pos": "Pos. départ",
            "start_pos_width": 100,
            "end_pos": "Pos. finale",
            "end_pos_width": 100,
            "progression": "Progression",
            "progression_width": 100
        }

        data = [
            (
                i + 1,
                prog['bib'],
                prog['name'],
                prog['race'],
                prog['start_pos'],
                prog['end_pos'],
                f"+{prog['progression']}" if prog['progression'] > 0 else str(prog['progression'])
            )
            for i, prog in enumerate(global_progressions[:20])
        ]

        # Ajouter les tooltips pour la progression globale
        tooltips = {
            "progression": "Places gagnées entre le premier et le dernier point de passage.",
            "start_pos": "Position au premier point de chronométrage.",
            "end_pos": "Position finale du coureur."
        }

        if data:
            ctk.CTkLabel(
                self.progress_global_scroll,
                text="Top 20 des meilleures progressions (Clic droit sur les en-têtes pour plus d'informations)",
                font=("Arial", 16, "bold")
            ).pack(pady=10)

            tree = self.create_table(self.progress_global_scroll, columns, headers, data, tooltips=tooltips)
            tree.pack(fill=tk.X, padx=5, pady=5)

        # Ajouter les tooltips pour la progression entre points
        section_tooltips = {
            "section": "Points de passage entre lesquels la progression est calculée",
            "progression": "Nombre de places gagnées sur cette section spécifique",
            "ranks": "Positions au début et à la fin de la section"
        }


        # Progression entre points
        section_progressions = []
        for bib in self.bibs:
            if str(bib) in self.scraper.all_data:
                data = self.scraper.all_data[str(bib)]
                if selected_race == "Toutes les courses" or data['infos']['race_name'] == selected_race:
                    checkpoints = data['checkpoints']

                    for i in range(len(checkpoints) - 1):
                        if checkpoints[i]['rank'] and checkpoints[i + 1]['rank']:
                            try:
                                rank1 = int(checkpoints[i]['rank'])
                                rank2 = int(checkpoints[i + 1]['rank'])
                                progression = rank1 - rank2
                                if progression > 0:
                                    section_progressions.append({
                                        'progression': progression,
                                        'bib': bib,
                                        'name': data['infos']['name'],
                                        'race': data['infos']['race_name'],
                                        'from_point': checkpoints[i]['point'],
                                        'to_point': checkpoints[i + 1]['point'],
                                        'start_rank': rank1,
                                        'end_rank': rank2
                                    })
                            except ValueError:
                                continue

        section_progressions.sort(key=lambda x: x['progression'], reverse=True)

        if section_progressions:
            ctk.CTkLabel(
                self.progress_sections_scroll,
                text="Top 20 des meilleures progressions entre points",
                font=("Arial", 16, "bold")
            ).pack(pady=10)

            columns = ["rank", "bib", "name", "race", "section", "progression", "ranks"]
            headers = {
                "rank": "Position",
                "rank_width": 80,
                "bib": "Dossard",
                "bib_width": 80,
                "name": "Nom",
                "name_width": 200,
                "race": "Course",
                "race_width": 150,
                "section": "Section",
                "section_width": 300,
                "progression": "Progression",
                "progression_width": 100,
                "ranks": "Classements",
                "ranks_width": 150
            }

            data = [
                (
                    i + 1,
                    prog['bib'],
                    prog['name'],
                    prog['race'],
                    f"{prog['from_point']} → {prog['to_point']}",
                    f"+{prog['progression']}",
                    f"{prog['start_rank']} → {prog['end_rank']}"
                )
                for i, prog in enumerate(section_progressions[:20])
            ]

            tree = self.create_table(self.progress_sections_scroll, columns, headers, data)
            tree.pack(fill=tk.X, padx=5, pady=5)

    def update_elevation_displays(self, selected_race):
        """Mettre à jour les affichages de dénivelé avec tooltips et indicateurs de tendance"""
        # Calcul pour les grimpeurs
        climbers = []
        for bib in self.bibs:
            if str(bib) in self.scraper.all_data:
                data = self.scraper.all_data[str(bib)]
                if selected_race == "Toutes les courses" or data['infos']['race_name'] == selected_race:
                    checkpoints = data['checkpoints']
                    total_elevation_time = 0
                    total_elevation_gain = 0
                    total_distance = 0

                    for i in range(len(checkpoints) - 1):
                        if checkpoints[i]['elevation_gain'] > 100:  # Sections significatives
                            try:
                                time1 = datetime.strptime(checkpoints[i]['race_time'], "%H:%M:%S")
                                time2 = datetime.strptime(checkpoints[i + 1]['race_time'], "%H:%M:%S")
                                segment_time = (time2 - time1).total_seconds() / 3600
                                distance = checkpoints[i + 1]['kilometer'] - checkpoints[i]['kilometer']

                                if segment_time > 0:
                                    total_elevation_time += segment_time
                                    total_elevation_gain += checkpoints[i]['elevation_gain']
                                    total_distance += distance
                            except:
                                continue

                    if total_elevation_time > 0:
                        climbing_speed = total_elevation_gain / total_elevation_time
                        # Calculer le ratio dénivelé/distance pour évaluer la difficulté
                        elevation_ratio = total_elevation_gain / (total_distance * 1000) if total_distance > 0 else 0
                        climbers.append({
                            'speed': climbing_speed,
                            'bib': bib,
                            'name': data['infos']['name'],
                            'race': data['infos']['race_name'],
                            'elevation_gain': total_elevation_gain,
                            'time': total_elevation_time,
                            'distance': total_distance,
                            'elevation_ratio': elevation_ratio
                        })

        climbers.sort(key=lambda x: x['speed'], reverse=True)

        # Tooltips pour les grimpeurs
        climber_tooltips = {
            "elevation": "Dénivelé positif total cumulé sur les sections de montée significative (>100m D+)",
            "time": "Temps total passé sur les sections de montée significative",
            "speed": "Vitesse verticale moyenne en montée (mètres de dénivelé par heure)",
            "ratio": "Pourcentage moyen de pente (D+ / Distance horizontale)",
            "tendency": "Indicateur de difficulté basé sur le ratio dénivelé/distance"
        }

        if climbers:
            ctk.CTkLabel(
                self.climbers_scroll,
                text="Top 20 des meilleurs grimpeurs (Clic droit sur les en-têtes pour plus d'informations)",
                font=("Arial", 16, "bold")
            ).pack(pady=10)

            columns = ["rank", "bib", "name", "race", "elevation", "time", "speed", "ratio", "tendency"]
            headers = {
                "rank": "Position",
                "rank_width": 80,
                "bib": "Dossard",
                "bib_width": 80,
                "name": "Nom",
                "name_width": 200,
                "race": "Course",
                "race_width": 150,
                "elevation": "D+ total",
                "elevation_width": 100,
                "time": "Temps",
                "time_width": 100,
                "speed": "Vitesse",
                "speed_width": 100,
                "ratio": "Pente moy.",
                "ratio_width": 100,
                "tendency": "Tendance",
                "tendency_width": 80
            }

            def get_climb_indicator(ratio):
                if ratio > 0.15:  # >15%
                    return "↗️↗️↗️"  # Très raide
                elif ratio > 0.10:  # >10%
                    return "↗️↗️"  # Raide
                else:
                    return "↗️"  # Modéré

            data = [
                (
                    i + 1,
                    climb['bib'],
                    climb['name'],
                    climb['race'],
                    f"{climb['elevation_gain']}m",
                    f"{climb['time']:.1f}h",
                    f"{climb['speed']:.1f} m/h",
                    f"{(climb['elevation_ratio'] * 100):.1f}%",
                    get_climb_indicator(climb['elevation_ratio'])
                )
                for i, climb in enumerate(climbers[:20])
            ]

            tree = self.create_table(self.climbers_scroll, columns, headers, data, tooltips=climber_tooltips)
            tree.pack(fill=tk.X, padx=5, pady=5)

        # Descente (avec les mêmes améliorations)
        descenders = []
        for bib in self.bibs:
            if str(bib) in self.scraper.all_data:
                data = self.scraper.all_data[str(bib)]
                if selected_race == "Toutes les courses" or data['infos']['race_name'] == selected_race:
                    checkpoints = data['checkpoints']
                    total_descent_time = 0
                    total_elevation_loss = 0
                    total_distance = 0

                    for i in range(len(checkpoints) - 1):
                        if checkpoints[i]['elevation_loss'] > 100:
                            try:
                                time1 = datetime.strptime(checkpoints[i]['race_time'], "%H:%M:%S")
                                time2 = datetime.strptime(checkpoints[i + 1]['race_time'], "%H:%M:%S")
                                segment_time = (time2 - time1).total_seconds() / 3600
                                distance = checkpoints[i + 1]['kilometer'] - checkpoints[i]['kilometer']

                                if segment_time > 0:
                                    total_descent_time += segment_time
                                    total_elevation_loss += abs(checkpoints[i]['elevation_loss'])
                                    total_distance += distance
                            except:
                                continue

                    if total_descent_time > 0:
                        descending_speed = total_elevation_loss / total_descent_time
                        elevation_ratio = total_elevation_loss / (total_distance * 1000) if total_distance > 0 else 0
                        descenders.append({
                            'speed': descending_speed,
                            'bib': bib,
                            'name': data['infos']['name'],
                            'race': data['infos']['race_name'],
                            'elevation_loss': total_elevation_loss,
                            'time': total_descent_time,
                            'distance': total_distance,
                            'elevation_ratio': elevation_ratio
                        })

        descenders.sort(key=lambda x: x['speed'], reverse=True)

        # Tooltips pour les descendeurs
        descender_tooltips = {
            "elevation": "Dénivelé négatif total cumulé sur les sections de descente significative (>100m D-)",
            "time": "Temps total passé sur les sections de descente significative",
            "speed": "Vitesse verticale moyenne en descente (mètres de dénivelé par heure)",
            "ratio": "Pourcentage moyen de pente (D- / Distance horizontale)",
            "tendency": "Indicateur de difficulté basé sur le ratio dénivelé/distance"
        }

        if descenders:
            ctk.CTkLabel(
                self.descenders_scroll,
                text="Top 20 des meilleurs descendeurs (Clic droit sur les en-têtes pour plus d'informations)",
                font=("Arial", 16, "bold")
            ).pack(pady=10)

            def get_descent_indicator(ratio):
                if ratio > 0.15:  # >15%
                    return "↘️↘️↘️"  # Très raide
                elif ratio > 0.10:  # >10%
                    return "↘️↘️"  # Raide
                else:
                    return "↘️"  # Modéré

            data = [
                (
                    i + 1,
                    desc['bib'],
                    desc['name'],
                    desc['race'],
                    f"{desc['elevation_loss']}m",
                    f"{desc['time']:.1f}h",
                    f"{desc['speed']:.1f} m/h",
                    f"{(desc['elevation_ratio'] * 100):.1f}%",
                    get_descent_indicator(desc['elevation_ratio'])
                )
                for i, desc in enumerate(descenders[:20])
            ]

            tree = self.create_table(self.descenders_scroll, columns, headers, data, tooltips=descender_tooltips)
            tree.pack(fill=tk.X, padx=5, pady=5)

    def update_speed_displays(self, selected_race):
        """Mettre à jour les affichages de vitesse"""
        speeds = []
        efforts = []
        section_speeds = []

        for bib in self.bibs:
            if str(bib) in self.scraper.all_data:
                data = self.scraper.all_data[str(bib)]
                if selected_race == "Toutes les courses" or data['infos']['race_name'] == selected_race:
                    checkpoints = data['checkpoints']

                    # Calcul des vitesses moyennes
                    avg_speed = 0
                    avg_effort = 0
                    count = 0

                    for cp in checkpoints:
                        try:
                            speed = float(cp['speed'].replace('km/h', '').strip())
                            effort = float(cp['effort_speed'].replace('km/h', '').strip())
                            avg_speed += speed
                            avg_effort += effort
                            count += 1
                        except:
                            continue

                    if count > 0:
                        speeds.append({
                            'speed': avg_speed / count,
                            'bib': bib,
                            'name': data['infos']['name'],
                            'race': data['infos']['race_name']
                        })

                        efforts.append({
                            'effort': avg_effort / count,
                            'bib': bib,
                            'name': data['infos']['name'],
                            'race': data['infos']['race_name']
                        })

                    # Calcul des vitesses par section
                    for i in range(len(checkpoints) - 1):
                        try:
                            time1 = datetime.strptime(checkpoints[i]['race_time'], "%H:%M:%S")
                            time2 = datetime.strptime(checkpoints[i + 1]['race_time'], "%H:%M:%S")
                            segment_time = (time2 - time1).total_seconds() / 3600
                            distance = checkpoints[i + 1]['kilometer'] - checkpoints[i]['kilometer']

                            if segment_time > 0:
                                section_speed = distance / segment_time
                                section_speeds.append({
                                    'speed': section_speed,
                                    'bib': bib,
                                    'name': data['infos']['name'],
                                    'race': data['infos']['race_name'],
                                    'from_point': checkpoints[i]['point'],
                                    'to_point': checkpoints[i + 1]['point'],
                                    'distance': distance
                                })
                        except:
                            continue

        # Afficher les vitesses moyennes
        speeds.sort(key=lambda x: x['speed'], reverse=True)
        self.display_speed_table(
            self.speed_avg_scroll,
            speeds[:20],
            "Top 20 des meilleures vitesses moyennes",
            "speed"
        )

        # Afficher les vitesses effort
        efforts.sort(key=lambda x: x['effort'], reverse=True)
        self.display_speed_table(
            self.speed_effort_scroll,
            efforts[:20],
            "Top 20 des meilleures vitesses effort",
            "effort"
        )

        # Afficher les vitesses par section
        section_speeds.sort(key=lambda x: x['speed'], reverse=True)
        self.display_section_speed_table(
            self.speed_sections_scroll,
            section_speeds[:20]
        )

    def display_speed_table(self, parent, data, title, speed_type):
        """Afficher un tableau de vitesses avec infobulles"""
        if not data:
            return

        tooltips = {
            "speed": {
                'speed': "Moyenne des vitesses instantanées sur l'ensemble du parcours (sans tenir compte du dénivelé).",
                'effort': "Moyenne des vitesses effort qui prennent en compte le dénivelé. Permet de comparer l'intensité réelle de l'effort."
            }[speed_type]
        }

        ctk.CTkLabel(
            parent,
            text=title + " (Clic droit sur les en-têtes pour plus d'informations)",
            font=("Arial", 16, "bold")
        ).pack(pady=10)

        columns = ["rank", "bib", "name", "race", "speed"]
        headers = {
            "rank": "Position",
            "rank_width": 80,
            "bib": "Dossard",
            "bib_width": 80,
            "name": "Nom",
            "name_width": 200,
            "race": "Course",
            "race_width": 150,
            "speed": {
                'speed': "Vitesse moyenne",
                'effort': "Vitesse effort moyenne"
            }[speed_type],
            "speed_width": 100
        }

        table_data = [
            (
                i + 1,
                item['bib'],
                item['name'],
                item['race'],
                f"{item[speed_type]:.1f} km/h"
            )
            for i, item in enumerate(data)
        ]

        tree = self.create_table(parent, columns, headers, table_data, tooltips=tooltips)
        tree.pack(fill=tk.X, padx=5, pady=5)

    def display_section_speed_table(self, parent, data):
        """Afficher un tableau de vitesses par section avec infobulles"""
        if not data:
            return

        tooltips = {
            "speed": "Vitesse moyenne réelle sur la section calculée avec (Distance / Temps).\nNe prend pas en compte le dénivelé.",
            "distance": "Distance horizontale entre les deux points de la section.",
            "section": "Points de début et de fin de la section."
        }

        ctk.CTkLabel(
            parent,
            text="Top 20 des meilleures vitesses par section (Clic droit sur les en-têtes pour plus d'informations)",
            font=("Arial", 16, "bold")
        ).pack(pady=10)

        columns = ["rank", "bib", "name", "race", "section", "distance", "speed"]
        headers = {
            "rank": "Position",
            "rank_width": 80,
            "bib": "Dossard",
            "bib_width": 80,
            "name": "Nom",
            "name_width": 200,
            "race": "Course",
            "race_width": 150,
            "section": "Section",
            "section_width": 300,
            "distance": "Distance",
            "distance_width": 100,
            "speed": "Vitesse",
            "speed_width": 100
        }

        table_data = [
            (
                i + 1,
                item['bib'],
                item['name'],
                item['race'],
                f"{item['from_point']} → {item['to_point']}",
                f"{item['distance']:.1f} km",
                f"{item['speed']:.1f} km/h"
            )
            for i, item in enumerate(data)
        ]

        tree = self.create_table(parent, columns, headers, table_data, tooltips=tooltips)
        tree.pack(fill=tk.X, padx=5, pady=5)

    def convert_time_to_seconds(self, time_str):
        """
        Convertit un temps au format HH:MM:SS en secondes,
        en gérant les temps supérieurs à 24h
        """
        try:
            # Diviser le temps en heures, minutes, secondes
            hours, minutes, seconds = map(int, time_str.split(':'))

            # Calculer le total en secondes
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds
        except Exception as e:
            print(f"Erreur lors de la conversion du temps {time_str}: {e}")
            return None

    def update_section_display(self):
        """Mettre à jour l'affichage des performances par section"""
        # Nettoyer l'affichage existant
        for widget in self.section_results_scroll.winfo_children():
            widget.destroy()

        selected_race = self.race_selector.get()
        selected_section = self.section_selector.get()
        if not selected_section or selected_section not in self.sections_info:
            return

        # Utiliser les informations correctes de la section
        section_info = self.sections_info[selected_section]

        for bib in self.bibs:
            if str(bib) in self.scraper.all_data:
                data = self.scraper.all_data[str(bib)]
                if selected_race == "Toutes les courses" or data['infos']['race_name'] == selected_race:
                    checkpoints = data['checkpoints']

                    for i in range(len(checkpoints) - 1):
                        section = f"{checkpoints[i]['point']} → {checkpoints[i + 1]['point']}"
                        if section == selected_section:
                            try:
                                # Utiliser les dénivelés corrects stockés
                                if section_info is None:
                                    section_info = {
                                        'name': section,
                                        'distance': checkpoints[i + 1]['kilometer'] - checkpoints[i]['kilometer'],
                                        'elevation_gain': checkpoints[i + 1]['elevation_gain'],
                                        'elevation_loss': checkpoints[i + 1]['elevation_loss']
                                    }

                                # Le reste du code pour le calcul des temps et vitesses
                                time1_seconds = self.convert_time_to_seconds(checkpoints[i]['race_time'])
                                time2_seconds = self.convert_time_to_seconds(checkpoints[i + 1]['race_time'])

                                if time1_seconds is None or time2_seconds is None:
                                    continue

                                section_time = time2_seconds - time1_seconds
                                if section_time <= 0:  # Ignorer les sections avec temps négatif ou nul
                                    continue

                                # Calculer la vitesse classique
                                hours = section_time / 3600
                                speed = section_info['distance'] / hours if hours > 0 else 0

                                # Calculer la vitesse effort avec la nouvelle formule
                                effort_speed = self.calculate_effort_speed(
                                    distance=section_info['distance'],
                                    time_seconds=section_time,
                                    elevation_gain=section_info['elevation_gain'],
                                    elevation_loss=section_info['elevation_loss']
                                )

                                # Déterminer la tendance de la section
                                total_distance_m = section_info['distance'] * 1000
                                if total_distance_m > 0:
                                    elevation_ratio = (section_info['elevation_gain'] - section_info[
                                        'elevation_loss']) / total_distance_m
                                    if elevation_ratio > 0.05:  # >5% montée
                                        tendency = "↗️"
                                    elif elevation_ratio < -0.05:  # >5% descente
                                        tendency = "↘️"
                                    else:
                                        tendency = "➡️"
                                else:
                                    tendency = "➡️"

                                # Progression sur la section
                                rank1 = int(checkpoints[i]['rank']) if checkpoints[i]['rank'] else 0
                                rank2 = int(checkpoints[i + 1]['rank']) if checkpoints[i + 1]['rank'] else 0
                                progression = rank1 - rank2 if rank1 and rank2 else 0

                                section_performances.append({
                                    'bib': bib,
                                    'name': data['infos']['name'],
                                    'race': data['infos']['race_name'],
                                    'time': section_time,
                                    'speed': speed,
                                    'effort_speed': effort_speed,
                                    'progression': progression,
                                    'start_rank': rank1,
                                    'end_rank': rank2,
                                    'tendency': tendency
                                })
                            except Exception as e:
                                print(f"Erreur lors du calcul des performances: {e}")
                                continue

        if section_info:
            # Créer la carte d'information de la section
            self.create_section_info_card(self.section_results_scroll, section_info)

            # 1. Classement par temps
            section_performances.sort(key=lambda x: x['time'])
            self.create_section_performance_table(
                self.section_results_scroll,
                section_performances[:20],
                "Top 20 temps sur la section",
                'time'
            )

            # 2. Classement par vitesse (avec tendance)
            section_performances.sort(key=lambda x: x['speed'], reverse=True)
            self.create_section_performance_table(
                self.section_results_scroll,
                section_performances[:20],
                "Top 20 vitesses sur la section",
                'speed'
            )

            # 3. Classement par vitesse effort (avec tendance)
            section_performances.sort(key=lambda x: x['effort_speed'], reverse=True)
            self.create_section_performance_table(
                self.section_results_scroll,
                section_performances[:20],
                "Top 20 vitesses effort sur la section",
                'effort'
            )

            # 4. Classement par progression
            section_performances.sort(key=lambda x: x['progression'], reverse=True)
            self.create_section_performance_table(
                self.section_results_scroll,
                section_performances[:20],
                "Top 20 progressions sur la section",
                'progression'
            )

    def calculate_effort_speed(self, distance, time_seconds, elevation_gain, elevation_loss):
        """
        Calcule la vitesse effort en prenant en compte le dénivelé

        La formule utilisée est :
        Vitesse effort = (distance + (D+ * facteur_montée) + (D- * facteur_descente)) / temps

        Où:
        - facteur_montée = 10 (100m de D+ équivaut à 1km de distance)
        - facteur_descente = 2 (100m de D- équivaut à 0.2km de distance)
        """
        if time_seconds == 0:
            return 0

        # Conversion des dénivelés en kilomètres équivalents
        elevation_gain_factor = 10  # 1000m D+ = 10km de distance
        elevation_loss_factor = 2  # 1000m D- = 2km de distance

        equivalent_distance = (
                distance +  # Distance réelle
                (elevation_gain / 1000 * elevation_gain_factor) +  # Distance équivalente montée
                (elevation_loss / 1000 * elevation_loss_factor)  # Distance équivalente descente
        )

        hours = time_seconds / 3600
        effort_speed = equivalent_distance / hours

        return effort_speed

    def create_section_performance_table(self, parent, data, title, performance_type):
        """Créer un tableau de performances pour une section spécifique avec tendance"""
        if not data:
            return

        frame = ctk.CTkFrame(parent)
        frame.pack(fill=tk.X, padx=5, pady=10)

        tooltips = {
            "performance": {
                'time': (
                    "Temps réel mis pour parcourir la section.\n"
                    "Calculé comme la différence entre les temps de passage aux deux points.\n"
                    "Inclut les temps d'arrêt éventuels."
                ),
                'speed': (
                    "Vitesse moyenne réelle sur la section.\n"
                    "Calculée avec : Distance / Temps total\n"
                    "Ne prend pas en compte le dénivelé."
                ),
                'effort': (
                    "Vitesse effort qui normalise la performance selon le terrain.\n"
                    "Calculée en prenant en compte :\n"
                    "- La distance réelle\n"
                    "- Le dénivelé positif (facteur 10)\n"
                    "- Le dénivelé négatif (facteur 2)\n"
                    "Permet de comparer les performances sur des terrains différents."
                ),
                'progression': (
                    "Évolution du classement sur la section.\n"
                    "Nombre de places gagnées (valeur positive)\n"
                    "ou perdues (valeur négative)."
                )
            }[performance_type],
            "tendency": "Indication du profil de la section:\n↗️ Montée (>5%)\n➡️ Plat\n↘️ Descente (>5%)"
        }

        ctk.CTkLabel(
            frame,
            text=title + " (Clic droit sur les en-têtes pour plus d'informations)",
            font=("Arial", 14, "bold")
        ).pack(pady=5)

        columns = ["rank", "bib", "name", "race", "performance", "tendency"]
        headers = {
            "rank": "Position",
            "rank_width": 80,
            "bib": "Dossard",
            "bib_width": 80,
            "name": "Nom",
            "name_width": 200,
            "race": "Course",
            "race_width": 150,
            "performance": {
                'time': "Temps",
                'speed': "Vitesse",
                'effort': "Vitesse effort",
                'progression': "Progression"
            }[performance_type],
            "performance_width": 150,
            "tendency": "Tendance",
            "tendency_width": 80
        }

        def format_performance(item):
            if performance_type == 'time':
                minutes = item['time'] / 60
                return f"{int(minutes)}:{int((minutes % 1) * 60):02d}"
            elif performance_type == 'speed':
                return f"{item['speed']:.1f} km/h"
            elif performance_type == 'effort':
                return f"{item['effort_speed']:.1f} km/h"
            elif performance_type == 'progression':
                return f"+{item['progression']}" if item['progression'] > 0 else str(item['progression'])

        table_data = [
            (
                i + 1,
                item['bib'],
                item['name'],
                item['race'],
                format_performance(item),
                item.get('tendency', '➡️')
            )
            for i, item in enumerate(data)
        ]

        tree = self.create_table(frame, columns, headers, table_data, tooltips=tooltips)
        tree.pack(fill=tk.X, padx=5, pady=5)




if __name__ == "__main__":
    app = RaceTrackerApp()
    app.run()
