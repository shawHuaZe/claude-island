"""
Windows terminal activation helper.
Finds and activates the Claude Code terminal window on Windows 11.
"""
import sys
import os

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    # Windows API constants
    SW_RESTORE = 9
    SW_SHOW = 5
    GWL_STYLE = -16
    GWL_EXSTYLE = -20
    WS_VISIBLE = 0x10000000
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000

    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int)
    )
    GetWindowText = user32.GetWindowTextW
    GetWindowTextLength = user32.GetWindowTextLengthW
    IsWindowVisible = user32.IsWindowVisible
    GetWindowLong = user32.GetWindowLongW
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    SetForegroundWindow = user32.SetForegroundWindow
    ShowWindow = user32.ShowWindow
    AttachThreadInput = user32.AttachThreadInput
    GetCurrentThreadId = user32.GetCurrentThreadId
    BringWindowToTop = user32.BringWindowToTop


def get_window_title(hwnd):
    """Get window title by HWND"""
    length = GetWindowTextLength(hwnd)
    if length == 0:
        return ""
    buff = ctypes.create_unicode_buffer(length + 1)
    GetWindowText(hwnd, buff, length + 1)
    return buff.value


def is_main_window(hwnd):
    """Check if window is a main application window"""
    if not IsWindowVisible(hwnd):
        return False

    style = GetWindowLong(hwnd, GWL_STYLE)
    ex_style = GetWindowLong(hwnd, GWL_EXSTYLE)

    # Must have WS_VISIBLE
    if not (style & WS_VISIBLE):
        return False

    # Skip tool windows
    if ex_style & WS_EX_TOOLWINDOW:
        # But include app windows (terminal windows)
        if not (ex_style & WS_EX_APPWINDOW):
            return False

    title = get_window_title(hwnd)
    return len(title) > 0


def get_terminal_windows():
    """Get all terminal/command prompt windows"""
    windows = []

    def callback(hwnd, _):
        if is_main_window(hwnd):
            title = get_window_title(hwnd)
            # Filter for terminal windows
            lower_title = title.lower()
            if any(term in lower_title for term in [
                'powershell', 'cmd', 'terminal', 'windows terminal',
                'claude', 'command prompt', 'pws'
            ]):
                pid = ctypes.c_ulong()
                GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                windows.append({
                    'hwnd': hwnd,
                    'title': title,
                    'pid': pid.value
                })
        return True

    EnumWindows(EnumWindowsProc(callback), 0)
    return windows


def activate_terminal():
    """
    Find and activate the most likely Claude Code terminal window.
    Priority: PowerShell with Claude > Windows Terminal > Other terminals
    """
    if sys.platform != "win32":
        return False, "Not on Windows"

    try:
        windows = get_terminal_windows()

        if not windows:
            return False, "No terminal windows found"

        # Score windows by likelihood of being Claude Code
        scored = []
        for win in windows:
            title = win['title'].lower()
            score = 0

            # Higher score for Claude-related titles
            if 'claude' in title:
                score += 100
            if 'powershell' in title and 'claude' in title:
                score += 150
            if ' Claude Code' in title or title.endswith('claude'):
                score += 200

            # Medium score for PowerShell/Windows Terminal
            if 'powershell' in title:
                score += 30
            if 'windows terminal' in title:
                score += 20

            # Prefer windows with longer titles (more specific)
            score += len(win['title']) // 10

            scored.append((score, win))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return False, "No suitable terminal found"

        # Activate the highest scoring window
        best = scored[0][1]
        hwnd = best['hwnd']

        # Restore if minimized
        ShowWindow(hwnd, SW_RESTORE)

        # Bring to foreground
        # First, attach to input thread to steal focus properly
        try:
            foreground_hwnd = user32.GetForegroundWindow()
            foreground_pid = ctypes.c_ulong()
            GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(foreground_pid))

            current_thread = GetCurrentThreadId()
            target_thread = ctypes.c_ulong()
            GetWindowThreadProcessId(hwnd, ctypes.byref(target_thread))

            if foreground_pid.value != target_thread.value:
                AttachThreadInput(target_thread.value, current_thread, True)

            SetForegroundWindow(hwnd)
            BringWindowToTop(hwnd)
            ShowWindow(hwnd, SW_SHOW)

            if foreground_pid.value != target_thread.value:
                AttachThreadInput(target_thread.value, current_thread, False)
        except:
            # Fallback: just set foreground
            SetForegroundWindow(hwnd)
            BringWindowToTop(hwnd)

        return True, f"Activated: {best['title']}"

    except Exception as e:
        return False, str(e)


def get_claude_sessions_from_terminals():
    """
    Try to find Claude Code sessions by examining window titles
    and process names.
    """
    if sys.platform != "win32":
        return []

    sessions = []
    try:
        windows = get_terminal_windows()
        for win in windows:
            title = win['title']
            if 'claude' in title.lower():
                sessions.append({
                    'title': title,
                    'pid': win['pid'],
                    'hwnd': win['hwnd']
                })
    except:
        pass

    return sessions


if __name__ == "__main__":
    # Test
    if sys.platform == "win32":
        success, msg = activate_terminal()
        print(f"Result: {success}, {msg}")

        sessions = get_claude_sessions_from_terminals()
        print(f"Claude sessions: {sessions}")
