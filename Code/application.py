import tkinter as tk
from tkinter import filedialog, messagebox
import csv
import math
import cv2
from PIL import Image, ImageTk

def validate_and_proceed():
    csv_path = csv_file_var.get()
    video_path = video_file_var.get()
    mass_value = mass_var.get()
    masscheck_value = masscheck_var.get()
    min_moves_value = min_moves_var.get()
    prise_value = prise_var.get()
    activite_value1 = activite_var1.get()
    activite_value2 = activite_var2.get()
    activite_value3 = activite_var3.get()
    activite_value4 = activite_var4.get()

    if not csv_path:
        messagebox.showerror("Erreur", "Veuillez sélectionner un fichier CSV.")
        return

    if not min_moves_value:
        messagebox.showerror("Erreur", "Veuillez entrer le nombre minimum de mouvements requis.")
        return

    try:
        int(min_moves_value)
    except ValueError:
        messagebox.showerror("Erreur", "Le nombre de mouvements doit être un entier.")
        return

    open_analysis_window(
        csv_path, 
        mass_value, 
        masscheck_value, 
        int(min_moves_value), 
        prise_value, 
        activite_value1, 
        activite_value2, 
        activite_value3, 
        activite_value4
    )
    if video_path != "":
        play_video(video_path)

def browse_csv():
    filepath = filedialog.askopenfilename(filetypes=[("Fichiers CSV", "*.csv")])
    if filepath:
        csv_file_var.set(filepath)

def browse_video():
    filepath = filedialog.askopenfilename(filetypes=[("Fichiers vidéo", "*.mp4")])
    if filepath:
        video_file_var.set(filepath)

def play_video(video_path):
    video_window = tk.Toplevel(root)
    video_window.title("Lecteur vidéo")

    # Dimensions souhaitées pour la vidéo
    video_width = 640
    video_height = 360

    video_label = tk.Label(video_window, bg="black")
    video_label.pack()

    # Boutons pour contrôler la vidéo
    control_frame = tk.Frame(video_window, bg="#f0f0f0")
    control_frame.pack(pady=10)

    play_button = tk.Button(control_frame, text="Rejouer", command=lambda: restart_video(), bg="#4CAF50", fg="white", padx=10, pady=5)
    play_button.pack(side="left", padx=5)

    stop_button = tk.Button(control_frame, text="Arrêter", command=lambda: stop_video(), bg="#F44336", fg="white", padx=10, pady=5)
    stop_button.pack(side="left", padx=5)

    # Variables de contrôle
    is_playing = tk.BooleanVar(value=True)

    cap = cv2.VideoCapture(video_path)

    def update_frame():
        if is_playing.get(): 
            ret, frame = cap.read()
            if ret:
                # Redimensionner la frame
                frame = cv2.resize(frame, (video_width, video_height))
                
                # Convertir l'image en format RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                
                # Mettre à jour le label
                video_label.imgtk = imgtk
                video_label.configure(image=imgtk)

                # Rappeler cette fonction après un délai
                video_label.after(10, update_frame)
            else:
                restart_video()

    def restart_video():
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        is_playing.set(True)
        update_frame()

    def stop_video():
        is_playing.set(False)

    update_frame()

    def on_close():
        cap.release()
        video_window.destroy()

    video_window.protocol("WM_DELETE_WINDOW", on_close)

def calculate_angle(o, a, b):
    try:
        # Vecteurs \vec{oa} et \vec{ob}
        oa = (a[0] - o[0], a[1] - o[1])
        ob = (b[0] - o[0], b[1] - o[1])

        # Produit scalaire et normes
        dot_product = oa[0] * ob[0] + oa[1] * ob[1]
        norm_oa = math.sqrt(oa[0]**2 + oa[1]**2)
        norm_ob = math.sqrt(ob[0]**2 + ob[1]**2)

        if norm_oa == 0 or norm_ob == 0:
            return None

        # Calcul du cosinus de l'angle
        cos_theta = dot_product / (norm_oa * norm_ob)

        # Limiter cos_theta pour éviter des erreurs dues à des imprécisions numériques
        cos_theta = max(min(cos_theta, 1.0), -1.0)

        # Calcul de l'angle en radians puis conversion en degrés
        angle = math.degrees(math.acos(cos_theta))
        return angle
    except Exception:
        return None

