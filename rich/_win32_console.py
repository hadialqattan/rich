"""Light wrapper around the win32 Console API"""
import sys
from typing import NamedTuple
from typing.io import IO

from rich.color import ColorSystem
from rich.style import Style
from rich.text import Text

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
    STDOUT = -11
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4

    kernel32 = windll.kernel32
    COORD = wintypes._COORD

    class WindowsCoordinates(NamedTuple):
        """Coordinates in the Windows Console API are (y, x), not (x, y).
        This class is intended to prevent that confusion.
        This class can be used in place of wintypes._COORD in arguments and argtypes.
        """

        row: int
        col: int

        @classmethod
        def from_param(cls, value: "WindowsCoordinates") -> COORD:
            return COORD(value.row, value.col)

    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
        _fields_ = [
            ("dwSize", COORD),
            ("dwCursorPosition", COORD),
            ("wAttributes", wintypes.WORD),
            ("srWindow", wintypes.SMALL_RECT),
            ("dwMaximumWindowSize", COORD),
        ]

    _GetStdHandle = kernel32.GetStdHandle
    _GetStdHandle.argtypes = [
        wintypes.DWORD,
    ]
    _GetStdHandle.restype = wintypes.HANDLE

    def GetStdHandle(handle: int = STDOUT) -> wintypes.HANDLE:
        return _GetStdHandle(handle)

    _GetConsoleMode = kernel32.GetConsoleMode
    _GetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.LPDWORD]
    _GetConsoleMode.restype = wintypes.BOOL

    def GetConsoleMode(
        std_handle: wintypes.HANDLE, console_mode: wintypes.DWORD
    ) -> bool:
        return _GetConsoleMode(std_handle, console_mode)

    _FillConsoleOutputCharacterW = windll.kernel32.FillConsoleOutputCharacterW
    _FillConsoleOutputCharacterW.argtypes = [
        wintypes.HANDLE,
        ctypes.c_char,
        wintypes.DWORD,
        WindowsCoordinates,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputCharacterW.restype = wintypes.BOOL

    def FillConsoleOutputCharacter(
        std_handle: wintypes.HANDLE,
        char: str,
        length: int,
        start_coords: WindowsCoordinates,
    ) -> int:
        """Writes a character to the console screen buffer a specified number of times, beginning at the specified coordinates."""
        assert len(char) == 1
        char = ctypes.c_char(char.encode())
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        x, y = start_coords
        _FillConsoleOutputCharacterW(
            std_handle,
            char,
            length,
            WindowsCoordinates(row=y, col=x),
            byref(num_written),
        )
        return num_written.value

    _SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute
    _SetConsoleTextAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
    ]
    _SetConsoleTextAttribute.restype = wintypes.BOOL

    def SetConsoleTextAttribute(
        std_handle: wintypes.HANDLE, attributes: wintypes.WORD
    ) -> bool:
        # TODO: Check the actual return types - it probably isnt a bool, will likely be wintypes.BOOL
        return _SetConsoleTextAttribute(std_handle, attributes)

    _GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
    _GetConsoleScreenBufferInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO),
    ]
    _GetConsoleScreenBufferInfo.restype = wintypes.BOOL

    def GetConsoleScreenBufferInfo(
        std_handle: wintypes.HANDLE,
    ) -> CONSOLE_SCREEN_BUFFER_INFO:
        console_screen_buffer_info = CONSOLE_SCREEN_BUFFER_INFO()
        _GetConsoleScreenBufferInfo(std_handle, byref(console_screen_buffer_info))
        return console_screen_buffer_info

    class LegacyWindowsTerm:

        WINDOWS_COLORS = {
            "black": 0,
            "blue": 1,
            "green": 2,
            "cyan": 3,
            "red": 4,
            "magenta": 5,
            "yellow": 6,
            "grey": 7,
        }

        def __init__(self, file: IO[str] = sys.stdout):
            self.file = file
            handle = GetStdHandle(STDOUT)
            self._handle = handle
            self._default_attributes = GetConsoleScreenBufferInfo(handle).wAttributes

            self.write = file.write
            self.flush = file.flush

        def write_text(self, text: str) -> None:
            self.write(text)
            self.flush()

        def write_styled(self, text: str, style: Style) -> None:
            fore = style.color.name  # .downgrade(ColorSystem.WINDOWS).number or 1
            back = style.bgcolor.name  # .downgrade(ColorSystem.WINDOWS).number or 1

            # TODO: Write now we're just looking up the number associated with the ANSI name,
            #  so this only works for ANSI colors at the moment.
            #  Do we want Color.downgrade(WINDOWS) to return a Color with a number that we can
            #  use to index into WINDOWS_PALETTE?
            fore_idx = self.WINDOWS_COLORS[fore]
            back_idx = self.WINDOWS_COLORS[back]

            SetConsoleTextAttribute(
                self._handle, attributes=ctypes.c_ushort(fore_idx + back_idx * 16)
            )
            self.write_text(text)
            SetConsoleTextAttribute(self._handle, attributes=self._default_attributes)

    if __name__ == "__main__":
        handle = GetStdHandle()
        console_mode = wintypes.DWORD()
        GetConsoleMode(handle, console_mode)
        # print(console_mode.value)

        # FillConsoleOutputCharacter(handle, "X", 20, WindowsCoordinates(row=10, col=10))

        style = Style(color="black", bgcolor="red")

        # term = LegacyWindowsTerm()
        # term.write_styled("Hello, world!", style)

        from rich.console import Console

        console = Console()

        text = Text("Hello world!", style=style)

        console.print(text)
