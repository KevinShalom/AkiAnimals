import tkinter as tk
from tkinter import ttk, messagebox
import random, os
from collections import Counter


def cargar_conocimiento(ruta="animales.pl"):
    conocimiento = {}
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if "(" in linea and ")" in linea:
                hecho = linea.strip(".\n")
                pred, vals = hecho.split("(", 1)
                args = [a.strip() for a in vals.rstrip(")").split(",")]

                animal = args[0]
                conocimiento.setdefault(
                    animal, {"clase": None, "subclase": None, "caracteristicas": []}
                )
                if pred == "clase":
                    conocimiento[animal]["clase"] = args[1]
                elif pred == "subclase":
                    conocimiento[animal]["subclase"] = args[1]
                elif pred == "caracteristica":
                    conocimiento[animal]["caracteristicas"].append(args[1])
    return conocimiento


class AkinatorGUI(tk.Tk):
    def __init__(self, conocimiento):
        super().__init__()
        self.title("Akinator de Animales")
        self.minsize(900, 600)
        self.geometry("1000x650")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.conocimiento = conocimiento
        self._build_widgets()
        self._init_state()
        self._fill_animal_list()

    def _build_widgets(self):
        list_frame = ttk.Frame(self)
        list_frame.grid(row=0, column=0, sticky="nsw", padx=8, pady=8)
        list_frame.rowconfigure(1, weight=1)

        ttk.Label(list_frame, text="Animales disponibles").grid(row=0, column=0)
        self.animal_lb = tk.Listbox(list_frame, width=28)
        self.animal_lb.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.animal_lb.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.animal_lb.configure(yscrollcommand=sb.set)

        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        self.info_txt = tk.Text(main_frame, height=8, wrap="word", state=tk.DISABLED)
        self.info_txt.grid(row=0, column=0, sticky="nsew")

        self.img_lbl = ttk.Label(main_frame)
        self.img_lbl.grid(row=1, column=0, sticky="n", pady=(30, 10))

        self.question_lbl = ttk.Label(main_frame, text="", font=("Helvetica", 15))
        self.question_lbl.grid(row=2, column=0, pady=12)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0)
        self.yes_btn = ttk.Button(btn_frame, text="Sí", width=12, command=lambda: self._answer(True))
        self.no_btn = ttk.Button(btn_frame, text="No", width=12, command=lambda: self._answer(False))
        self.yes_btn.grid(row=0, column=0, padx=8)
        self.no_btn.grid(row=0, column=1, padx=8)

        self.start_btn = ttk.Button(main_frame, text="Comenzar preguntas", command=self._start_game)
        self.start_btn.grid(row=4, column=0, pady=(20, 5))

    def _init_state(self):
        self.phase = "inicio"
        self.clase_confirmada = self.subclase_confirmada = None
        self.candidatos = []
        self.caracteristicas_ordenadas = []
        self.respuestas = {}
        self.char_index = 0
        self._enable_yesno(False)
        self.img_lbl.config(image="")
        self.photo_cache = None

    def _enable_yesno(self, enable):
        state = tk.NORMAL if enable else tk.DISABLED
        self.yes_btn["state"] = self.no_btn["state"] = state

    def _set_info(self, text):
        self.info_txt.config(state=tk.NORMAL)
        self.info_txt.delete("1.0", tk.END)
        self.info_txt.insert(tk.END, text)
        self.info_txt.config(state=tk.DISABLED)

    def _fill_animal_list(self):
        for a in sorted(self.conocimiento):
            self.animal_lb.insert(tk.END, a.capitalize())

    def _start_game(self):
        sel = self.animal_lb.get(tk.ACTIVE)
        if not sel:
            messagebox.showinfo("Akinator", "Selecciona un animal primero.")
            return

        key = sel.lower()
        info = self.conocimiento[key]
        self._set_info(
            f"Información de {sel}:\n"
            f"  • Clase: {info['clase']}\n"
            f"  • Subclase: {info['subclase']}\n"
            f"  • Características: {', '.join(info['caracteristicas'])}"
        )
        self.phase = "clase"
        self.clases_iter = iter(sorted({d["clase"] for d in self.conocimiento.values()}))
        self._ask_next()

    def _ask_next(self):
        if self.phase == "clase":
            try:
                c = next(self.clases_iter)
                self.current_q = ("clase", c)
                self.question_lbl["text"] = f"¿Es un {c}?"
                self._enable_yesno(True)
            except StopIteration:
                self._finish("No pude determinar la clase.")
        elif self.phase == "subclase":
            try:
                s = next(self.sub_iter)
                self.current_q = ("subclase", s)
                self.question_lbl["text"] = f"¿Pertenece a la subclase {s}?"
                self._enable_yesno(True)
            except StopIteration:
                self._finish("No pude determinar la subclase.")
        elif self.phase == "caracteristicas":
            while self.char_index < len(self.caracteristicas_ordenadas):
                c = self.caracteristicas_ordenadas[self.char_index]
                self.char_index += 1
                if c not in self.respuestas:
                    self.current_q = ("caracteristica", c)
                    self.question_lbl["text"] = f"¿Tiene la característica {c}?"
                    self._enable_yesno(True)
                    return
            self._evaluate_candidates()
        elif self.phase == "adivinanza":
            a = self.best_animal.capitalize()
            self.current_q = ("adivinanza", a)
            self.question_lbl["text"] = f"¿Estás pensando en un {a}?"
            self._enable_yesno(True)

    def _answer(self, yes):
        self._enable_yesno(False)
        qtype, val = self.current_q

        if qtype == "clase":
            if yes:
                self.clase_confirmada = val
                self.sub_iter = iter(
                    sorted({d["subclase"] for d in self.conocimiento.values() if d["clase"] == val})
                )
                self.phase = "subclase"
        elif qtype == "subclase":
            if yes:
                self.subclase_confirmada = val
                self.candidatos = [
                    a for a, inf in self.conocimiento.items()
                    if inf["clase"] == self.clase_confirmada and inf["subclase"] == self.subclase_confirmada
                ]
                if not self.candidatos:
                    self._finish("No hay coincidencias con esa subclase.")
                    return
                todas = list(set(
                    c for a in self.candidatos for c in self.conocimiento[a]["caracteristicas"]
                    if c not in self.respuestas
                ))
                random.shuffle(todas)
                MAX_PREGUNTAS = 15
                self.caracteristicas_ordenadas = todas[:MAX_PREGUNTAS]
                self.phase = "caracteristicas"
                self.char_index = 0
        elif qtype == "caracteristica":
            self.respuestas[val] = yes
        elif qtype == "adivinanza":
            if yes:
                self._show_image(val.lower())
                self._finish("¡Genial! Lo Adivine")
            else:
                self._finish("Vaya, no lo adiviné.")
            return

        self.after(200, self._ask_next)

    def _evaluate_candidates(self):
        best_score, best = -1, None
        for a in self.candidatos:
            score = sum(1 for c in self.conocimiento[a]["caracteristicas"] if self.respuestas.get(c, False))
            if score > best_score:
                best_score, best = score, a
        if best is None:
            self._finish("No pude adivinar.")
        else:
            self.best_animal = best
            self.phase = "adivinanza"
            self._ask_next()

    def _finish(self, msg):
        self.question_lbl["text"] = msg
        self._enable_yesno(False)

    def _show_image(self, animal_name):
        try:
            from PIL import Image, ImageTk
        except ImportError:
            messagebox.showerror("Error", "Pillow no está instalado. Ejecuta: pip install pillow")
            return

        candidatos = [
            f"{animal_name}.png",
            f"{animal_name}.gif",
            f"{animal_name}.jpg",
            f"{animal_name}.jpeg",
        ]
        ruta = next((os.path.join("images", f) for f in candidatos if os.path.exists(os.path.join("images", f))), None)
        if not ruta:
            return

        try:
            if ruta.endswith((".png", ".gif")):
                photo = tk.PhotoImage(file=ruta)
            else:
                img = Image.open(ruta)
                img.thumbnail((450, 300))
                photo = ImageTk.PhotoImage(img)
        except Exception as e:
            print("Error cargando imagen:", e)
            return

        self.photo_cache = photo
        self.img_lbl.config(image=photo)


if __name__ == "__main__":
    datos = cargar_conocimiento("animales.pl")
    app = AkinatorGUI(datos)
    app.mainloop()
