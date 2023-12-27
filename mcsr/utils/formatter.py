import json
from ..typing import *


class Colors(Enum):
    black = 'black'
    dark_blue = 'dark_blue'
    dark_green = 'dark_green'
    dark_aqua = 'dark_aqua'
    dark_red = 'dark_red'
    dark_purple = 'dark_purple'
    gold = 'gold'
    gray = 'gray'
    dark_gray = 'dark_gray'
    blue = 'blue'
    green = 'green'
    aqua = 'aqua'
    red = 'red'
    light_purple = 'light_purple'
    yellow = 'yellow'
    white = 'white'
    reset = 'reset'


class JsonText:
    class ClickEvent:
        def __init__(self, type: Literal['open_url', 'open_file', 'run_command', 'suggest_command', 'change_page', 'copy_to_clipboard'], value: str) -> None:
            return {
                'action': type,
                'value': value
            }


    class HoverEvent:
        def __init__(self, type: Literal['show_text', 'show_item', 'show_entity'], contents: dict) -> None:
            return {
                'action': type,
                'contents': contents
            }


    def __init__(self, text: str=None, selector: str=None, color: Union[Colors, str]=None, bold: bool=False, italic: bool=False, underlined: bool=False, strikethrough: bool=False, obfuscated: bool=False, insertion: Optional[str]=None, click_event: Optional[ClickEvent]=None, hover_event: Optional[HoverEvent]=None) -> None:
        if text:
            self._data = { 'text': text }
        if selector:
            self._data = { 'selector': selector }
        if 'text' in self._data.keys() and 'selector' in self._data.keys():
            raise ValueError('text，selector 不能同时存在')
        if len(self._data.items()) == 0:
            raise ValueError('必须指定 text，selector 中的一个')


        if color:
            self._data['color'] = color.value if isinstance(color, Colors) else color
        if bold:
            self._data['bold'] = True
        if italic:
            self._data['italic'] = True
        if underlined:
            self._data['underlined'] = True
        if strikethrough:
            self._data['strikethrough'] = True
        if obfuscated:
            self._data['obfuscated'] = True
        if insertion:
            self._data['insertion'] = insertion
        if click_event:
            self._data['clickEvent'] = click_event
        if hover_event:
            self._data['hoverEvent'] = hover_event

    def format(self) -> str:
        return json.dumps(self._data, ensure_ascii=False)


class Texts:
    def __init__(self, *args: JsonText) -> None:
        self._data = [arg._data for arg in args]

    def format(self) -> str:
        return json.dumps(self._data, ensure_ascii=False)
