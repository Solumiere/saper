/*
 * Сапёр — веб-версия (ванильный JS).
 * Выбор сложности, таймер, счётчик мин, настраиваемый размер поля.
 */

(function () {
  "use strict";

  // -------- Уровни сложности --------
  const LEVELS = {
    beginner:     { rows: 9,  cols: 9,  mines: 10 },
    intermediate: { rows: 16, cols: 16, mines: 40 },
    expert:       { rows: 16, cols: 30, mines: 99 },
  };

  // -------- DOM --------
  const boardEl     = document.getElementById("board");
  const mineCounter = document.getElementById("mine-counter");
  const timerEl     = document.getElementById("timer");
  const faceBtn     = document.getElementById("face");
  const diffWrap    = document.getElementById("difficulty");
  const customForm  = document.getElementById("custom-form");
  const inpCols     = document.getElementById("custom-cols");
  const inpRows     = document.getElementById("custom-rows");
  const inpMines    = document.getElementById("custom-mines");
  const overlay     = document.getElementById("overlay");
  const overlayEmoji= document.getElementById("overlay-emoji");
  const overlayTitle= document.getElementById("overlay-title");
  const overlayText = document.getElementById("overlay-text");
  const overlayBtn  = document.getElementById("overlay-restart");

  // -------- Состояние --------
  let rows, cols, mines;
  let grid = [];            // массив объектов клеток
  let started = false;      // расставлены ли мины
  let finished = false;
  let revealedCount = 0;
  let flagsCount = 0;
  let seconds = 0;
  let timerId = null;

  // -------- Инициализация --------
  function startGame(level) {
    let cfg;
    if (level === "custom") {
      cfg = readCustom();
    } else {
      cfg = LEVELS[level] || LEVELS.beginner;
    }
    rows = cfg.rows;
    cols = cfg.cols;
    mines = cfg.mines;
    resetState();
    buildBoard();
    updateMineCounter();
  }

  function readCustom() {
    let c = clamp(parseInt(inpCols.value, 10) || 12, 5, 40);
    let r = clamp(parseInt(inpRows.value, 10) || 12, 5, 30);
    const maxMines = r * c - 9 > 1 ? r * c - 9 : r * c - 1;
    let m = clamp(parseInt(inpMines.value, 10) || 24, 1, maxMines);
    inpCols.value = c;
    inpRows.value = r;
    inpMines.value = m;
    return { rows: r, cols: c, mines: m };
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function resetState() {
    grid = [];
    started = false;
    finished = false;
    revealedCount = 0;
    flagsCount = 0;
    seconds = 0;
    stopTimer();
    timerEl.textContent = "000";
    faceBtn.textContent = "\uD83D\uDE42"; // 🙂
    overlay.hidden = true;
  }

  // -------- Построение поля --------
  function buildBoard() {
    boardEl.innerHTML = "";
    boardEl.style.gridTemplateColumns = `repeat(${cols}, var(--cell-size))`;

    // адаптивный размер клеток под ширину
    const maxBoardWidth = Math.min(window.innerWidth - 60, 720);
    const size = clamp(Math.floor((maxBoardWidth - (cols + 1) * 4) / cols), 18, 38);
    boardEl.style.setProperty("--cell-size", size + "px");

    for (let r = 0; r < rows; r++) {
      const rowArr = [];
      for (let c = 0; c < cols; c++) {
        const cell = {
          r, c,
          mine: false,
          adjacent: 0,
          open: false,
          flag: false,
          el: document.createElement("button"),
        };
        cell.el.className = "cell";
        cell.el.type = "button";
        cell.el.addEventListener("click", () => onLeftClick(cell));
        cell.el.addEventListener("contextmenu", (e) => { e.preventDefault(); onRightClick(cell); });
        cell.el.addEventListener("dblclick", () => onChord(cell));
        attachLongPress(cell);
        boardEl.appendChild(cell.el);
        rowArr.push(cell);
      }
      grid.push(rowArr);
    }
  }

  // Долгое нажатие на телефоне = флажок
  function attachLongPress(cell) {
    let timer = null;
    cell.el.addEventListener("touchstart", () => {
      timer = setTimeout(() => { onRightClick(cell); timer = null; }, 420);
    }, { passive: true });
    const cancel = () => { if (timer) { clearTimeout(timer); timer = null; } };
    cell.el.addEventListener("touchend", cancel);
    cell.el.addEventListener("touchmove", cancel);
  }

  // -------- Расстановка мин (первый клик безопасен) --------
  function placeMines(safeR, safeC) {
    const forbidden = new Set();
    for (let dr = -1; dr <= 1; dr++) {
      for (let dc = -1; dc <= 1; dc++) {
        forbidden.add((safeR + dr) + "," + (safeC + dc));
      }
    }
    const candidates = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (!forbidden.has(r + "," + c)) candidates.push([r, c]);
      }
    }
    // если мин больше доступных клеток — разрешаем соседство (кроме самой клетки)
    let pool = candidates;
    if (mines > candidates.length) {
      pool = [];
      for (let r = 0; r < rows; r++)
        for (let c = 0; c < cols; c++)
          if (!(r === safeR && c === safeC)) pool.push([r, c]);
    }
    // перемешивание Фишера–Йетса
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    for (let i = 0; i < mines; i++) {
      const [r, c] = pool[i];
      grid[r][c].mine = true;
    }
    // подсчёт соседей
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (grid[r][c].mine) continue;
        grid[r][c].adjacent = neighbors(r, c).filter((n) => n.mine).length;
      }
    }
  }

  function neighbors(r, c) {
    const res = [];
    for (let dr = -1; dr <= 1; dr++) {
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        const nr = r + dr, nc = c + dc;
        if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) res.push(grid[nr][nc]);
      }
    }
    return res;
  }

  // -------- Обработчики --------
  function onLeftClick(cell) {
    if (finished || cell.open || cell.flag) return;
    if (!started) {
      placeMines(cell.r, cell.c);
      started = true;
      startTimer();
    }
    if (cell.mine) {
      cell.el.classList.add("is-exploded");
      cell.el.textContent = "\uD83D\uDCA5"; // 💥
      lose();
      return;
    }
    reveal(cell);
    checkWin();
  }

  function onRightClick(cell) {
    if (finished || cell.open) return;
    cell.flag = !cell.flag;
    if (cell.flag) {
      cell.el.classList.add("is-flag");
      cell.el.textContent = "\uD83D\uDEA9"; // 🚩
      flagsCount++;
    } else {
      cell.el.classList.remove("is-flag");
      cell.el.textContent = "";
      flagsCount--;
    }
    updateMineCounter();
  }

  function onChord(cell) {
    if (finished || !cell.open || cell.adjacent === 0) return;
    const around = neighbors(cell.r, cell.c);
    const flags = around.filter((n) => n.flag).length;
    if (flags !== cell.adjacent) return;
    for (const n of around) {
      if (!n.open && !n.flag) {
        if (n.mine) {
          n.el.classList.add("is-exploded");
          n.el.textContent = "\uD83D\uDCA5";
          lose();
          return;
        }
        reveal(n);
      }
    }
    checkWin();
  }

  // -------- Раскрытие (flood fill) --------
  function reveal(start) {
    const stack = [start];
    while (stack.length) {
      const cell = stack.pop();
      if (cell.open || cell.flag) continue;
      cell.open = true;
      revealedCount++;
      cell.el.classList.add("is-open");
      if (cell.adjacent > 0) {
        cell.el.textContent = String(cell.adjacent);
        cell.el.classList.add("n" + cell.adjacent);
      } else {
        cell.el.textContent = "";
        for (const n of neighbors(cell.r, cell.c)) {
          if (!n.open && !n.flag) stack.push(n);
        }
      }
    }
  }

  // -------- Завершение --------
  function lose() {
    finished = true;
    stopTimer();
    faceBtn.textContent = "\uD83D\uDE35"; // 😵
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cell = grid[r][c];
        if (cell.mine && !cell.flag && !cell.el.classList.contains("is-exploded")) {
          cell.el.classList.add("is-mine");
          cell.el.textContent = "\uD83D\uDCA3"; // 💣
        } else if (!cell.mine && cell.flag) {
          cell.el.classList.add("is-wrong");
          cell.el.textContent = "\u274C"; // ❌
        }
      }
    }
    showOverlay("\uD83D\uDCA5", "Бум!", "Вы подорвались на мине. Попробуйте ещё раз!");
  }

  function checkWin() {
    if (revealedCount === rows * cols - mines) {
      finished = true;
      stopTimer();
      faceBtn.textContent = "\uD83D\uDE0E"; // 😎
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const cell = grid[r][c];
          if (cell.mine && !cell.flag) {
            cell.flag = true;
            cell.el.classList.add("is-flag");
            cell.el.textContent = "\uD83D\uDEA9";
          }
        }
      }
      flagsCount = mines;
      updateMineCounter();
      showOverlay("\uD83C\uDF89", "Победа!", "Отличная работа! Время: " + seconds + " сек.");
    }
  }

  function showOverlay(emoji, title, text) {
    overlayEmoji.textContent = emoji;
    overlayTitle.textContent = title;
    overlayText.textContent = text;
    overlay.hidden = false;
  }

  // -------- Индикаторы --------
  function updateMineCounter() {
    const remaining = mines - flagsCount;
    mineCounter.textContent = pad(remaining);
  }

  function pad(n) {
    const neg = n < 0;
    const s = String(Math.abs(n)).padStart(3, "0");
    return neg ? "-" + s.slice(1) : s;
  }

  function startTimer() {
    stopTimer();
    timerId = setInterval(() => {
      seconds = Math.min(seconds + 1, 999);
      timerEl.textContent = pad(seconds);
    }, 1000);
  }

  function stopTimer() {
    if (timerId) { clearInterval(timerId); timerId = null; }
  }

  // -------- События интерфейса --------
  let currentLevel = "beginner";

  diffWrap.addEventListener("click", (e) => {
    const btn = e.target.closest(".difficulty__btn");
    if (!btn) return;
    diffWrap.querySelectorAll(".difficulty__btn").forEach((b) => b.classList.remove("is-active"));
    btn.classList.add("is-active");
    currentLevel = btn.dataset.level;
    if (currentLevel === "custom") {
      customForm.hidden = false;
      startGame("custom");
    } else {
      customForm.hidden = true;
      startGame(currentLevel);
    }
  });

  customForm.addEventListener("submit", (e) => {
    e.preventDefault();
    currentLevel = "custom";
    startGame("custom");
  });

  faceBtn.addEventListener("click", () => startGame(currentLevel));
  overlayBtn.addEventListener("click", () => startGame(currentLevel));
  window.addEventListener("resize", () => {
    // пересчёт размера клеток без сброса игры
    if (!cols) return;
    const maxBoardWidth = Math.min(window.innerWidth - 60, 720);
    const size = clamp(Math.floor((maxBoardWidth - (cols + 1) * 4) / cols), 18, 38);
    boardEl.style.setProperty("--cell-size", size + "px");
  });

  // -------- Старт --------
  startGame("beginner");
})();
