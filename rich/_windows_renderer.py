from typing import IO, Iterable

from rich._win32_console import LegacyWindowsTerm
from rich.segment import Segment


def buffer_to_win32_calls(buffer: Iterable[Segment], file: IO[str]) -> None:
    term = LegacyWindowsTerm(file)
    for segment in buffer:
        text = segment.text
        style = segment.style
        if style:
            term.write_styled(text, segment.style)
        else:
            term.write_text(text)


if __name__ == "__main__":
    import sys

    try:
        import ctypes
        from ctypes import LibraryLoader, Structure, Union, byref, wintypes

        if sys.platform == "win32":
            windll = LibraryLoader(ctypes.WinDLL)
        else:
            windll = None
            raise ImportError("Not windows")
    except:
        windll = None
    else:
        pass

    WriteConsole = windll.kernel32.WriteConsole

    STDOUT = -11
    handle = windll.kernel32.GetStdHandle(STDOUT)

    WriteConsole(
        handle,
    )
