import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from datetime import datetime, timedelta
import threading
import webbrowser

# Cache des arrêts
stops_dict = {}

def load_stops_for_line(line):
    if line in stops_dict:
        return
    try:
        r = requests.get(f"https://data.mobilites-m.fr/api/routers/default/index/routes/SEM:{line}/clusters")
        stops = r.json()
        for s in stops:
            name = s['name']
            full = f"{s['id']}::{s['lat']},{s['lon']}"
            stops_dict[name.lower()] = (full, name)
    except:
        pass

# Charger les arrêts des lignes communes
all_lines = []
try:
    r = requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes")
    routes = r.json()
    for route in routes:
        if route.get('id', '').startswith('SEM:'):
            line = route['id'][4:]  # remove SEM:
            all_lines.append(line)
except:
    all_lines = ['E', 'A', 'C1', 'C2', 'B']  # fallback

for line in all_lines:
    load_stops_for_line(line)

# Ajouter des arrêts connus manuellement
stops_dict["pont de vence"] = ("SEM:GENPTVENCE::45.23009,5.6823", "Pont de Vence")
stops_dict["alsace lorraine"] = ("SEM:GENALSACELO::45.18911,5.7193", "Alsace Lorraine")
stops_dict["neron"] = ("SEM:NERON::45.21782,5.69334", "Néron")
stops_dict["néron"] = ("SEM:NERON::45.21782,5.69334", "Néron")

# Mapping des lignes courtes vers les noms complets des routes
line_names = {
    "E": "Fontanil-Cornillon Palluel / Grenoble Louise Michel",
    # Ajouter d'autres lignes si besoin
}

def search_stop(query):
    query = query.strip().lower()
    if not query:
        return None, None

    # Recherche dans le cache
    if query in stops_dict:
        return stops_dict[query]

    # Recherche floue : si le nom contient la query ou vice versa
    for name_lower, (full, name) in stops_dict.items():
        if query in name_lower or name_lower in query:
            return full, name

    # Fallback : texte brut
    return query, query

class TAGApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TAG Express - Calculateur d'Itinéraires")
        self.root.geometry("760x510")

        # lien Github (modifiez ici)
        self.github_url = "https://github.com/PALMINE"  # à changer avec votre profil

        # bouton haut-droite
        top_frame = ttk.Frame(root)
        top_frame.grid(row=0, column=2, padx=4, pady=4, sticky='ne')
        self.github_btn = ttk.Button(top_frame, text="Made by Palmine", command=self.open_github)
        self.github_btn.pack()

        # Variables
        self.fromPlace = ""
        self.toPlace = ""
        self.ligne = ""
        self.time_offset = 0
        self.results = []

        # Widgets
        ttk.Label(root, text="Départ:").grid(row=0, column=0, sticky="w", padx=6, pady=2)
        self.dep_entry = ttk.Entry(root, width=28)
        self.dep_entry.grid(row=0, column=1, padx=6, pady=2)

        ttk.Label(root, text="Arrivée:").grid(row=1, column=0, sticky="w", padx=6, pady=2)
        self.arr_entry = ttk.Entry(root, width=28)
        self.arr_entry.grid(row=1, column=1, padx=6, pady=2)

        # auto-complétion de nom d'arrêt
        self.suggestion_box = tk.Listbox(root, height=5)
        self.suggestion_box.bind("<ButtonRelease-1>", self._fill_from_suggestion)

        for entry in [self.dep_entry, self.arr_entry]:
            entry.bind("<KeyRelease>", self.on_entry_keyrelease)
            entry.bind("<Return>", lambda e: self.search())
            entry.bind("<Tab>", self.on_entry_tab)

        ttk.Label(root, text="Ligne (optionnel):").grid(row=2, column=0, sticky="w", padx=6, pady=2)
        self.line_entry = ttk.Entry(root, width=28)
        self.line_entry.grid(row=2, column=1, padx=6, pady=2)
        self.line_entry.bind("<Return>", lambda e: self.search())

        # compact buttons
        button_frame = ttk.Frame(root)
        button_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky='ew')

        self.search_btn = ttk.Button(button_frame, text="Rechercher", command=self.search)
        self.load_more_btn = ttk.Button(button_frame, text="+1h", command=self.load_more, state="disabled")
        self.list_stops_btn = ttk.Button(button_frame, text="Lister arrêts", command=self.list_stops)
        self.new_search_btn = ttk.Button(button_frame, text="Réinitialiser", command=self.new_search)

        self.search_btn.grid(row=0, column=0, padx=2)
        self.load_more_btn.grid(row=0, column=1, padx=2)
        self.list_stops_btn.grid(row=0, column=2, padx=2)
        self.new_search_btn.grid(row=0, column=3, padx=2)
        self.load_more_btn.grid_remove()  # Masqué jusqu'à la première recherche réussie

        self.results_tree = ttk.Treeview(root, columns=("ligne", "direction", "dep", "arr", "dur", "type"), show="headings", height=9)
        self.results_tree.heading("ligne", text="LIGNE")
        self.results_tree.heading("direction", text="Direction")
        self.results_tree.heading("dep", text="Départ")
        self.results_tree.heading("arr", text="Arrivée")
        self.results_tree.heading("dur", text="Durée")
        self.results_tree.heading("type", text="Type")
        self.results_tree.column("ligne", width=60, anchor="center")
        self.results_tree.column("direction", width=280, anchor="w")
        self.results_tree.column("dep", width=90, anchor="center")
        self.results_tree.column("arr", width=90, anchor="center")
        self.results_tree.column("dur", width=70, anchor="center")
        self.results_tree.column("type", width=110, anchor="center")
        self.results_tree.grid(row=4, column=0, columnspan=2, padx=4, pady=2, sticky="nsew")

        # Scrollbar collée au tableau droit
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=4, column=2, sticky="ns", pady=2)

        # Make resizable
        root.rowconfigure(4, weight=1)
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)

    def _update_load_more_button_text(self):
        if not hasattr(self, 'search_base_time') or self.search_base_time is None:
            return
        next_time = self.search_base_time + timedelta(hours=self.time_offset + 1)
        self.load_more_btn.config(text=f"Rechercher pour après {next_time.strftime('%H:%M')} (+{self.time_offset+1}h)")
        self.load_more_btn.grid()

    def open_github(self):
        webbrowser.open(self.github_url)

    def search(self):
        dep = self.dep_entry.get().strip()
        arr = self.arr_entry.get().strip()
        ligne = self.line_entry.get().strip().upper()

        fromPlace, dep_name = search_stop(dep)
        toPlace, arr_name = search_stop(arr)

        if "::" not in fromPlace:
            messagebox.showerror("Erreur", f"Arrêt de départ '{dep}' non trouvé.")
            return
        if "::" not in toPlace:
            messagebox.showerror("Erreur", f"Arrêt d'arrivée '{arr}' non trouvé.")
            return

        self.fromPlace = fromPlace
        self.toPlace = toPlace
        self.ligne = ligne
        self.time_offset = 0
        self.search_base_time = datetime.now()

        self.search_btn.config(state="disabled")

        threading.Thread(target=self.do_search).start()

    def list_stops(self):
        win = tk.Toplevel(self.root)
        win.title("Lister arrêts par ligne")
        win.geometry("560x450")

        ttk.Label(win, text="Ligne (E, A, C1...) :").pack(anchor="w", padx=10, pady=(10, 0))
        line_entry = ttk.Entry(win, width=18)
        line_entry.pack(anchor="w", padx=10, pady=(0, 10))

        columns = ("name", "cluster", "lat", "lon")
        stop_tree = ttk.Treeview(win, columns=columns, show='headings', height=16)
        stop_tree.heading("name", text="Nom")
        stop_tree.heading("cluster", text="Cluster ID")
        stop_tree.heading("lat", text="Lat")
        stop_tree.heading("lon", text="Lon")
        stop_tree.column("name", width=210, anchor="w")
        stop_tree.column("cluster", width=150, anchor="center")
        stop_tree.column("lat", width=80, anchor="center")
        stop_tree.column("lon", width=80, anchor="center")
        stop_tree.pack(fill="both", expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(win, orient="vertical", command=stop_tree.yview)
        stop_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        def show_stops(event=None):
            line = line_entry.get().strip().upper()
            if not line:
                messagebox.showerror("Erreur", "Entrez une ligne valide.")
                return

            try:
                r = requests.get(f"https://data.mobilites-m.fr/api/routers/default/index/routes/SEM:{line}/clusters", timeout=8)
                stops = r.json()
                if not stops:
                    messagebox.showinfo("Info", f"Aucun arrêt trouvé pour la ligne {line}.")
                    for item in stop_tree.get_children():
                        stop_tree.delete(item)
                    return
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de lister la ligne {line} : {e}")
                return

            for item in stop_tree.get_children():
                stop_tree.delete(item)

            for s in stops:
                stop_tree.insert("", "end", values=(s.get('name'), s.get('id'), s.get('lat'), s.get('lon')))

        line_entry.bind('<Return>', show_stops)
        line_entry.focus()

        stop_tree.bind('<Double-Button-1>', lambda event: self._fill_from_list_table(event, stop_tree))

        ttk.Button(win, text="Fermer", command=win.destroy).pack(pady=6)

    def _fill_from_list_table(self, event, tree):
        item = tree.selection()
        if not item:
            return
        values = tree.item(item[0], 'values')
        if not values:
            return
        name = values[0]
        choice = tk.Toplevel(self.root)
        choice.title("Choisir champ")
        choice.geometry("250x100")
        ttk.Label(choice, text=f"Utiliser '{name}' comme :").pack(pady=6)

        def choose_depart():
            self.dep_entry.delete(0, tk.END)
            self.dep_entry.insert(0, name)
            choice.destroy()

        def choose_arrivee():
            self.arr_entry.delete(0, tk.END)
            self.arr_entry.insert(0, name)
            choice.destroy()

        btn_frame = ttk.Frame(choice)
        btn_frame.pack(pady=4)
        ttk.Button(btn_frame, text="Départ", command=choose_depart).grid(row=0, column=0, padx=6)
        ttk.Button(btn_frame, text="Arrivée", command=choose_arrivee).grid(row=0, column=1, padx=6)



    def _fill_from_list(self, event, listbox):
        sel = listbox.curselection()
        if not sel:
            return
        text = listbox.get(sel[0])
        name = text.split('  |  ')[0]

        # Choix dépôt vs arrivée dans une mini popup
        choice = tk.Toplevel(self.root)
        choice.title("Choisir champ")
        choice.geometry("240x100")
        ttk.Label(choice, text=f"Sélection : {name}").pack(pady=5)

        def choose_depart():
            self.dep_entry.delete(0, tk.END)
            self.dep_entry.insert(0, name)
            choice.destroy()

        def choose_arrivee():
            self.arr_entry.delete(0, tk.END)
            self.arr_entry.insert(0, name)
            choice.destroy()

        ttk.Button(choice, text="Départ", command=choose_depart).pack(side="left", padx=10, pady=5)
        ttk.Button(choice, text="Arrivée", command=choose_arrivee).pack(side="right", padx=10, pady=5)

    def on_entry_keyrelease(self, event):
        widget = event.widget
        query = widget.get().strip().lower()

        # si correspond exactement à un arrêt, on masque la suggestion
        if query in stops_dict:
            self.suggestion_box.place_forget()
            return

        if not query:
            self.suggestion_box.place_forget()
            return

        matches = [name for name in stops_dict.keys() if query in name]
        if not matches:
            self.suggestion_box.place_forget()
            return

        self.suggestion_box.delete(0, tk.END)
        for name in matches[:10]:
            self.suggestion_box.insert(tk.END, stops_dict[name][1])

        x = widget.winfo_rootx() - self.root.winfo_rootx()
        y = widget.winfo_rooty() - self.root.winfo_rooty() + widget.winfo_height()
        self.suggestion_box.place(x=x, y=y, width=widget.winfo_width())
        self.suggestion_box.lift()

        self.active_entry = widget

    def _fill_from_suggestion(self, event):
        if not hasattr(self, 'active_entry') or not self.active_entry:
            return
        sel = self.suggestion_box.curselection()
        if not sel:
            return
        text = self.suggestion_box.get(sel[0])
        self.active_entry.delete(0, tk.END)
        self.active_entry.insert(0, text)
        self.suggestion_box.place_forget()

    def on_entry_tab(self, event):
        if self.suggestion_box.winfo_ismapped() and self.suggestion_box.size() > 0:
            text = self.suggestion_box.get(0)
            self.active_entry.delete(0, tk.END)
            self.active_entry.insert(0, text)
            self.suggestion_box.place_forget()
            return 'break'
        return None

    def do_search(self):
        # Clear tree
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        loading_text = f"Chargement des départs après +{self.time_offset}h..." if self.time_offset > 0 else "Calcul en cours..."
        self.results_tree.insert("", "end", values=("", loading_text, "", "", "", ""))

        base_time = getattr(self, 'search_base_time', None)
        if base_time is None:
            base_time = datetime.now()
            self.search_base_time = base_time
        search_time = base_time + timedelta(hours=self.time_offset)
        heure = search_time.strftime("%H:%M")
        date = base_time.strftime("%Y-%m-%d")

        self._update_load_more_button_text()

        params = {
            "fromPlace": self.fromPlace,
            "toPlace": self.toPlace,
            "time": heure,
            "date": date,
            "mode": "TRANSIT",
            "maxWalkDistance": "100",
            "walkSpeed": "1.5",
            "waitReluctance": "0.8",
            "locale": "fr",
            "numItineraries": "12"
        }

        try:
            r = requests.get("https://data.mobilites-m.fr/api/routers/default/plan", params=params, timeout=12)
            data = r.json()
            its = data.get("plan", {}).get("itineraries", [])

            self.results = its
            self.display_results()
        except Exception as e:
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.results_tree.insert("", "end", values=("", f"Erreur: {e}", "", "", "", ""))
            self.load_more_btn.config(state="disabled")
            self.load_more_btn.grid_remove()
        finally:
            self.search_btn.config(state="normal")

    def display_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        shown = 0
        for it in self.results:
            dur = round(it["duration"] / 60)
            if dur > 35: continue

            if self.ligne:
                target = self.ligne.upper()
                target_pattern = line_names.get(target, target).upper()
                leg_routes = []
                for leg in it["legs"]:
                    if leg["mode"] == "WALK":
                        continue
                    route_short = (leg.get("routeShortName") or "").replace("SEM:", "").upper()
                    route_id = (leg.get("routeId") or "").replace("SEM:", "").upper()
                    route = (leg.get("route") or "").replace("SEM:", "").upper()
                    for r in [route_short, route_id, route]:
                        if r:
                            leg_routes.append(r)
                # déduire de la route shortest name ou identifiant
                if not any(rt == target or rt == target_pattern or rt.startswith(target) for rt in leg_routes):
                    continue

            if "startTime" not in it or "endTime" not in it:
                continue
            try:
                dep_time = datetime.fromtimestamp(it["startTime"] / 1000).strftime("%H:%M")
                arr_time = datetime.fromtimestamp(it["endTime"] / 1000).strftime("%H:%M")
            except Exception:
                continue

            shown += 1
            legs = [leg for leg in it["legs"] if leg["mode"] != "WALK"]
            direct = len(legs) <= 1

            # direction = terminus dans le sens du trajet (headsign, ou seconde partie du nom de route)
            if legs:
                transit_leg = legs[0]
                headsign = (transit_leg.get('headsign') or '').strip()
                route_text = transit_leg.get('route') or ''
                if headsign:
                    direction = headsign
                elif '/' in route_text:
                    direction = route_text.split('/', 1)[1].strip()
                else:
                    direction = legs[-1]['to'].get('name', '?')

                # extraire ligne la plus fiable: routeShortName en priorité
                raw_route = transit_leg.get('routeShortName') or transit_leg.get('routeId') or route_text or ''
                if raw_route.startswith('SEM:'):
                    raw_route = raw_route.replace('SEM:', '')
                default_ligne = raw_route.strip() or '?'
            else:
                direction = "?"
                default_ligne = "?"

            ligne_display = (self.ligne.upper() if self.ligne.strip() else default_ligne)

            self.results_tree.insert("", "end", values=(ligne_display, direction, dep_time, arr_time, f"{dur} min", "DIRECT" if direct else "CORRESPONDANCE"))

        if shown == 0:
            self.results_tree.insert("", "end", values=("", "⚠️ Aucun itinéraire trouvé.", "", "", "", ""))
            self.load_more_btn.config(state="disabled")
            self.load_more_btn.grid_remove()
        else:
            self.load_more_btn.config(state="normal")
            self.load_more_btn.grid()
            self._update_load_more_button_text()

    def load_more(self):
        self.time_offset += 1
        self._update_load_more_button_text()
        self.load_more_btn.config(state="disabled")
        threading.Thread(target=self.do_search).start()

    def new_search(self):
        self.dep_entry.delete(0, tk.END)
        self.arr_entry.delete(0, tk.END)
        self.line_entry.delete(0, tk.END)
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.load_more_btn.config(state="disabled")
        self.load_more_btn.grid_remove()
        self.time_offset = 0
        self.search_base_time = None

if __name__ == "__main__":
    root = tk.Tk()
    app = TAGApp(root)
    root.mainloop()