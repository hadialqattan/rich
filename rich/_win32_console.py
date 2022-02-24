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
        Rows and columns are indexed from 0.
        This class can be used in place of wintypes._COORD in arguments and argtypes.
        """

        row: int
        col: int

        @classmethod
        def from_param(cls, value: "WindowsCoordinates") -> COORD:
            return COORD(value.col, value.row)

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
        start: WindowsCoordinates,
    ) -> int:
        """Writes a character to the console screen buffer a specified number of times, beginning at the specified coordinates."""
        assert len(char) == 1
        char = ctypes.c_char(char.encode())
        length = wintypes.DWORD(length)
        num_written = wintypes.DWORD(0)
        x, y = start
        _FillConsoleOutputCharacterW(
            std_handle,
            char,
            length,
            WindowsCoordinates(row=y, col=x),
            byref(num_written),
        )
        return num_written.value

    _FillConsoleOutputAttribute = windll.kernel32.FillConsoleOutputAttribute
    _FillConsoleOutputAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
        wintypes.DWORD,
        WindowsCoordinates,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _FillConsoleOutputAttribute.restype = wintypes.BOOL

    def FillConsoleOutputAttribute(
        std_handle: wintypes.HANDLE,
        attributes: int,
        length: int,
        start: WindowsCoordinates,
    ) -> int:
        length = wintypes.DWORD(length)
        attributes = wintypes.WORD(attributes)
        num_written = wintypes.DWORD(0)
        _FillConsoleOutputAttribute(
            std_handle, attributes, length, start, byref(num_written)
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
        # TODO: Check the actual return types - it probably isn't a bool, will likely be wintypes.BOOL
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

    _SetConsoleCursorPosition = windll.kernel32.SetConsoleCursorPosition
    _SetConsoleCursorPosition.argtypes = [
        wintypes.HANDLE,
        WindowsCoordinates,
    ]
    _SetConsoleCursorPosition.restype = wintypes.BOOL

    def SetConsoleCursorPosition(
        std_handle: wintypes.HANDLE, coords: WindowsCoordinates
    ) -> bool:
        if coords.col < 0 or coords.row < 0:
            return False
        return _SetConsoleCursorPosition(std_handle, coords)

    class LegacyWindowsTerm:

        # WINDOWS_COLORS = {
        #     "black": 0,
        #     "blue": 1,
        #     "green": 2,
        #     "cyan": 3,
        #     "red": 4,
        #     "magenta": 5,
        #     "yellow": 6,
        #     "grey": 7,
        # }

        # Keys are ANSI color numbers, values are the corresponding Windows Console API color numbers
        ANSI_TO_WINDOWS = {0: 0, 1: 4, 2: 2, 3: 6, 4: 1, 5: 5, 6: 3, 7: 7}

        def __init__(self, file: IO[str] = sys.stdout):
            self.file = file
            handle = GetStdHandle(STDOUT)
            self._handle = handle
            default_text = GetConsoleScreenBufferInfo(handle).wAttributes
            self._default_text = default_text

            self._default_fore = default_text & 7
            self._default_back = (default_text >> 4) & 7
            # self._style = default_text & (WinStyle.BRIGHT | WinStyle.BRIGHT_BACKGROUND)

            self._default_attrs = self._default_fore + self._default_back * 16

            self.write = file.write
            self.flush = file.flush

        @property
        def cursor_position(self) -> WindowsCoordinates:
            """Returns the current position of the cursor (0-based)"""
            coord: COORD = GetConsoleScreenBufferInfo(self._handle).dwCursorPosition
            return WindowsCoordinates(row=coord.Y, col=coord.X)

        @property
        def screen_size(self) -> WindowsCoordinates:
            """Returns the current size of the console screen buffer, in character columns and rows"""
            screen_size: COORD = GetConsoleScreenBufferInfo(self._handle).dwSize
            return WindowsCoordinates(row=screen_size.Y, col=screen_size.X)

        def write_text(self, text: str) -> None:
            self.write(text)
            self.flush()

        def write_styled(self, text: str, style: Style) -> None:
            if style.color:
                fore = style.color.downgrade(ColorSystem.WINDOWS).number
                fore = self.ANSI_TO_WINDOWS.get(fore, self._default_fore)
            else:
                fore = self._default_fore

            if style.bgcolor:
                back = style.bgcolor.downgrade(ColorSystem.WINDOWS).number
                back = self.ANSI_TO_WINDOWS.get(back, self._default_back)
            else:
                back = self._default_back

            SetConsoleTextAttribute(
                self._handle, attributes=ctypes.c_ushort(fore + back * 16)
            )
            self.write_text(text)
            SetConsoleTextAttribute(self._handle, attributes=self._default_text)

        def move_cursor_to(self, new_position: WindowsCoordinates) -> None:
            SetConsoleCursorPosition(self._handle, new_position)

        def erase_line(self) -> None:
            screen_size = self.screen_size
            cursor_position = self.cursor_position
            cells_to_erase = screen_size.col
            start_coordinates = WindowsCoordinates(cursor_position.row, 0)
            FillConsoleOutputCharacter(
                self._handle, " ", cells_to_erase, start_coordinates
            )

        def erase_end_of_line(self) -> None:
            cursor_position = self.cursor_position
            cells_to_erase = self.screen_size.col - cursor_position.col
            FillConsoleOutputCharacter(
                self._handle, " ", cells_to_erase, cursor_position
            )

        def move_cursor_up(self):
            cursor_position = self.cursor_position
            SetConsoleCursorPosition(
                self._handle,
                WindowsCoordinates(
                    row=cursor_position.row - 1, col=cursor_position.col
                ),
            )

        def move_cursor_line_start(self):
            cursor_position = self.cursor_position
            SetConsoleCursorPosition(
                self._handle, WindowsCoordinates(cursor_position.row, 0)
            )

    if __name__ == "__main__":
        handle = GetStdHandle()
        console_mode = wintypes.DWORD()
        GetConsoleMode(handle, console_mode)
        # print(console_mode.value)

        # FillConsoleOutputCharacter(handle, "X", 20, WindowsCoordinates(row=10, col=10))

        style = Style(color="black", bgcolor="red")

        from rich.console import Console

        console = Console()
        text = Text("Hello world!", style=style)
        console.print(text)

        # console.print("[bold green]Hello world!")
        # console.print("[italic cyan]Hello world!")
        # console.print("[bold black on blue]Hello world!")
        # console.print("[bold black on cyan]Hello world!")
        # console.print("[black on green]Hello world!")
        # console.print("[blue on green]Hello world!")
        # console.print("[#1BB152 on #DA812D]Hello\nworld!")

        term = LegacyWindowsTerm()
        # print("0. Initial position:", term.cursor_position)
        # term.write_styled("Hello, world!", style)
        # print("1. After write_styled:", term.cursor_position)
        # term.move_cursor_up()
        # print("2. After move_cursor_up:", term.cursor_position)
        # term.write_styled("2nd", style)
        # print("3. After write_styled:", term.cursor_position)
        # term.erase_end_of_line()

        term.write_text("Hello, world!")
        print()
        print()
        print()
        print()
        print()
        print("1", term.cursor_position)
        print("aksjdlaskjd", end="")
        term.move_cursor_up()
        term.move_cursor_up()
        term.move_cursor_up()
        term.move_cursor_up()
        term.move_cursor_up()
        print("2", term.cursor_position, end="")
        term.move_cursor_up()
        print("3", term.cursor_position, end="")