def detect_movements(csv_path):
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            headers = next(reader)  # Lire les en-têtes

            # Identifier les colonnes des points pour chaque angle
            angle_points = {
                "pd": {"o": {}, "a": {}, "b": {}},
                "cd": {"o": {}, "a": {}, "b": {}},
                "ep": {"o": {}, "a": {}, "b": {}},
                "cou": {"o": {}, "a": {}, "b": {}}
            }

            for angle, points in angle_points.items():
                for i, col in enumerate(headers):
                    if f"{angle}/o/X" in col:
                        points["o"]["X"] = i
                    elif f"{angle}/o/Y" in col:
                        points["o"]["Y"] = i
                    elif f"{angle}/a/X" in col:
                        points["a"]["X"] = i
                    elif f"{angle}/a/Y" in col:
                        points["a"]["Y"] = i
                    elif f"{angle}/b/X" in col:
                        points["b"]["X"] = i
                    elif f"{angle}/b/Y" in col:
                        points["b"]["Y"] = i

            previous_angles = {angle: None for angle in angle_points}
            movement_counts = {angle: 0 for angle in angle_points}
            movement_active = {angle: False for angle in angle_points}
            min_max_values = {
                "pd": {"min": 360, "max": -360},
                "cd": {"min": 360, "max": -360},
                "ep": {"min": 360, "max": -360},
                "cou": {"min": 360, "max": -360}
            }

            # Dictionnaire pour stocker les dernières valeurs valides pour chaque angle
            last_valid_points = {angle: None for angle in angle_points}

            for row in reader:
                for angle, points in angle_points.items():
                    # Extraire les coordonnées
                    try:
                        o = (float(row[points["o"]["X"]].replace(',', '.')), float(row[points["o"]["Y"]].replace(',', '.')))
                        a = (float(row[points["a"]["X"]].replace(',', '.')), float(row[points["a"]["Y"]].replace(',', '.')))
                        b = (float(row[points["b"]["X"]].replace(',', '.')), float(row[points["b"]["Y"]].replace(',', '.')))

                        # Si les coordonnées sont valides, les mémoriser
                        last_valid_points[angle] = {"o": o, "a": a, "b": b}

                    except (ValueError, KeyError):
                        # Si une erreur est rencontrée, utiliser la dernière valeur valide
                        if last_valid_points[angle] is not None:
                            o = last_valid_points[angle]["o"]
                            a = last_valid_points[angle]["a"]
                            b = last_valid_points[angle]["b"]
                        else:
                            # Si aucune valeur valide n'existe, ignorer cet angle
                            continue

                    # Calculer l'angle actuel
                    current_angle = calculate_angle(o, a, b)

                    if current_angle is not None:
                        # Mettre à jour les valeurs min et max
                        min_max_values[angle]["min"] = min(min_max_values[angle]["min"], current_angle)
                        min_max_values[angle]["max"] = max(min_max_values[angle]["max"], current_angle)

                        # Comparer avec l'angle précédent
                        prev_angle = previous_angles[angle]

                        if prev_angle is not None and abs(current_angle - prev_angle) > 17.5:
                            if not movement_active[angle]:
                                movement_counts[angle] += 1
                                movement_active[angle] = True
                        else:
                            movement_active[angle] = False

                        # Mettre à jour l'angle précédent
                        previous_angles[angle] = current_angle

            total_movements = sum(movement_counts.values())
            return (
                total_movements,
                min_max_values["pd"]["min"], min_max_values["pd"]["max"],
                min_max_values["cd"]["min"], min_max_values["cd"]["max"],
                min_max_values["ep"]["min"], min_max_values["ep"]["max"],
                min_max_values["cou"]["min"], min_max_values["cou"]["max"]
            )

    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'analyser le fichier CSV : {e}")
        return None

