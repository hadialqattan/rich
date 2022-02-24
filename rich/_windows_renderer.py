from typing import IO, Iterable

from rich._win32_console import LegacyWindowsTerm
from rich.segment import Segment


def buffer_to_win32_calls(buffer: Iterable[Segment], file: IO[str]) -> None:
    term = LegacyWindowsTerm(file)
    for segment in buffer:
        print("/", end="")
        text = segment.text
        style = segment.style
        if style:
            term.write_styled(text, segment.style)
        else:
            term.write_text(text)
        # print(f"/[{segment}]", end="")
