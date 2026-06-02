#!/usr/bin/env python3
import curses
import random
import time
import os
import copy

BEST_FILE = os.path.join(os.path.dirname(__file__), "best.txt")

TILE_COLORS = {
    0:    (curses.COLOR_BLACK,   curses.COLOR_BLACK),
    2:    (curses.COLOR_BLACK,   232),
    4:    (curses.COLOR_BLACK,   229),
    8:    (curses.COLOR_WHITE,   208),
    16:   (curses.COLOR_WHITE,   202),
    32:   (curses.COLOR_WHITE,   196),
    64:   (curses.COLOR_WHITE,   160),
    128:  (curses.COLOR_BLACK,   226),
    256:  (curses.COLOR_BLACK,   220),
    512:  (curses.COLOR_BLACK,   214),
    1024: (curses.COLOR_WHITE,   94),
    2048: (curses.COLOR_BLACK,   220),
}

CELL_W = 7
CELL_H = 3
COLS = 4
ROWS = 4


def load_best():
    try:
        with open(BEST_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_best(score):
    with open(BEST_FILE, "w") as f:
        f.write(str(score))


def empty_board():
    return [[0] * COLS for _ in range(ROWS)]


def add_tile(board):
    empties = [(r, c) for r in range(ROWS) for c in range(COLS) if board[r][c] == 0]
    if empties:
        r, c = random.choice(empties)
        board[r][c] = 4 if random.random() < 0.1 else 2


def slide_row(row):
    nums = [x for x in row if x != 0]
    merged = []
    score = 0
    skip = False
    for i in range(len(nums)):
        if skip:
            skip = False
            continue
        if i + 1 < len(nums) and nums[i] == nums[i + 1]:
            merged.append(nums[i] * 2)
            score += nums[i] * 2
            skip = True
        else:
            merged.append(nums[i])
    merged += [0] * (COLS - len(merged))
    return merged, score


def move(board, direction):
    score = 0
    new_board = empty_board()
    if direction == "left":
        for r in range(ROWS):
            new_board[r], s = slide_row(board[r])
            score += s
    elif direction == "right":
        for r in range(ROWS):
            rev, s = slide_row(board[r][::-1])
            new_board[r] = rev[::-1]
            score += s
    elif direction == "up":
        for c in range(COLS):
            col = [board[r][c] for r in range(ROWS)]
            slid, s = slide_row(col)
            for r in range(ROWS):
                new_board[r][c] = slid[r]
            score += s
    elif direction == "down":
        for c in range(COLS):
            col = [board[r][c] for r in range(ROWS)][::-1]
            slid, s = slide_row(col)
            slid = slid[::-1]
            for r in range(ROWS):
                new_board[r][c] = slid[r]
            score += s
    changed = new_board != board
    return new_board, score, changed


def has_moves(board):
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] == 0:
                return True
            if c + 1 < COLS and board[r][c] == board[r][c + 1]:
                return True
            if r + 1 < ROWS and board[r][c] == board[r + 1][c]:
                return True
    return False


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    pair = 1
    color_map = {}
    seen = {}
    for val, (fg, bg) in TILE_COLORS.items():
        key = (fg, bg)
        if key not in seen:
            curses.init_pair(pair, fg, bg)
            seen[key] = pair
            pair += 1
        color_map[val] = seen[key]
    # default pair for unknown values
    curses.init_pair(pair, curses.COLOR_WHITE, 241)
    color_map["default"] = pair
    return color_map


def get_pair(color_map, val):
    return color_map.get(val, color_map["default"])


