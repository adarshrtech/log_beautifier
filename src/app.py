import csv
import os
import asyncio
from datetime import datetime
from collections import Counter
from textual.app import App
from textual.widgets import Header, Footer, DataTable, Input, Static, LoadingIndicator, Button
from textual.screen import ModalScreen
from rich.markup import escape
from rich.table import Table
from rich.panel import Panel

# Local imports
from src.loadaudit import load_audit_logs
from src.jsonpopup import JsonPopup

class StatsScreen(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss", "Close")
    ]

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
    DataTable { height: 1fr; border-top: solid white; }
    Input { margin: 1; border: solid white; }
    #results_count { margin-left: 2; color: white; height: 1; }
    #summary_area {
        height: auto;
        margin: 0 1;
        border: solid blue;
    }
    LoadingIndicator {
        background: black 50%;
        color: blue;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "clear", "Clear Search"),
        ("s", "save_csv", "Save to CSV"),
        ("m", "load_more", "Load More (+1k)"),
        ("g", "jump_to_end", "End (G)"),
        ("h", "jump_to_start", "Home (H)"),
        ("tab", "focus_next", "Switch Focus"),
        ("tab", "focus_next", "Switch Focus"),
        ("t", "show_stats", "Show Stats"),
        ("x", "show_recent_actions", "Recent Actions")
    ]

    def __init__(self, log_file_path):
        super().__init__()
        self.log_file_path = log_file_path
        self.all_logs = []
        self.current_logs = []
        self.search_task = None
        self.display_count = 1000

    def compose(self):
        yield Header()
        yield Input(placeholder="Search logs (Time, User, URI...)", id="search_input")
        yield Static("", id="summary_area")
        yield Static("Found 0 logs", id="results_count")
        yield DataTable(zebra_stripes=True, cursor_type="row")
        yield Footer()

    def on_mount(self):
        raw_logs = load_audit_logs(self.log_file_path)
        # Store original line index for the # column
        for idx, log in enumerate(raw_logs, 1):
            log["_line_number"] = idx

        self.all_logs = raw_logs
        self.current_logs = self.all_logs

        table = self.query_one(DataTable)
        table.add_column("#", key="line_no")
        table.add_column("TIME", key="time")
        table.add_column("USER", key="user")
        table.add_column("CODE", key="code")
        table.add_column("METHOD", key="method")
        table.add_column("URI", key="uri")

        self.update_dashboard(self.all_logs)
        self.update_table(self.all_logs)
        self.query_one("#search_input").focus()

    def update_dashboard(self, logs_to_analyze):
        if not logs_to_analyze:
            self.query_one("#summary_area").update(Panel("[yellow]No matches found.[/]", title="Dashboard"))
            return

        codes = [str(l.get("responseCode") or l.get("responseStatus", {}).get("code", "unk")) for l in logs_to_analyze]
        uris = [l.get("requestURI", "unknown") for l in logs_to_analyze]
        users = [l.get("user", {}).get("name") or l.get("user", {}).get("username") or "unknown" for l in logs_to_analyze]

        status_counts = Counter(codes).most_common(10)
        top_10_api = Counter(uris).most_common(10)
        top_5_users = Counter(users).most_common(5)

        summary_table = Table(show_header=True, header_style="bold magenta", expand=True, box=None)
        summary_table.add_column("📊 HTTP Status Codes (count)", justify="left", width=28, no_wrap=True)
        summary_table.add_column("👤 Top Users (Hits)", justify="left", width=32, no_wrap=True)
        summary_table.add_column("🔗 Top 10 API Calls", justify="left", no_wrap=True)

        status_lines = [f"• [{( 'green' if c.startswith('2') else 'yellow' if c.startswith('4') else 'red' if c.startswith('5') else 'white' )}]{c:<3}[/]: {count}" for c, count in status_counts]
        user_lines = [f"{i}. [yellow][{count}][/] {name[:20]}" for i, (name, count) in enumerate(top_5_users, 1)]
        api_lines = [f"{i:>2}. [yellow][{count}][/] {uri[:80]}" for i, (uri, count) in enumerate(top_10_api, 1)]

        summary_table.add_row("\n".join(status_lines), "\n".join(user_lines), "\n".join(api_lines))
        self.query_one("#summary_area").update(Panel(summary_table, title="[bold blue]Audit Dashboard[/]", border_style="blue"))

    def update_table(self, logs_to_show, reset_pagination=True):
        if reset_pagination:
            self.display_count = 1000
        self.current_logs = logs_to_show
        table = self.query_one(DataTable)
        table.loading = True
        table.clear()

        count_label = self.query_one("#results_count")
        count_label.update(f"Found {len(logs_to_show)} logs" + (f" | [b]Showing {self.display_count}[/] (Press 'M' for more)" if len(logs_to_show) > self.display_count else ""))

        for index, log in enumerate(logs_to_show[:self.display_count]):
            line_no = str(log.get("_line_number", ""))
            user_data = log.get("user", {})
            user = user_data.get("name") or user_data.get("username") or "unknown"
            code = str(log.get("responseCode") or log.get("responseStatus", {}).get("code", ""))
            time_raw = log.get("requestTimestamp") or log.get("requestReceivedTimestamp") or ""
            time = time_raw[11:19]
            method, uri = log.get("method") or log.get("verb") or "", log.get("requestURI", "")
            color = "[red]" if code.startswith(("4", "5")) else "[green]"

            table.add_row(f"[grey37]{line_no}[/]", escape(time), escape(user), f"{color}{code}[/]", escape(method), escape(uri), key=str(index))

        table.loading = False

    def action_jump_to_end(self):
        """Instant Jump to End - No popup notifications."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            table.move_cursor(row=table.row_count - 1, animate=False)

    def action_jump_to_start(self):
        """Instant Jump to Start - No popup notifications."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            table.move_cursor(row=0, animate=False)

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
            self.update_dashboard(self.all_logs)
            self.update_table(self.all_logs)
            return

        filtered_list = []
        for log in self.all_logs:
            user_data = log.get("user", {})
            user = str(user_data.get("name") or user_data.get("username") or "").lower()
            code = str(log.get("responseCode") or log.get("responseStatus", {}).get("code", ""))
            uri = log.get("requestURI", "").lower()
            method = str(log.get("method") or log.get("verb") or "").lower()
            time_raw = log.get("requestTimestamp") or log.get("requestReceivedTimestamp") or ""
            time = time_raw[11:19].lower()
            line_no = str(log.get("_line_number", ""))

            if any(search_text in field for field in [user, code, uri, method, time, line_no]):
                filtered_list.append(log)

        self.update_dashboard(filtered_list)
        self.update_table(filtered_list)

    def action_load_more(self):
        if len(self.current_logs) > self.display_count:
            self.display_count += 1000
            self.update_table(self.current_logs, reset_pagination=False)

    async def action_save_csv(self):
        spinner = LoadingIndicator()
        await self.mount(spinner)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"output/audit_{timestamp}.csv"
        if not os.path.exists("output"): os.makedirs("output")
        try:
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["#", "TIME", "USER", "CODE", "METHOD", "URI"])
                for log in self.current_logs:
                    user_data = log.get("user", {})
                    user = user_data.get("name") or user_data.get("username") or "unknown"
                    code = str(log.get("responseCode") or log.get("responseStatus", {}).get("code", ""))
                    time_raw = log.get("requestTimestamp") or log.get("requestReceivedTimestamp") or ""
                    time = time_raw[11:19]
                    writer.writerow([log.get("_line_number"), time, user, code, log.get("method") or log.get("verb", ""), log.get("requestURI", "")])
            self.notify(f"Saved to {output_file}")
        finally: await spinner.remove()

    def on_data_table_row_selected(self, event):
        row_index = int(event.row_key.value)
        self.push_screen(JsonPopup(self.current_logs[row_index]))

    def action_clear(self):
        self.query_one("#search_input").value = ""
        self.query_one("#search_input").focus()


    def format_top_uris_25(self, logs):
        uris = [log.get("requestURI", "unknown") for log in logs]
        top_uris = Counter(uris).most_common(25)

        lines = ["[bold #FFA500]Top 25 URIs:[/bold #FFA500]"]

        for i, (uri, count) in enumerate(top_uris, 1):
            lines.append(f"{i}. {uri} ({count})")

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
    
    def format_top_slow_requests_25(self, logs):
        stats = {}

        for entry in logs:
            latency = self.get_latency(entry)

            if latency != "-":
                value = float(latency.replace("s", ""))
                uri = entry.get("requestURI", "unknown").split("?")[0]

                if uri not in stats:
                    stats[uri] = {"count": 0, "total": 0, "max": 0}

                stats[uri]["count"] += 1
                stats[uri]["total"] += value
                stats[uri]["max"] = max(stats[uri]["max"], value)

        results = []

        for uri, data in stats.items():
            avg = data["total"] / data["count"]
            results.append((uri, avg, data["max"], data["count"]))

        results = sorted(results, key=lambda x: x[1], reverse=True)[:25]

        lines = ["[bold yellow]Top Slow APIs by Average Latency:[/bold yellow]"]

        for i, (uri, avg, max_latency, count) in enumerate(results, 1):
            lines.append(
                f"{i}. {uri} "
                f"(avg: {avg:.3f}s, max: {max_latency:.3f}s, count: {count})"
            )

        return "\n".join(lines)
    
    def format_top_failing_apis_25(self, logs):
        stats = {}

        for entry in logs:
            code = str(
                entry.get("responseCode")
                or entry.get("responseStatus", {}).get("code")
                or ""
            )

            if code.startswith(("4", "5")):
                uri = entry.get("requestURI", "unknown").split("?")[0]

                if uri not in stats:
                    stats[uri] = {
                        "total": 0,
                        "5xx": 0,
                        "4xx": 0
                    }

                stats[uri]["total"] += 1

                if code.startswith("5"):
                    stats[uri]["5xx"] += 1
                else:
                    stats[uri]["4xx"] += 1

        results = sorted(
            stats.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )[:25]

        lines = ["[bold red]Top Failing APIs:[/bold red]"]

        for i, (uri, data) in enumerate(results, 1):
            lines.append(
                f"{i}. {uri} "
                f"(total: {data['total']}, "
                f"5xx: {data['5xx']}, "
                f"4xx: {data['4xx']})"
            )

        return "\n".join(lines)
    
    def format_top_users_25(self, logs):
        users = [
            log.get("user", {}).get("name")
            or log.get("user", {}).get("username")
            or "unknown"
            for log in logs
        ]

        top_users = Counter(users).most_common(25)

        lines = ["[bold cyan]Top Users:[/bold cyan]"]

        for i, (user, count) in enumerate(top_users, 1):
            lines.append(f"{i}. {user} ({count})")

        return "\n".join(lines)
    
    def format_top_error_users_25(self, logs):
        stats = {}

        for entry in logs:
            code = str(
                entry.get("responseCode")
                or entry.get("responseStatus", {}).get("code")
                or ""
            )

            if code.startswith(("4", "5")):
                user = (
                    entry.get("user", {}).get("name")
                    or entry.get("user", {}).get("username")
                    or "unknown"
                )

                if user not in stats:
                    stats[user] = {
                        "total": 0,
                        "5xx": 0,
                        "4xx": 0
                    }

                stats[user]["total"] += 1

                if code.startswith("5"):
                    stats[user]["5xx"] += 1
                else:
                    stats[user]["4xx"] += 1

        results = sorted(
            stats.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )[:25]

        lines = ["[bold magenta]Top Error Users:[/bold magenta]"]

        for i, (user, data) in enumerate(results, 1):
            lines.append(
                f"{i}. {user} "
                f"(total: {data['total']}, "
                f"5xx: {data['5xx']}, "
                f"4xx: {data['4xx']})"
            )

        return "\n".join(lines)
    
    def format_recent_modification_actions(self, logs):
        modification_methods = {"DELETE", "PATCH", "PUT", "POST"}

        actions = []

        for entry in reversed(logs):
            method = str(entry.get("method") or entry.get("verb") or "").upper()

            if method in modification_methods:
                user = (
                    entry.get("user", {}).get("name")
                    or entry.get("user", {}).get("username")
                    or "unknown"
                )

                uri = entry.get("requestURI", "unknown").split("?")[0]

                time_raw = (
                    entry.get("requestTimestamp")
                    or entry.get("requestReceivedTimestamp")
                    or ""
                )

                time = time_raw[11:19] if time_raw else "unknown"

                actions.append((time, user, method, uri))

            if len(actions) >= 25:
                break

        lines = ["[bold violet]Recent Modification Actions:[/bold violet]"]

        if not actions:
            lines.append("[dim]No DELETE / PATCH / PUT / POST actions found.[/dim]")
            return "\n".join(lines)

        for i, (time, user, method, uri) in enumerate(actions, 1):
            color = (
                "purple" if method == "DELETE"
                else "yellow" if method in ("PATCH", "PUT")
                else "green"
            )

            lines.append(
                f"{i}. [cyan]{time}[/cyan] "
                f"{user} "
                f"[bold {color}]{method}[/bold {color}] "
                f"{uri}"
            )

        return "\n".join(lines)
    
    def format_recent_deletions(self, logs):
        deletions = []

        for entry in reversed(logs):
            method = str(entry.get("method") or entry.get("verb") or "").upper()

            if method == "DELETE":
                user = (
                    entry.get("user", {}).get("name")
                    or entry.get("user", {}).get("username")
                    or "unknown"
                )

                uri = entry.get("requestURI", "unknown").split("?")[0]

                time_raw = (
                    entry.get("requestTimestamp")
                    or entry.get("requestReceivedTimestamp")
                    or ""
                )

                time = time_raw[11:19] if time_raw else "unknown"

                deletions.append((time, user, uri))

            if len(deletions) >= 25:
                break

        lines = ["[bold purple]Recent Resource Deletions:[/bold purple]"]

        if not deletions:
            lines.append("[dim]No DELETE actions found.[/dim]")
            return "\n".join(lines)

        for i, (time, user, uri) in enumerate(deletions, 1):
            lines.append(
                f"{i}. [red]{time}[/red] "
                f"{user} "
                f"[bold red]DELETE[/bold red] "
                f"{uri}"
            )

        return "\n".join(lines)

    def action_show_stats(self):
        text = (
            self.format_top_uris_25(self.current_logs)
            + "\n\n----------------------\n\n"
            + self.format_top_slow_requests_25(self.current_logs)
            + "\n\n----------------------\n\n"
            + self.format_top_failing_apis_25(self.current_logs)
            + "\n\n----------------------\n\n"
            + self.format_top_users_25(self.current_logs)
            + "\n\n----------------------\n\n"
            + self.format_top_error_users_25(self.current_logs)
        )
        self.push_screen(StatsScreen(text))

    def action_show_recent_actions(self):
        text = (
            self.format_recent_modification_actions(self.current_logs)
            + "\n\n----------------------\n\n"
            + self.format_recent_deletions(self.current_logs)
        )
        self.push_screen(StatsScreen(text))


