import json
from textual.widgets import Static, Label
from textual.screen import ModalScreen
from textual.containers import Vertical, VerticalScroll
from rich.syntax import Syntax

class JsonPopup(ModalScreen):
    def __init__(self, log_data):
        super().__init__()
        self.log_data = log_data

    def compose(self):
        with Vertical():
            with VerticalScroll(id="json_scroll_area"):
                json_text = json.dumps(self.log_data, indent=4)

                colored_json = Syntax(json_text, "json", theme="monokai", background_color="default")

                yield Static(colored_json)

            yield Label(" ← Back (Press ESC)", id="back_hint")

    def on_key(self, event):
        if event.key == "escape":
            self.app.pop_screen()

    DEFAULT_CSS = """
    JsonPopup { background: $background; }
    #json_scroll_area { height: 1fr; padding: 1; }
    #back_hint {
        background: $surface;
        color: $text-muted;
        width: 100%;
        height: 3;
        content-align: center middle;
        border-top: solid $panel;
    }
    """
