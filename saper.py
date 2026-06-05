"""
Сапёр (Minesweeper) на Python + tkinter.

Возможности:
  * Экранный выбор сложности кнопками: Новичок / Любитель / Эксперт / Свой
  * Настройка размера поля и числа мин прямо в окне
  * Красивый тёмный визуал с цветными цифрами
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
    "Эксперт":  {"rows": 16, "cols": 30, "mines": 99},
}

# Ограничения для режима "Свой"
MIN_SIZE = 5
MAX_ROWS = 30
MAX_COLS = 40

# --------------------------- Палитра / стиль -----------------------------

COLORS = {
    "bg":            "#0f1320",   # общий фон окна
    "panel":         "#1e2438",   # фон панелей
    "panel_2":       "#262d45",   # фон кнопок
    "cell_hidden":   "#38405c",   # закрытая клетка
    "cell_open":     "#1a1f30",   # открытая клетка
    "accent":        "#5da9e9",
    "accent_2":      "#7c5cff",
    "text":          "#e8edf6",
    "text_dim":      "#9aa6c2",
    "mine":          "#ff5d6c",
    "mine_bg":       "#7a2331",
    "explode_bg":    "#c62f3d",
    "flag":          "#ffce4d",
    "display_bg":    "#0b0e18",
    "display_fg":    "#ff5d6c",
}

# Классические цвета цифр сапёра
NUMBER_COLORS = {
    1: "#4fa3ff",
    2: "#42c97a",
    3: "#ff6b6b",
    4: "#a779ff",
    5: "#ffae42",
    6: "#39d0d8",
    7: "#e8edf6",
    8: "#9aa6c2",
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

        self.diff_buttons = {}

        self._build_difficulty_bar()
        self._build_custom_panel()
        self._build_top_panel()
        self.board_frame = tk.Frame(self.root, bg=COLORS["bg"], padx=12, pady=12)
        self.board_frame.pack()

        self.new_game(self.difficulty_name)

    # ----------------------------- UI -----------------------------------

    def _build_difficulty_bar(self):
        self.diff_bar = tk.Frame(self.root, bg=COLORS["panel"], padx=10, pady=10)
        self.diff_bar.pack(fill="x", padx=12, pady=(12, 0))

        title = tk.Label(
            self.diff_bar, text="💣 Сапёр", bg=COLORS["panel"], fg=COLORS["text"],
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(pady=(0, 8))

        btn_row = tk.Frame(self.diff_bar, bg=COLORS["panel"])
        btn_row.pack()

        for name in DIFFICULTIES:
            b = tk.Button(
                btn_row, text=name, font=("Segoe UI", 11, "bold"),
                bg=COLORS["panel_2"], fg=COLORS["text"],
                activebackground=COLORS["accent"], activeforeground="#ffffff",
                relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
                command=lambda n=name: self.select_difficulty(n),
            )
            b.pack(side="left", padx=4)
            self.diff_buttons[name] = b

        custom_btn = tk.Button(
            btn_row, text="⚙ Свой", font=("Segoe UI", 11, "bold"),
            bg=COLORS["panel_2"], fg=COLORS["text"],
            activebackground=COLORS["accent"], activeforeground="#ffffff",
            relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
            command=self.select_custom,
        )
        custom_btn.pack(side="left", padx=4)
        self.diff_buttons["Свой"] = custom_btn

    def _build_custom_panel(self):
        self.custom_frame = tk.Frame(self.root, bg=COLORS["panel"], padx=10, pady=10)
        # показываем только при выборе "Свой" (pack в select_custom)

        self.var_cols = tk.IntVar(value=12)
        self.var_rows = tk.IntVar(value=12)
        self.var_mines = tk.IntVar(value=24)

        specs = [
            ("Ширина", self.var_cols, MIN_SIZE, MAX_COLS),
            ("Высота", self.var_rows, MIN_SIZE, MAX_ROWS),
            ("Мины", self.var_mines, 1, MAX_ROWS * MAX_COLS),
        ]
        for label, var, lo, hi in specs:
            wrap = tk.Frame(self.custom_frame, bg=COLORS["panel"])
            wrap.pack(side="left", padx=8)
            tk.Label(
                wrap, text=label, bg=COLORS["panel"], fg=COLORS["text_dim"],
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w")
            tk.Spinbox(
                wrap, from_=lo, to=hi, textvariable=var, width=6,
                font=("Segoe UI", 11), justify="center",
                bg=COLORS["display_bg"], fg=COLORS["text"],
                buttonbackground=COLORS["panel_2"], relief="flat",
                insertbackground=COLORS["text"],
            ).pack()

        apply_btn = tk.Button(
            self.custom_frame, text="Применить", font=("Segoe UI", 11, "bold"),
            bg=COLORS["accent_2"], fg="#ffffff", activebackground=COLORS["accent"],
            relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
            command=self.apply_custom,
        )
        apply_btn.pack(side="left", padx=(12, 4), anchor="s", pady=(0, 1))

    def _build_top_panel(self):
        self.panel = tk.Frame(self.root, bg=COLORS["panel"], padx=12, pady=10)
        self.panel.pack(fill="x", padx=12, pady=(10, 0))

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
            relief="flat", width=3, cursor="hand2",
            command=lambda: self.new_game(self.difficulty_name),
        )
        self.reset_button.pack(side="left", expand=True)

        # таймер
        self.timer_label = tk.Label(
            self.panel, text="000", font=("Consolas", 22, "bold"),
            bg=COLORS["display_bg"], fg=COLORS["display_fg"], width=4, padx=6,
        )
        self.timer_label.pack(side="right")

    # --------------------------- Выбор сложности ----------------------

    def _highlight_difficulty(self, active_name):
        for name, btn in self.diff_buttons.items():
            if name == active_name:
                btn.config(bg=COLORS["accent"], fg="#ffffff")
            else:
                btn.config(bg=COLORS["panel_2"], fg=COLORS["text"])

    def select_difficulty(self, name):
        self.custom_frame.pack_forget()
        self._highlight_difficulty(name)
        self.new_game(name)

    def select_custom(self):
        self._highlight_difficulty("Свой")
        # показываем панель настроек сразу под панелью сложности
        self.custom_frame.pack(fill="x", padx=12, pady=(10, 0), after=self.diff_bar)
        self.apply_custom()

    def apply_custom(self):
        try:
            cols = self._clamp(int(self.var_cols.get()), MIN_SIZE, MAX_COLS)
            rows = self._clamp(int(self.var_rows.get()), MIN_SIZE, MAX_ROWS)
            max_mines = rows * cols - 1
            mines = self._clamp(int(self.var_mines.get()), 1, max_mines)
        except (ValueError, tk.TclError):
            messagebox.showerror("Ошибка", "Введите корректные числа.")
            return
        self.var_cols.set(cols)
        self.var_rows.set(rows)
        self.var_mines.set(mines)
        self.new_game("Свой", rows, cols, mines)

    @staticmethod
    def _clamp(value, lo, hi):
        return max(lo, min(hi, value))

    # --------------------------- Логика игры -----------------------------

    def new_game(self, difficulty_name, rows=None, cols=None, mines=None):
        if difficulty_name in DIFFICULTIES:
            cfg = DIFFICULTIES[difficulty_name]
            self.rows, self.cols, self.mines = cfg["rows"], cfg["cols"], cfg["mines"]
        else:
            self.rows, self.cols, self.mines = rows, cols, mines
        self.difficulty_name = difficulty_name
        if difficulty_name in self.diff_buttons:
            self._highlight_difficulty(difficulty_name)

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

        # размер клеток подстраивается под ширину поля
        cell_font_size = 13 if self.cols <= 20 else 10
        cell_w = 2 if self.cols <= 20 else 1

        for r in range(self.rows):
            for c in range(self.cols):
                btn = tk.Label(
                    self.board_frame, width=cell_w, height=1,
                    font=("Segoe UI", cell_font_size, "bold"),
                    bg=COLORS["cell_hidden"], fg=COLORS["text"],
                    relief="flat", bd=0,
                )
                btn.grid(row=r, column=c, padx=1, pady=1, ipadx=3, ipady=2)
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
            self._lose((r, c))
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
                self._lose((nr, nc))
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

    def _lose(self, exploded=None):
        self.game_over = True
        self.timer_running = False
        self.reset_button.config(text="😵")
        for (mr, mc) in self.mine_positions:
            btn = self.buttons[(mr, mc)]
            if (mr, mc) == exploded:
                btn.config(text="💥", bg=COLORS["explode_bg"], fg="#ffffff")
            elif (mr, mc) in self.flagged:
                btn.config(text="🚩", bg=COLORS["cell_open"])
            else:
                btn.config(text="💣", bg=COLORS["mine_bg"], fg="#ffffff")
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
