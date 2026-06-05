"""
Сапёр (Minesweeper) на Python + tkinter.

Возможности:
  * Выбор сложности: Новичок / Любитель / Профи / Своя игра
  * Красивый минималистичный визуал с цветными цифрами
  * Кнопка-смайлик для перезапуска, таймер и счётчик мин
  * Первый клик всегда безопасен
  * Автораскрытие пустых областей (flood fill)
  * Флажки (правая кнопка мыши) и "аккорд" (двойной клик по открытой цифре)

Запуск:
    python saper.py
"""

import random
import tkinter as tk
from tkinter import messagebox

# --------------------------- Настройки уровней ---------------------------

DIFFICULTIES = {
    "Новичок":  {"rows": 9,  "cols": 9,  "mines": 10},
    "Любитель": {"rows": 16, "cols": 16, "mines": 40},
    "Профи":    {"rows": 16, "cols": 30, "mines": 99},
}

# --------------------------- Палитра / стиль -----------------------------

COLORS = {
    "bg":            "#1e2430",   # общий фон окна
    "panel":         "#2a3140",   # фон верхней панели
    "cell_hidden":   "#3d4659",   # закрытая клетка
    "cell_open":     "#222834",   # открытая клетка
    "cell_border":   "#161b24",
    "accent":        "#5da9e9",
    "text":          "#e6ebf2",
    "mine":          "#ff5c5c",
    "mine_bg":       "#7a2331",
    "flag":          "#ffcc4d",
    "display_bg":    "#0f1117",
    "display_fg":    "#ff5151",
}

# Классические цвета цифр сапёра
NUMBER_COLORS = {
    1: "#4fa3ff",
    2: "#42c97a",
    3: "#ff6b6b",
    4: "#a779ff",
    5: "#ffae42",
    6: "#39d0d8",
    7: "#e6ebf2",
    8: "#9aa6b8",
}


