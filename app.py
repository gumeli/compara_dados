import csv
import io
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def detect_separator(text):
    first_line = text.replace("\ufeff", "", 1).splitlines()[0] if text else ""
    candidates = ("\t", ";", ",")
    return max(
        candidates,
        key=lambda candidate: len(split_row(first_line, candidate)),
    )


def split_row(line, separator):
    fields = []
    current = []
    quoted = False
    index = 0

    while index < len(line):
        char = line[index]
        if char == '"':
            if quoted and index + 1 < len(line) and line[index + 1] == '"':
                current.append('"')
                index += 2
                continue
            quoted = not quoted
        elif char == separator and not quoted:
            fields.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1

    fields.append("".join(current).strip())
    return fields


def parse_data(text):
    text = text.replace("\ufeff", "", 1)
    if not text.strip():
        return []

    separator = detect_separator(text)
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(split_row(line, separator))
    return rows


def normalize(value, case_sensitive):
    text = str(value).strip()
    return text if case_sensitive else text.lower()


def identity(row, mode, key_index, case_sensitive):
    if mode == "key":
        column = max(0, key_index - 1)
        value = row[column] if column < len(row) else ""
        return normalize(value, case_sensitive)
    return "\x01".join(normalize(value, case_sensitive) for value in row)


def compare_data(
    rows_a,
    rows_b,
    mode="exact",
    key_index=1,
    case_sensitive=False,
):
    seen = set()
    unique = []
    removed = []

    ids_a = {
        identity(row, mode, key_index, case_sensitive)
        for row in rows_a
    }
    ids_b = {
        identity(row, mode, key_index, case_sensitive)
        for row in rows_b
    }

    for row in [*rows_a, *rows_b]:
        row_identity = identity(row, mode, key_index, case_sensitive)
        if row_identity in seen:
            removed.append(row)
        else:
            seen.add(row_identity)
            unique.append(row)

    only_a = [
        row
        for row in rows_a
        if identity(row, mode, key_index, case_sensitive) not in ids_b
    ]
    only_b = [
        row
        for row in rows_b
        if identity(row, mode, key_index, case_sensitive) not in ids_a
    ]

    return {
        "unique": unique,
        "removed": removed,
        "onlyA": only_a,
        "onlyB": only_b,
    }


def rows_to_csv(rows):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerows(rows)
    return "\ufeff" + buffer.getvalue()


class ComparisonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Comparar dados")
        self.geometry("1180x760")
        self.minsize(760, 620)
        self.result_sets = {}
        self.configure(padx=24, pady=20)

        self.create_header()
        self.create_data_panels()
        self.create_controls()
        self.create_results()
        self.update_counts()

    def create_header(self):
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)

        title = ttk.Label(
            header,
            text="Comparar dados",
            font=("Georgia", 28, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        clear_button = ttk.Button(
            header,
            text="Limpar tudo",
            command=self.clear_all,
        )
        clear_button.grid(row=0, column=1)

    def create_data_panels(self):
        panels = ttk.Frame(self)
        panels.grid(row=1, column=0, sticky="nsew")
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(4, weight=1)

        self.data_a = self.create_text_panel(
            panels,
            "1",
            "Conjunto A",
            0,
        )
        self.data_b = self.create_text_panel(
            panels,
            "2",
            "Conjunto B",
            1,
        )

    def create_text_panel(self, parent, number, heading, column):
        panel = ttk.LabelFrame(parent, text=f"{number}  {heading}", padding=12)
        panel.grid(row=0, column=column, sticky="nsew", padx=(0, 8 if column == 0 else 0), pady=0)
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(panel)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(0, weight=1)

        count_label = ttk.Label(toolbar, text="0 linhas")
        count_label.grid(row=0, column=0, sticky="w")

        text = tk.Text(
            panel,
            wrap="none",
            width=48,
            height=12,
            font=("Consolas", 11),
        )
        text.grid(row=1, column=0, sticky="nsew")

        return text, count_label

    def create_controls(self):
        controls = ttk.Frame(self)
        controls.grid(row=2, column=0, sticky="ew", pady=(16, 0))

        ttk.Label(controls, text="Modo de comparação").grid(row=0, column=0, sticky="w")
        self.mode = ttk.Combobox(
            controls,
            state="readonly",
            values=["Linha completa", "Coluna-chave"],
            width=18,
        )
        self.mode.current(0)
        self.mode.grid(row=1, column=0, padx=(0, 12), sticky="w")
        self.mode.bind("<<ComboboxSelected>>", self.toggle_key_field)

        ttk.Label(controls, text="Número da coluna-chave").grid(row=0, column=1, sticky="w")
        self.key_index = tk.Spinbox(
            controls,
            from_=1,
            to=999,
            width=8,
        )
        self.key_index.delete(0, "end")
        self.key_index.insert(0, "1")
        self.key_index.grid(row=1, column=1, padx=(0, 12), sticky="w")

        self.case_sensitive = tk.BooleanVar(value=False)
        case_check = ttk.Checkbutton(
            controls,
            text="Diferenciar maiúsculas e minúsculas",
            variable=self.case_sensitive,
        )
        case_check.grid(row=1, column=2, padx=(0, 12), sticky="w")

        compare_button = ttk.Button(
            controls,
            text="Comparar e limpar",
            command=self.compare,
        )
        compare_button.grid(row=1, column=3, sticky="e")
        controls.columnconfigure(3, weight=1)

        import_a = ttk.Button(
            controls,
            text="Importar A",
            command=lambda: self.import_file(self.data_a),
        )
        import_a.grid(row=0, column=4, rowspan=2, padx=(12, 4), sticky="e")

        import_b = ttk.Button(
            controls,
            text="Importar B",
            command=lambda: self.import_file(self.data_b),
        )
        import_b.grid(row=0, column=5, rowspan=2, sticky="e")

        self.data_a[0].bind("<<Modified>>", lambda _event: self.on_text_modified(self.data_a))
        self.data_b[0].bind("<<Modified>>", lambda _event: self.on_text_modified(self.data_b))
        self.toggle_key_field()

    def create_results(self):
        self.results_frame = ttk.Frame(self)
        self.results_frame.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        self.results_frame.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=2)

        self.notebook = ttk.Notebook(self.results_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.results_frame.rowconfigure(0, weight=1)

        self.tabs = {}
        tab_names = (
            ("unique", "Resultado único"),
            ("removed", "Removidos"),
            ("onlyA", "Só em A"),
            ("onlyB", "Só em B"),
        )
        for key, title in tab_names:
            frame = ttk.Frame(self.notebook)
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)

            tree = ttk.Treeview(
                frame,
                columns=("number", "data"),
                show="headings",
                height=12,
            )
            tree.heading("number", text="#")
            tree.heading("data", text=title)
            tree.column("number", width=60, stretch=False)
            tree.column("data", width=900)
            tree.grid(row=0, column=0, sticky="nsew")

            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.grid(row=0, column=1, sticky="ns")

            self.notebook.add(frame, text=title)
            self.tabs[key] = tree

        download_button = ttk.Button(
            self.results_frame,
            text="Baixar resultado CSV",
            command=self.download_csv,
        )
        download_button.grid(row=1, column=0, sticky="w", pady=(10, 0))

    def on_text_modified(self, panel):
        text_widget = panel[0]
        if text_widget.edit_modified():
            text_widget.edit_modified(False)
            self.update_counts()

    def update_counts(self):
        count_a = len(parse_data(self.data_a[0].get("1.0", "end")))
        count_b = len(parse_data(self.data_b[0].get("1.0", "end")))
        self.data_a[1].configure(
            text=f"{count_a} linha{'s' if count_a != 1 else ''}"
        )
        self.data_b[1].configure(
            text=f"{count_b} linha{'s' if count_b != 1 else ''}"
        )

    def import_file(self, panel):
        path = filedialog.askopenfilename(
            title="Importar dados",
            filetypes=[
                ("Dados", "*.csv *.txt *.tsv"),
                ("CSV", "*.csv"),
                ("Texto", "*.txt"),
                ("TSV", "*.tsv"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as file:
                text = file.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="latin-1", newline="") as file:
                text = file.read()
        except OSError as error:
            messagebox.showerror("Erro ao importar", str(error))
            return

        text_widget = panel[0]
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", text)
        text_widget.edit_modified(False)
        self.update_counts()

    def toggle_key_field(self, _event=None):
        if self.mode.get() == "Coluna-chave":
            self.key_index.configure(state="normal")
        else:
            self.key_index.configure(state="disabled")

    def compare(self):
        text_a = self.data_a[0].get("1.0", "end")
        text_b = self.data_b[0].get("1.0", "end")
        rows_a = parse_data(text_a)
        rows_b = parse_data(text_b)

        if not rows_a and not rows_b:
            messagebox.showwarning(
                "Dados vazios",
                "Cole ou importe dados em pelo menos um conjunto.",
            )
            return

        try:
            key_index = int(self.key_index.get())
        except ValueError:
            key_index = 1

        mode = "key" if self.mode.get() == "Coluna-chave" else "exact"
        self.result_sets = compare_data(
            rows_a,
            rows_b,
            mode=mode,
            key_index=key_index,
            case_sensitive=self.case_sensitive.get(),
        )
        self.render_results()

    def render_results(self):
        headings = {
            "unique": "Dados únicos",
            "removed": "Duplicados removidos",
            "onlyA": "Somente em A",
            "onlyB": "Somente em B",
        }

        counts = {
            "unique": len(self.result_sets["unique"]),
            "removed": len(self.result_sets["removed"]),
            "onlyA": len(self.result_sets["onlyA"]),
            "onlyB": len(self.result_sets["onlyB"]),
        }

        for key, tree in self.tabs.items():
            tree.delete(*tree.get_children())
            for index, row in enumerate(self.result_sets[key], start=1):
                tree.insert("", "end", values=(index, " | ".join(row)))

            tab_title = (
                f"{headings[key]} ({counts[key]})"
            )
            tab_index = list(self.tabs).index(key)
            self.notebook.tab(tab_index, text=tab_title)

    def download_csv(self):
        rows = self.result_sets.get("unique", [])
        if not rows:
            messagebox.showwarning(
                "Sem resultado",
                "Execute uma comparação antes de baixar o arquivo.",
            )
            return

        path = filedialog.asksaveasfilename(
            title="Salvar dados únicos",
            defaultextension=".csv",
            initialfile="dados_unicos.csv",
            filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as file:
                file.write(rows_to_csv(rows))
        except OSError as error:
            messagebox.showerror("Erro ao salvar", str(error))

    def clear_all(self):
        self.data_a[0].delete("1.0", "end")
        self.data_b[0].delete("1.0", "end")
        self.result_sets = {}
        self.update_counts()
        for tree in self.tabs.values():
            tree.delete(*tree.get_children())


if __name__ == "__main__":
    app = ComparisonApp()
    app.mainloop()