def open_analysis_window(
        csv_path, 
        mass_value, 
        masscheck_value, 
        min_moves_value, 
        prise_value, 
        activite_value1, 
        activite_value2, 
        activite_value3, 
        activite_value4
    ):
    movement_count, pd_min, pd_max, cd_min, cd_max, ep_min, ep_max, cou_min, cou_max =  detect_movements(csv_path)

    if movement_count is None:
        return
    
    analysis_window = tk.Toplevel(root)
    analysis_window.title("Résultats de l'analyse")
    analysis_window.geometry("500x500")
    analysis_window.configure(bg="#f5f5f5")
    reba_scores = {
        "pd": 1,
        "cd": 1,
        "ep": 1,
        "cou": 1,
        "tronc": 3,
        "jambes": 2,
        "effort": 0,
        "prise": 0,
        "A": 0,
        "A_2": 0,
        "B": 0,
        "B_2": 0,
        "C": 0,
        "activite": 0,
        "final": 0  
    }
    tab_A = {
        1: {
            1: {1: 1, 2: 2, 3: 2, 4: 3, 5: 4},
            2: {1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
            3: {1: 3, 2: 4, 3: 5, 4: 6, 5: 7},
            4: {1: 4, 2: 5, 3: 6, 4: 7, 5: 8},
        },
        2: {
            1: {1: 1, 2: 3, 3: 4, 4: 5, 5: 6},
            2: {1: 2, 2: 4, 3: 5, 4: 6, 5: 7},
            3: {1: 3, 2: 5, 3: 6, 4: 7, 5: 8},
            4: {1: 4, 2: 6, 3: 7, 4: 8, 5: 9},
        },
        3: {
            1: {1: 3, 2: 4, 3: 5, 4: 6, 5: 7},
            2: {1: 3, 2: 5, 3: 6, 4: 7, 5: 8},
            3: {1: 5, 2: 6, 3: 7, 4: 8, 5: 9},
            4: {1: 6, 2: 7, 3: 8, 4: 9, 5: 9},
        }
    }
    tab_B = {
        1: {
            1: {1: 1, 2: 1, 3: 3, 4: 4, 5: 6, 6: 7},
            2: {1: 2, 2: 2, 3: 4, 4: 5, 5: 7, 6: 8},
            3: {1: 2, 2: 3, 3: 5, 4: 5, 5: 8, 6: 8},
        },
        2: {
            1: {1: 1, 2: 2, 3: 4, 4: 5, 5: 7, 6: 8},
            2: {1: 2, 2: 3, 3: 5, 4: 6, 5: 8, 6: 9},
            3: {1: 3, 2: 4, 3: 5, 4: 7, 5: 8, 6: 9}
        }
    }
    tab_C = {
        1: {1: 1, 2: 1, 3: 2, 4: 3, 5: 4, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12},
        2: {1: 1, 2: 2, 3: 3, 4: 4, 5: 4, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12},
        3: {1: 1, 2: 2, 3: 3, 4: 4, 5: 4, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12},
        4: {1: 2, 2: 3, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12},
        5: {1: 3, 2: 4, 3: 4, 4: 5, 5: 6, 6: 8, 7: 9, 8: 10, 9: 10, 10: 11, 11: 12, 12: 12},
        6: {1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9, 8: 10, 9: 10, 10: 11, 11: 12, 12: 12},
        7: {1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 9, 8: 10, 9: 11, 10: 11, 11: 12, 12: 12},
        8: {1: 5, 2: 6, 3: 7, 4: 8, 5: 8, 6: 9, 7: 10, 8: 10, 9: 11, 10: 12, 11: 12, 12: 12},
        9: {1: 6, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10, 7: 10, 8: 10, 9: 11, 10: 12, 11: 12, 12: 12},
        10: {1: 7, 2: 7, 3: 8, 4: 9, 5: 9, 6: 10, 7: 11, 8: 11, 9: 12, 10: 12, 11: 12, 12: 12},
        11: {1: 7, 2: 7, 3: 8, 4: 9, 5: 9, 6: 10, 7: 11, 8: 11, 9: 12, 10: 12, 11: 12, 12: 12},
        12: {1: 7, 2: 8, 3: 8, 4: 9, 5: 9, 6: 10, 7: 11, 8: 11, 9: 12, 10: 12, 11: 12, 12: 12}
    }
    tab_bg = {
        "pd": {1: "green", 2: "yellow", 3: "red"},
        "cd": {1: "green", 2: "orange"},
        "ep": {1: "green", 2: "yellow", 3: "orange", 4: "orange", 5: "red", 6: "purple"},
        "cou": {1: "green", 2: "yellow", 3: "red"},
        "tronc": {1: "green", 2: "yellow", 3: "orange", 4: "red", 5: "purple"},
        "jambes": {1: "green", 2: "yellow", 3: "orange", 4: "red"},
        "effort": {0: "green", 1: "yellow", 2: "orange", 3: "red"},
        "prise": {0: "green", 1: "yellow", 2: "orange", 3: "red"},
        "activite": {0: "green", 1: "yellow", 2: "orange", 3: "red"},
        "final": {1: "green", 2: "yellow", 3: "yellow", 4: "orange", 5: "orange", 6: "orange", 7: "orange", 8: "red", 9: "red", 10: "red", 11: "purple", 12: "purple", 13: "purple", 14: "purple", 15: "purple"}
    }

    if pd_min < 165:
        reba_scores["pd"] += 1
    if pd_max > 195:
        reba_scores["pd"] += 1
    if cd_min < 60 or cd_max > 100:
        reba_scores["cd"] += 1
    if ep_max > 20:
        reba_scores["ep"] += 1
        if ep_max > 45:
            reba_scores["ep"] += 2
            if ep_max > 90:
                reba_scores["ep"] += 2
    if cou_min < 150:
        reba_scores["cou"] += 1
    if cou_max > 170:
        reba_scores["cou"] += 1

    if mass_value != "inf5":
        if mass_value == "5e10":
            reba_scores["effort"] += 1
        elif mass_value == "sup10":
            reba_scores["effort"] += 2
    if masscheck_value == 1:
        reba_scores["effort"] += 1

    if prise_value != "Très bonne":
        if prise_value == "Acceptable":
            reba_scores["prise"] += 1
        elif prise_value == "Possible":
            reba_scores["prise"] += 2
        elif prise_value == "Dangereuse":
            reba_scores["prise"] += 3

    if activite_value1 == 1:
        reba_scores["activite"] += 1
    if activite_value2 == 1:
        reba_scores["activite"] += 1
    if activite_value3 == 1 or activite_value4 == 1:
        reba_scores["activite"] += 1
    
    reba_scores["A"] = tab_A[reba_scores["cou"]][reba_scores["jambes"]][reba_scores["tronc"]]
    reba_scores["A_2"] = reba_scores["A"] + reba_scores["effort"]
    reba_scores["B"] = tab_B[reba_scores["cd"]][reba_scores["pd"]][reba_scores["ep"]]
    reba_scores["B_2"] = reba_scores["B"] + reba_scores["prise"]
    reba_scores["C"] = tab_C[reba_scores["B_2"]][reba_scores["A_2"]]
    reba_scores["final"] = reba_scores["C"] + reba_scores["activite"]

    # Ajouter des labels pour chaque donnée
    tk.Label(analysis_window, text=f"Nombre total de mouvements détectés : {movement_count}", font=("Arial", 14), bg="#f5f5f5", fg="#333").pack(pady=10)
    correct_movements = movement_count * 0.9
    ocra_score = movement_count/correct_movements
    tk.Label(analysis_window, text=f"Score OCRA : {ocra_score:.2f}", font=("Arial", 14), bg="#f5f5f5", fg="#333").pack(pady=10)
    percentage = (movement_count / min_moves_value) * 100
    label_text = f"Utilisation de la machine : "
    if percentage <= 100:
        color = "green"
    elif percentage <= 120:
        color = "yellow"
    elif percentage <= 150:
        color = "orange"
    elif percentage <= 180:
        color = "red"
    elif percentage > 200:
        color = "purple"

    # Créez une première étiquette pour la partie du texte avant le nombre
    label = tk.Label(analysis_window, text=label_text, font=("Arial", 14))
    label.pack(pady=5)

    # Créez une deuxième étiquette pour afficher le pourcentage avec une couleur différente
    percentage_label = tk.Label(analysis_window, text=f"{percentage:.2f}%", font=("Arial", 14), fg=color)
    percentage_label.pack(pady=5, anchor='center')
    tab_reba = []
    parties_corps = [
        ("Nuque", "cou", "3"),
        ("Épaule", "ep", "6"),
        ("Coude", "cd", "2"),
        ("Poignet", "pd", "3"),
        ("Tronc", "tronc", "5"),
        ("Jambes", "jambes", "4"),
        ("Effort", "effort", "3"),
        ("Prise", "prise", "3"),
        ("Activité", "activite", "3"),
        ("Final", "final", "15"),
    ]
    for label, key, scoreMax in parties_corps:
        case_score = tk.Label(
            analysis_window,
            text=f"{label} : {reba_scores[key]}/{scoreMax}",
            bg=tab_bg[key][reba_scores[key]],
            font=("Arial", 10),
            width=20
        )
        case_score.pack(pady=5)
        tab_reba.append(case_score)
    

# Fenêtre principale
root = tk.Tk()
root.title("Récupération des données")
root.geometry("800x700")
root.configure(bg="#f9f9f9")

# Variables
csv_file_var = tk.StringVar()
video_file_var = tk.StringVar()
mass_var = tk.StringVar(value="inf5")
masscheck_var = tk.IntVar()
min_moves_var = tk.StringVar()
prise_var = tk.StringVar(value="Très bonne")
activite_var1 = tk.IntVar()
activite_var2 = tk.IntVar()
activite_var3 = tk.IntVar()
activite_var4 = tk.IntVar()

# Widgets
frame = tk.Frame(root, padx=20, pady=20, bg="#f9f9f9")
frame.pack(fill="both", expand=True)

# Champ pour sélectionner un fichier CSV
csv_label = tk.Label(frame, text="Fichier CSV :", bg="#f9f9f9", font=("Arial", 12))
csv_label.grid(row=0, column=0, sticky="w", pady=5)
csv_button = tk.Button(frame, text="Choisir un fichier", command=browse_csv, bg="#2196F3", fg="white", padx=10, pady=5)
csv_button.grid(row=0, column=1, pady=5)
csv_entry = tk.Entry(frame, textvariable=csv_file_var, width=40, state="readonly", font=("Arial", 10))
csv_entry.grid(row=0, column=2, pady=5)

# Champ pour sélectionner un fichier vidéo
video_label = tk.Label(frame, text="Fichier vidéo (optionnel) :", bg="#f9f9f9", font=("Arial", 12))
video_label.grid(row=1, column=0, sticky="w", pady=5)
video_button = tk.Button(frame, text="Choisir un fichier", command=browse_video, bg="#2196F3", fg="white", padx=10, pady=5)
video_button.grid(row=1, column=1, pady=5)
video_entry = tk.Entry(frame, textvariable=video_file_var, width=40, state="readonly", font=("Arial", 10))
video_entry.grid(row=1, column=2, pady=5)

# Champ pour le nombre minimum de mouvements
min_moves_label = tk.Label(frame, text="Nb min de mouvements :", bg="#f9f9f9", font=("Arial", 12))
min_moves_label.grid(row=2, column=0, sticky="w", pady=5)
min_moves_entry = tk.Entry(frame, textvariable=min_moves_var, width=20, font=("Arial", 10))
min_moves_entry.grid(row=2, column=1, pady=5)

# Boutons radio pour la masse
mass_label = tk.Label(frame, text="Masse de la charge :", bg="#f9f9f9", font=("Arial", 12))
mass_label.grid(row=3, column=0, sticky="w", pady=5)
mass_radiobutton1 = tk.Radiobutton(frame, text="inf. à 5kg", variable=mass_var, value="inf5", bg="#f9f9f9", font=("Arial", 10))
mass_radiobutton1.grid(row=3, column=1, sticky="w", pady=5)
mass_radiobutton2 = tk.Radiobutton(frame, text="entre 5 et 10kg", variable=mass_var, value="5e10", bg="#f9f9f9", font=("Arial", 10))
mass_radiobutton2.grid(row=4, column=1, sticky="w", pady=5)
mass_radiobutton3 = tk.Radiobutton(frame, text="sup. à 10kg", variable=mass_var, value="sup10", bg="#f9f9f9", font=("Arial", 10))
mass_radiobutton3.grid(row=5, column=1, sticky="w", pady=5)
mass_checkbutton = tk.Checkbutton(frame, text="Chocs, chgmt de posture violents, répétitivité", variable=masscheck_var, bg="#f9f9f9", font=("Arial", 10))
mass_checkbutton.grid(row=6, column=1, sticky="w", pady=5)
empty_label1 = tk.Label(frame, text="", bg="#f9f9f9")
empty_label1.grid(row=7, column=0, sticky="w", pady=5)

# Boutons radio pour la prise
prise_label = tk.Label(frame, text="Prise :", bg="#f9f9f9", font=("Arial", 12))
prise_label.grid(row=8, column=0, sticky="w", pady=5)
prise_radiobutton1 = tk.Radiobutton(frame, text="Très bonne", variable=prise_var, value="Très bonne", bg="#f9f9f9", font=("Arial", 10))
prise_radiobutton1.grid(row=8, column=1, sticky="w", pady=5)
prise_radiobutton2 = tk.Radiobutton(frame, text="Acceptable", variable=prise_var, value="Acceptable", bg="#f9f9f9", font=("Arial", 10))
prise_radiobutton2.grid(row=9, column=1, sticky="w", pady=5)
prise_radiobutton3 = tk.Radiobutton(frame, text="Possible", variable=prise_var, value="Possible", bg="#f9f9f9", font=("Arial", 10))
prise_radiobutton3.grid(row=10, column=1, sticky="w", pady=5)
prise_radiobutton4 = tk.Radiobutton(frame, text="Dangereuse", variable=prise_var, value="Dangereuse", bg="#f9f9f9", font=("Arial", 10))
prise_radiobutton4.grid(row=11, column=1, sticky="w", pady=5)
empty_label2 = tk.Label(frame, text="", bg="#f9f9f9")
empty_label2.grid(row=12, column=0, sticky="w", pady=5)

# Boutons check pour l'activité
activite_label = tk.Label(frame, text="Activité :", bg="#f9f9f9", font=("Arial", 12))
activite_label.grid(row=13, column=0, sticky="w", pady=5)
activite_checkbutton1 = tk.Checkbutton(frame, text="Statique (> 1min)", variable=activite_var1, bg="#f9f9f9", font=("Arial", 10))
activite_checkbutton1.grid(row=13, column=1, sticky="w", pady=5)
activite_checkbutton2 = tk.Checkbutton(frame, text="Répétée (+ de 4 fois/min)", variable=activite_var2, bg="#f9f9f9", font=("Arial", 10))
activite_checkbutton2.grid(row=14, column=1, sticky="w", pady=5)
activite_checkbutton3 = tk.Checkbutton(frame, text="Base instable", variable=activite_var3, bg="#f9f9f9", font=("Arial", 10))
activite_checkbutton3.grid(row=15, column=1, sticky="w", pady=5)
activite_checkbutton4 = tk.Checkbutton(frame, text="Larges/rapides changements de posture", variable=activite_var4, font=("Arial", 10))
activite_checkbutton4.grid(row=16, column=1, sticky="w", pady=5)

# Bouton de validation
validate_button = tk.Button(frame, text="Lancer l'analyse", command=validate_and_proceed)
validate_button.grid(row=17, column=0, columnspan=3, pady=20)

# Lancement de l'application
root.mainloop()