class Minesweeper:
    def __init__(self, root):
        self.root = root
        self.root.title("Сапёр")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        self.rows = 9
        self.cols = 9
        self.mines = 10
        self.difficulty_name = "Новичок"

        # состояние игры
        self.buttons = {}
        self.mine_positions = set()
        self.adjacent = {}
        self.revealed = set()
        self.flagged = set()
        self.first_click = True
        self.game_over = False
        self.timer_running = False
        self.seconds = 0

        self._build_menu_bar()
        self._build_top_panel()
        self.board_frame = tk.Frame(self.root, bg=COLORS["bg"], padx=10, pady=10)
        self.board_frame.pack()

        self.new_game(self.difficulty_name)

    # ----------------------------- UI -----------------------------------

    def _build_menu_bar(self):
        menubar = tk.Menu(self.root)
        game_menu = tk.Menu(menubar, tearoff=0)
        for name in DIFFICULTIES:
            game_menu.add_command(label=name, command=lambda n=name: self.new_game(n))
        game_menu.add_separator()
        game_menu.add_command(label="Своя игра…", command=self._custom_game_dialog)
        game_menu.add_separator()
        game_menu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Игра", menu=game_menu)
        self.root.config(menu=menubar)

    def _build_top_panel(self):
        self.panel = tk.Frame(self.root, bg=COLORS["panel"], padx=12, pady=10)
        self.panel.pack(fill="x", padx=10, pady=(10, 0))

        # счётчик мин
        self.mine_label = tk.Label(
            self.panel, text="010", font=("Consolas", 22, "bold"),
            bg=COLORS["display_bg"], fg=COLORS["display_fg"], width=4, padx=6,
        )
        self.mine_label.pack(side="left")

        # кнопка-смайлик (сброс)
        self.reset_button = tk.Button(
            self.panel, text="🙂", font=("Segoe UI Emoji", 18),
            bg=COLORS["cell_hidden"], activebackground=COLORS["accent"],
            relief="flat", width=3, command=lambda: self.new_game(self.difficulty_name),
        )
        self.reset_button.pack(side="left", expand=True)

        # таймер
        self.timer_label = tk.Label(
            self.panel, text="000", font=("Consolas", 22, "bold"),
            bg=COLORS["display_bg"], fg=COLORS["display_fg"], width=4, padx=6,
        )
        self.timer_label.pack(side="right")

    def _custom_game_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Своя игра")
        dialog.configure(bg=COLORS["bg"])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        fields = [("Строки (2-30):", 9), ("Столбцы (2-40):", 9), ("Мины:", 10)]
        entries = []
        for i, (label, default) in enumerate(fields):
            tk.Label(dialog, text=label, bg=COLORS["bg"], fg=COLORS["text"],
                     font=("Segoe UI", 11)).grid(row=i, column=0, sticky="w", padx=12, pady=6)
            e = tk.Entry(dialog, width=6, font=("Segoe UI", 11))
            e.insert(0, str(default))
            e.grid(row=i, column=1, padx=12, pady=6)
            entries.append(e)

        def start():
            try:
                rows = max(2, min(30, int(entries[0].get())))
                cols = max(2, min(40, int(entries[1].get())))
                max_mines = rows * cols - 1
                mines = max(1, min(max_mines, int(entries[2].get())))
            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректные числа.")
                return
            dialog.destroy()
            self.new_game("Своя игра", rows, cols, mines)

        tk.Button(dialog, text="Старт", command=start, bg=COLORS["accent"],
                  fg="#ffffff", relief="flat", font=("Segoe UI", 11, "bold"),
                  padx=10).grid(row=3, column=0, columnspan=2, pady=12)

    # --------------------------- Логика игры -----------------------------

    def new_game(self, difficulty_name, rows=None, cols=None, mines=None):
        if difficulty_name in DIFFICULTIES:
            cfg = DIFFICULTIES[difficulty_name]
            self.rows, self.cols, self.mines = cfg["rows"], cfg["cols"], cfg["mines"]
        else:
            self.rows, self.cols, self.mines = rows, cols, mines
        self.difficulty_name = difficulty_name

        # сброс состояния
        self.mine_positions = set()
        self.adjacent = {}
        self.revealed = set()
        self.flagged = set()
        self.first_click = True
        self.game_over = False
        self.timer_running = False
        self.seconds = 0
        self.timer_label.config(text="000")
        self.reset_button.config(text="🙂")
        self._update_mine_label()

        # перерисовка поля
        for widget in self.board_frame.winfo_children():
            widget.destroy()
        self.buttons = {}

        for r in range(self.rows):
            for c in range(self.cols):
                btn = tk.Label(
                    self.board_frame, width=2, height=1,
                    font=("Segoe UI", 13, "bold"),
                    bg=COLORS["cell_hidden"], fg=COLORS["text"],
                    relief="flat", bd=0,
                )
                btn.grid(row=r, column=c, padx=1, pady=1, ipadx=4, ipady=3)
                btn.bind("<Button-1>", lambda e, r=r, c=c: self.on_left_click(r, c))
                btn.bind("<Button-3>", lambda e, r=r, c=c: self.on_right_click(r, c))
                btn.bind("<Double-Button-1>", lambda e, r=r, c=c: self.on_chord(r, c))
                self.buttons[(r, c)] = btn

    def _place_mines(self, safe_r, safe_c):
        """Расставляем мины так, чтобы первый клик и его соседи были пусты."""
        forbidden = {
            (safe_r + dr, safe_c + dc)
            for dr in (-1, 0, 1) for dc in (-1, 0, 1)
        }
        all_cells = [
            (r, c) for r in range(self.rows) for c in range(self.cols)
            if (r, c) not in forbidden
        ]
        # если мин больше, чем доступных клеток — допускаем соседство
        if self.mines > len(all_cells):
            all_cells = [
                (r, c) for r in range(self.rows) for c in range(self.cols)
                if (r, c) != (safe_r, safe_c)
            ]
        self.mine_positions = set(random.sample(all_cells, self.mines))

        # подсчёт соседних мин
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in self.mine_positions:
                    continue
                count = sum(
                    1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                    if (r + dr, c + dc) in self.mine_positions
                )
                self.adjacent[(r, c)] = count

    def _neighbors(self, r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc

    # --------------------------- Обработчики -----------------------------

    def on_left_click(self, r, c):
        if self.game_over or (r, c) in self.flagged or (r, c) in self.revealed:
            return
        if self.first_click:
            self._place_mines(r, c)
            self.first_click = False
            self.timer_running = True
            self._tick()

        if (r, c) in self.mine_positions:
            self._lose()
            return

        self._reveal(r, c)
        self._check_win()

    def on_right_click(self, r, c):
        if self.game_over or (r, c) in self.revealed:
            return
        if (r, c) in self.flagged:
            self.flagged.discard((r, c))
            self._style_hidden(r, c)
        else:
            self.flagged.add((r, c))
            btn = self.buttons[(r, c)]
            btn.config(text="🚩", fg=COLORS["flag"], bg=COLORS["cell_hidden"])
        self._update_mine_label()

    def on_chord(self, r, c):
        """Двойной клик по открытой цифре: открыть соседей, если флажков достаточно."""
        if self.game_over or (r, c) not in self.revealed:
            return
        number = self.adjacent.get((r, c), 0)
        if number == 0:
            return
        flags_around = sum(1 for n in self._neighbors(r, c) if n in self.flagged)
        if flags_around != number:
            return
        for nr, nc in self._neighbors(r, c):
            if (nr, nc) in self.flagged or (nr, nc) in self.revealed:
                continue
            if (nr, nc) in self.mine_positions:
                self._lose()
                return
            self._reveal(nr, nc)
        self._check_win()

    # --------------------------- Раскрытие -------------------------------

    def _reveal(self, r, c):
        """Раскрытие клетки с автозаливкой пустых областей (итеративно)."""
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            if (cr, cc) in self.revealed or (cr, cc) in self.flagged:
                continue
            self.revealed.add((cr, cc))
            number = self.adjacent.get((cr, cc), 0)
            self._style_open(cr, cc, number)
            if number == 0:
                for nr, nc in self._neighbors(cr, cc):
                    if (nr, nc) not in self.revealed:
                        stack.append((nr, nc))

    # --------------------------- Стилизация ------------------------------

    def _style_hidden(self, r, c):
        self.buttons[(r, c)].config(
            text="", bg=COLORS["cell_hidden"], fg=COLORS["text"]
        )

    def _style_open(self, r, c, number):
        btn = self.buttons[(r, c)]
        if number == 0:
            btn.config(text="", bg=COLORS["cell_open"])
        else:
            btn.config(
                text=str(number), bg=COLORS["cell_open"],
                fg=NUMBER_COLORS.get(number, COLORS["text"]),
            )

    # --------------------------- Конец игры ------------------------------

    def _lose(self):
        self.game_over = True
        self.timer_running = False
        self.reset_button.config(text="😵")
        for (mr, mc) in self.mine_positions:
            btn = self.buttons[(mr, mc)]
            if (mr, mc) in self.flagged:
                btn.config(text="🚩", bg=COLORS["cell_open"])
            else:
                btn.config(text="💣", bg=COLORS["mine_bg"], fg=COLORS["text"])
        # неверно поставленные флажки
        for (fr, fc) in self.flagged:
            if (fr, fc) not in self.mine_positions:
                self.buttons[(fr, fc)].config(text="❌", bg=COLORS["cell_open"],
                                              fg=COLORS["mine"])
        messagebox.showinfo("Сапёр", "💥 Бум! Вы подорвались. Попробуйте ещё раз!")

    def _check_win(self):
        total = self.rows * self.cols
        if len(self.revealed) == total - self.mines:
            self.game_over = True
            self.timer_running = False
            self.reset_button.config(text="😎")
            for (mr, mc) in self.mine_positions:
                if (mr, mc) not in self.flagged:
                    self.buttons[(mr, mc)].config(text="🚩", fg=COLORS["flag"])
            self.flagged = set(self.mine_positions)
            self._update_mine_label()
            messagebox.showinfo(
                "Сапёр", f"🎉 Победа! Ваше время: {self.seconds} сек."
            )

    # --------------------------- Индикаторы ------------------------------

    def _update_mine_label(self):
        remaining = self.mines - len(self.flagged)
        self.mine_label.config(text=f"{remaining:03d}")

    def _tick(self):
        if self.timer_running and not self.game_over:
            self.seconds += 1
            self.timer_label.config(text=f"{min(self.seconds, 999):03d}")
            self.root.after(1000, self._tick)


def main():
    root = tk.Tk()
    Minesweeper(root)
    root.mainloop()


if __name__ == "__main__":
    main()
