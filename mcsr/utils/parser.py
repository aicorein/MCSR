from ..typing import *


class CmdParser:
    class Matched:
        def __init__(self, cmd: str, args: List[str]=None) -> None:
            self.cmd = cmd
            self.args = args

        def verify(self, cmd: str, args_num: int=0) -> bool:
            if self.args is None:
                num = 0
            else:
                num = len(self.args)
            return self.cmd == cmd and num == args_num

    def __init__(self, start_char: str, sep_char: str) -> None:
        self.start = start_char
        self.sep = sep_char

    def parse(self, string: str):
        string = string.strip('\n').strip(' ')
        if len(string) == 0 or string[0] != self.start:
            return None
        else:
            string = string[1:]
            parts = string.split(self.sep)
            if len(parts) == 1:
                return CmdParser.Matched(parts[0])
            else:
                return CmdParser.Matched(parts.pop(0), parts)
