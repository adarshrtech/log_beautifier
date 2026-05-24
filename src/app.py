import csv
import os
import asyncio
from collections import Counter

from datetime import datetime
from textual.app import App

from textual.screen import ModalScreen
from textual.widgets import Header, Footer, DataTable, Input, Static, LoadingIndicator, Button
from rich.markup import escape

from src.loadaudit import load_audit_logs
from src.jsonpopup import JsonPopup


class StatsScreen(ModalScreen):
    def __init__(self, stats_text):
        super().__init__()
        self.stats_text = stats_text

    def compose(self):
        yield Static(self.stats_text, id="stats_view")
        yield Button("Close", id="close_stats")

    def on_button_pressed(self, event):
        self.dismiss()

class AuditApp(App):
    CSS = """
    DataTable { height: 1fr; border-top: solid $panel; }
    Input { margin: 1; border: solid white; }
    #results_count { margin-left: 2; color: $text-muted; height: 1; }
    
    LoadingIndicator {
        background: $background 50%;
        color: $accent;
    }
    """

    # We keep the 'm' binding here - it will show up automatically in the Footer!
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "clear", "Clear Search"),
        ("s", "save_csv", "Save to CSV"),
        ("m", "load_more", "Load More (+1k)"), 
        ("tab", "focus_next", "Switch Focus"),
        ("t", "show_stats", "Show Stats")
    ]

    def __init__(self, log_file_path):
        super().__init__()
        self.log_file_path = log_file_path
        self.all_logs = []       
        self.current_logs = []   
        self.search_task = None  
        self.display_count = 1000  
        self.show_stats = False

    def compose(self):
        yield Header()
        yield Input(placeholder="Search logs...", id="search_input")
        
        yield Static("Found 0 logs", id="results_count")
        yield DataTable(zebra_stripes=True, cursor_type="row")
        yield Footer() # This will now show the 'M' key shortcut clearly

    def on_mount(self):
        self.all_logs = load_audit_logs(self.log_file_path)

        self.current_logs = self.all_logs

        table = self.query_one(DataTable)
        table.add_column("TIME", key="time")
        table.add_column("USER", key="user")
        table.add_column("CODE", key="code")
        table.add_column("METHOD", key="method")
        table.add_column("URI", key="uri")
        
        self.update_table(self.all_logs)
        self.query_one("#search_input").focus()

    def update_table(self, logs_to_show, reset_pagination=True):
        if reset_pagination:
            self.display_count = 1000

        self.current_logs = logs_to_show
        table = self.query_one(DataTable)
        
        table.loading = True
        table.clear()

        count_label = self.query_one("#results_count")
        
        # Professional status label
        if len(logs_to_show) > self.display_count:
            count_label.update(f"Found {len(logs_to_show)} logs | [b]Showing {self.display_count}[/] (Press 'M' for more)")
        else:
            count_label.update(f"Found {len(logs_to_show)} logs")

        logs_to_render = logs_to_show[:self.display_count]

        for index, log in enumerate(logs_to_render):
            user_data = log.get("user", {})
            user = user_data.get("name") or user_data.get("username") or "unknown"
            code = str(log.get("responseCode") or log.get("responseStatus", {}).get("code", ""))
            time_raw = log.get("requestTimestamp") or log.get("requestReceivedTimestamp") or ""
            time = time_raw[11:19]
            method = log.get("method") or log.get("verb") or ""
            uri = log.get("requestURI", "")

            color = "[red]" if code.startswith(("4", "5")) else "[green]"

            table.add_row(
                escape(time), escape(user), f"{color}{code}[/]", 
                escape(method), escape(uri), key=str(index)
            )
        
        table.loading = False

    def action_load_more(self):
        """Logic for the 'M' key shortcut"""
        if len(self.current_logs) > self.display_count:
            self.display_count += 1000
            self.update_table(self.current_logs, reset_pagination=False)
            # A tiny notification to confirm it worked
            self.notify(f"Display expanded to {self.display_count} rows")
        else:
            self.notify("All results already displayed", severity="warning")

    def on_data_table_header_selected(self, event):
        table = self.query_one(DataTable)
        table.sort(event.column_key)

    async def action_save_csv(self):
        spinner = LoadingIndicator()
        await self.mount(spinner)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"output/audit_export_{timestamp}.csv"
        
        if not os.path.exists("output"):
            os.makedirs("output")

        try:
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["TIME", "USER", "CODE", "METHOD", "URI"])
                for log in self.current_logs:
                    user_data = log.get("user", {})
                    user = user_data.get("name") or user_data.get("username") or "unknown"
                    code = str(log.get("responseCode") or log.get("responseStatus", {}).get("code", ""))
                    time_raw = log.get("requestTimestamp") or log.get("requestReceivedTimestamp") or ""
                    time = time_raw[11:19]
                    method = log.get("method") or log.get("verb") or ""
                    uri = log.get("requestURI", "")
                    writer.writerow([time, user, code, method, uri])
            self.notify(f"Saved to {output_file}", title="CSV Exported")
        except Exception as e:
            self.notify(f"Export Failed: {str(e)}", severity="error")
        finally:
            await spinner.remove()

    async def on_input_changed(self, event):
        if self.search_task:
            self.search_task.cancel()
        self.search_task = asyncio.create_task(self.run_delayed_search(event.value))

    async def run_delayed_search(self, text):
        try:
            await asyncio.sleep(0.3)
            self.perform_search(text)
        except asyncio.CancelledError:
            pass

    def perform_search(self, search_text):
        search_text = search_text.lower()
        if not search_text:
            self.update_table(self.all_logs)
            return

        filtered_list = []
        for log in self.all_logs:
            user_data = log.get("user", {})
            user = str(user_data.get("name") or user_data.get("username") or "").lower()
            code = str(log.get("responseCode") or log.get("responseStatus", {}).get("code", ""))
            uri = log.get("requestURI", "").lower()
            method = str(log.get("method") or log.get("verb") or "").lower()

            if any(search_text in field for field in [user, code, uri, method]):
                filtered_list.append(log)

        self.update_table(filtered_list)

    def on_input_submitted(self):
        self.query_one(DataTable).focus()

    def on_data_table_row_selected(self, event):
        row_index = int(event.row_key.value)
        selected_log = self.current_logs[row_index]
        self.push_screen(JsonPopup(selected_log))

    def action_clear(self):
        search_bar = self.query_one("#search_input")
        search_bar.value = ""
        search_bar.focus()
    def get_top_uris(self, logs, top_n=25):
        uris = []
        for entry in logs:
            uri = entry.get("requestURI", "unknown")
            uris.append(uri)

        counter = Counter(uris)
        return counter.most_common(top_n)


    def format_top_uris(self, logs):
        top_uris = self.get_top_uris(logs)

        lines = ["[bold #FFA500]Top URIs:[/bold #FFA500]"]
        for i, (uri, count) in enumerate(top_uris, 1):
            lines.append(f"{i}. {uri} ({count})")

        return "\n".join(lines)
    def get_top_failing_uris(self, logs, top_n=25):
        stats = {}

        for entry in logs:
            code = str(
                entry.get("responseCode") or
                entry.get("responseStatus", {}).get("code") or
                ""
            )

            if code.startswith(("4", "5")):
                uri = entry.get("requestURI", "unknown").split("?")[0]

                if uri not in stats:
                    stats[uri] = {"total": 0, "5xx": 0, "4xx": 0}

                stats[uri]["total"] += 1

                if code.startswith("5"):
                    stats[uri]["5xx"] += 1
                else:
                    stats[uri]["4xx"] += 1

        sorted_uris = sorted(
            stats.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )

        return sorted_uris[:top_n]
    def format_top_failing_uris(self, logs):
        top_uris = self.get_top_failing_uris(logs)

        lines = ["[bold red]Top Failing URIs:[/bold red]"]

        for i, (uri, data) in enumerate(top_uris, 1):
            lines.append(
                f"{i}. {uri} "
                f"(total: {data['total']}, 5xx: {data['5xx']}, 4xx: {data['4xx']})"
            )

        return "\n".join(lines)
    def get_top_slow_requests(self, logs, top_n=25):
        slow = []

        for entry in logs:
            latency = self.get_latency(entry)

            if latency != "-":
                value = float(latency.replace("s", ""))
                uri = entry.get("requestURI", "unknown").split("?")[0]
                slow.append((uri, value))

        slow_sorted = sorted(slow, key=lambda x: x[1], reverse=True)
        return slow_sorted[:top_n]
    def format_top_slow_requests(self, logs):
        top = self.get_top_slow_requests(logs)

        lines = ["[bold yellow]Top Slow Requests:[/bold yellow]"]

        for i, (uri, latency) in enumerate(top, 1):
            lines.append(f"{i}. {uri} ({latency:.3f}s)")

        return "\n".join(lines)
    def get_latency(self, entry):
        try:
            if entry.get("verb") == "watch":
                return "-"

            if "responseTimestamp" in entry:
                start = entry.get("requestReceivedTimestamp") or entry.get("requestTimestamp")
                end = entry.get("responseTimestamp")

            elif entry.get("stage") == "ResponseComplete":
                start = entry.get("requestReceivedTimestamp")
                end = entry.get("stageTimestamp")

            else:
                return "-"

            if start and end:
                t1 = datetime.fromisoformat(start.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(end.replace("Z", "+00:00"))
                return f"{(t2 - t1).total_seconds():.3f}s"

        except Exception:
            pass

        return "-"
    def get_top_users(self, logs, top_n=25):
        users = []

        for entry in logs:
            user = (
                entry.get("user", {}).get("name") or
                entry.get("user", {}).get("username") or
                "unknown"
            )
            users.append(user)

        counter = Counter(users)
        return counter.most_common(top_n)
    def format_top_users(self, logs):
        top_users = self.get_top_users(logs)

        lines = ["[bold cyan]Top Users:[/bold cyan]"]

        for i, (user, count) in enumerate(top_users, 1):
            lines.append(f"{i}. {user} ({count})")

        return "\n".join(lines)
    def action_show_stats(self):
        text = (
            self.format_top_uris(self.current_logs)
            + "\n\n----------------------\n\n"
            + self.format_top_failing_uris(self.current_logs)
            + "\n\n----------------------\n\n"
            + self.format_top_slow_requests(self.current_logs)
            + "\n\n----------------------\n\n"
            + self.format_top_users(self.current_logs)
        )

        self.push_screen(StatsScreen(text))