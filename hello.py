import shutil
import sys
import time


def enable_ansi():
    """Enable ANSI escape sequences on Windows."""
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        mode.value |= 0x0004
        kernel32.SetConsoleMode(handle, mode)


# --- Color codes ---
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"


RAINBOW = [C.RED, C.YELLOW, C.GREEN, C.CYAN, C.BLUE, C.MAGENTA]


def colorize(text, color):
    return f"{color}{text}{C.RESET}"


def rainbow_text(text):
    result = ""
    for i, ch in enumerate(text):
        if ch != " ":
            result += RAINBOW[i % len(RAINBOW)] + ch
        else:
            result += ch
    return result + C.RESET


def get_terminal_width():
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def center(text):
    # Strip ANSI codes for width calculation
    import re

    clean = re.sub(r"\033\[[0-9;]*m", "", text)
    width = get_terminal_width()
    return text.center(width)


def slow_print(text, delay=0.03):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def separator(char="=", length=50, color=C.DIM):
    print(colorize(center(char * length), color))


def banner():
    art = [
        "  _   _      _ _         __        __",
        " | | | | ___| | | ___    \\ \\      / /",
        " | |_| |/ _ \\ | |/ _ \\    \\ \\ /\\ / /",
        " |  _  |  __/ | | (_) |    \\ V  V /",
        " |_| |_|\\___|_|_|\\___/      \\_/\\_/",
        "",
        "       [ Welcome to the Show! ]",
    ]
    box_width = max(len(line) for line in art) + 4

    # Top border in cyan
    print(colorize(center("+" + "-" * box_width + "+"), C.CYAN))

    # Each line of the banner in a different rainbow color
    for i, line in enumerate(art):
        colored_line = colorize(line, RAINBOW[i % len(RAINBOW)])
        # We need to center manually since ANSI codes affect padding
        padding = (get_terminal_width() - box_width) // 2
        left = colorize("|", C.CYAN) + "  "
        right = "  " + colorize("|", C.CYAN)
        print(" " * max(padding, 0) + left + colored_line.ljust(box_width - 2) + right)

    # Bottom border in cyan
    print(colorize(center("+" + "-" * box_width + "+"), C.CYAN))


def main():
    enable_ansi()

    print()
    banner()
    print()
    separator("~", 50, C.BLUE)
    print()

    slow_print(
        center(colorize(">>> Hello, World! <<<", C.BOLD + C.YELLOW)), delay=0.04
    )
    print()
    time.sleep(0.2)

    slow_print(
        center(colorize("Your fancy Python script", C.GREEN))
        + center(colorize("is running perfectly!", C.CYAN)),
        delay=0.02,
    )
    print()
    time.sleep(0.2)

    slow_print(
        center(colorize("Have an awesome day!", C.BOLD + C.MAGENTA)), delay=0.04
    )
    print()

    separator("~", 50, C.BLUE)
    print()

    print(center(colorize("Made with <3 and Python", C.RED)))
    separator("=", 50, C.DIM)
    print()


if __name__ == "__main__":
    main()