def draw_board(win, board, display_board, score, best, color_map, game_over=False):
    win.erase()
    h, w = win.getmaxyx()

    board_px_w = COLS * CELL_W + COLS + 1
    board_px_h = ROWS * CELL_H + ROWS + 1
    start_x = max(0, (w - board_px_w) // 2)
    start_y = 3

    # Header
    title = "2048"
    win.attron(curses.A_BOLD)
    try:
        win.addstr(1, start_x, title)
    except curses.error:
        pass
    win.attroff(curses.A_BOLD)
    score_str = f"SCORE: {score}   BEST: {best}"
    try:
        win.addstr(1, start_x + board_px_w - len(score_str), score_str)
    except curses.error:
        pass

    # Grid
    for r in range(ROWS):
        for c in range(COLS):
            val = display_board[r][c]
            px = start_x + c * (CELL_W + 1)
            py = start_y + r * (CELL_H + 1)
            pair = get_pair(color_map, val)
            attr = curses.color_pair(pair) | curses.A_BOLD

            # Draw cell background
            for dy in range(CELL_H):
                try:
                    win.addstr(py + dy, px, " " * CELL_W, attr)
                except curses.error:
                    pass

            # Draw number centered
            text = str(val) if val != 0 else ""
            tx = px + (CELL_W - len(text)) // 2
            ty = py + CELL_H // 2
            try:
                win.addstr(ty, tx, text, attr)
            except curses.error:
                pass

            # Draw separators
            for dy in range(CELL_H):
                try:
                    win.addstr(py + dy, px + CELL_W, "│", curses.A_DIM)
                except curses.error:
                    pass
            try:
                win.addstr(py + CELL_H, px, "─" * CELL_W, curses.A_DIM)
                win.addstr(py + CELL_H, px + CELL_W, "┼", curses.A_DIM)
            except curses.error:
                pass

    # Controls hint
    hint = "← → ↑ ↓ Move  U Undo  Q Quit"
    try:
        win.addstr(start_y + board_px_h + 1, start_x, hint, curses.A_DIM)
    except curses.error:
        pass

    if game_over:
        msg = "  GAME OVER! Press R to restart  "
        try:
            win.addstr(start_y + board_px_h // 2 + 1, start_x + (board_px_w - len(msg)) // 2,
                       msg, curses.A_BOLD | curses.color_pair(get_pair(color_map, 32)))
        except curses.error:
            pass

    win.refresh()


def animate_slide(win, from_board, to_board, score, best, color_map, steps=4):
    """Interpolate between from_board and to_board over `steps` frames."""
    for step in range(1, steps + 1):
        interp = copy.deepcopy(from_board)
        # Simple interpolation: at each step show more of the destination
        frac = step / steps
        if frac >= 1.0:
            interp = to_board
        else:
            for r in range(ROWS):
                for c in range(COLS):
                    if to_board[r][c] != from_board[r][c]:
                        if frac >= 0.5:
                            interp[r][c] = to_board[r][c]
        draw_board(win, to_board, interp, score, best, color_map)
        time.sleep(0.04)


def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.timeout(100)

    color_map = init_colors()

    board = empty_board()
    add_tile(board)
    add_tile(board)
    score = 0
    best = load_best()
    prev_board = None
    prev_score = 0
    game_over = False

    KEY_MAP = {
        curses.KEY_LEFT:  "left",
        curses.KEY_RIGHT: "right",
        curses.KEY_UP:    "up",
        curses.KEY_DOWN:  "down",
    }

    draw_board(stdscr, board, board, score, best, color_map)

    while True:
        key = stdscr.getch()

        if key in (ord("q"), ord("Q")):
            break

        if key in (ord("r"), ord("R")):
            board = empty_board()
            add_tile(board)
            add_tile(board)
            score = 0
            prev_board = None
            prev_score = 0
            game_over = False
            draw_board(stdscr, board, board, score, best, color_map)
            continue

        if key in (ord("u"), ord("U")) and prev_board is not None:
            board = copy.deepcopy(prev_board)
            score = prev_score
            prev_board = None
            draw_board(stdscr, board, board, score, best, color_map)
            continue

        if game_over:
            draw_board(stdscr, board, board, score, best, color_map, game_over=True)
            continue

        direction = KEY_MAP.get(key)
        if direction is None:
            continue

        new_board, gained, changed = move(board, direction)
        if not changed:
            continue

        prev_board = copy.deepcopy(board)
        prev_score = score
        score += gained
        if score > best:
            best = score
            save_best(best)

        animate_slide(stdscr, board, new_board, score, best, color_map)
        board = new_board
        add_tile(board)

        if not has_moves(board):
            game_over = True

        draw_board(stdscr, board, board, score, best, color_map, game_over=game_over)


if __name__ == "__main__":
    curses.wrapper(main)
