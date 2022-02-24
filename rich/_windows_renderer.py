from typing import IO, Iterable, Sequence

from rich._win32_console import LegacyWindowsTerm, WindowsCoordinates
from rich.segment import ControlCode, ControlType, Segment


def legacy_windows_render(buffer: Iterable[Segment], file: IO[str]) -> None:
    term = LegacyWindowsTerm(file)
    for segment in buffer:
        # print("/", end="")
        text, style, control = segment
        if style:
            term.write_styled(text, segment.style)
        else:
            term.write_text(text)

        control_codes: Sequence[ControlCode] = control or []
        for control_code in control_codes:
            control_type = control_code[0]
            if control_type == ControlType.CURSOR_MOVE_TO:
                # TODO
                _, x, y = control_code
                term.move_cursor_to(WindowsCoordinates(row=y - 1, col=x - 1))

        # print(f"/[{segment}]", end="")
