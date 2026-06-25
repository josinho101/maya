import json
import os
from datetime import datetime
from string import Template
from configs.settings import PATHS

_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "execution_report.html")


class ExecutionStorage:

    @staticmethod
    def save(project_path, results):

        projectName = project_path.split("/")[-1]
        out_dir = f"{PATHS['execution_results']}/{projectName}"
        lastest_dir = os.path.join(out_dir, "latest")
        history_dir = os.path.join(out_dir, "history")

        os.makedirs(lastest_dir, exist_ok=True)
        os.makedirs(history_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        latest_json_path = os.path.join(lastest_dir, "execution_report.json")
        latest_html_path = os.path.join(lastest_dir, "execution_report.html")

        history_json_path = os.path.join(
            history_dir, f"execution_report_{timestamp}.json"
        )
        history_html_path = os.path.join(
            history_dir, f"execution_report_{timestamp}.html"
        )

        for path in [latest_json_path, history_json_path]:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(results, file, indent=2)

        ExecutionStorage.generate_html_report(results, latest_html_path)
        ExecutionStorage.generate_html_report(results, history_html_path)

        return {
            "latest_json_report": latest_json_path,
            "latest_html_report": latest_html_path,
            "history_json_report": history_json_path,
            "history_html_report": history_html_path,
        }

    @staticmethod
    def generate_html_report(results, html_path):

        total = len(results)
        passed = len([r for r in results if r.get("status") == "PASS"])
        failed = len([r for r in results if r.get("status") == "FAIL"])
        skipped = len([r for r in results if r.get("status") == "SKIPPED"])
        rated = total - skipped
        success_rate = round((passed / rated) * 100, 2) if rated > 0 else 0
        total_execution_time = round(
            sum(result.get("execution_time_ms", 0) for result in results), 2
        )

        rows = ""

        for result in results:

            status = result.get("status", "")

            if status == "PASS":
                row_color = "rgba(102, 187, 106, 0.12)"
                badge_class = "pass-badge"
            elif status == "FAIL":
                row_color = "rgba(239, 83, 80, 0.12)"
                badge_class = "fail-badge"
            elif status == "SKIPPED":
                row_color = "rgba(158, 158, 158, 0.12)"
                badge_class = "skip-badge"
            else:
                row_color = "transparent"
                badge_class = ""

            response_body = result.get("response_body", "")
            execution_time = result.get("execution_time_ms", "")
            request_data = result.get("request", {})
            request_json = json.dumps(request_data, indent=2)
            verification_error = ""

            if status == "FAIL":
                verification_details = result.get("validation_details", [])
                failed_checks = [
                    check for check in verification_details
                    if not check.get("passed", True)
                ]
                if failed_checks:
                    verification_error = json.dumps(failed_checks, indent=2)
            elif status == "SKIPPED":
                verification_error = result.get("skip_reason", "")

            error_cell = (
                f"<details class='expandable'>"
                f"<summary>View</summary>"
                f"<div class='json-view'><pre>{verification_error}</pre></div>"
                f"</details>"
                if verification_error else ""
            )

            tc_id_lower = result.get("tc_id", "").lower()
            scenario_lower = result.get("test_scenario", "").lower()

            rows += f"""
            <tr style="background-color:{row_color}"
                data-status="{status}"
                data-tcid="{tc_id_lower}"
                data-scenario="{scenario_lower}">
                <td>{result.get("tc_id", "")}</td>
                <td>{result.get("test_scenario", "")}</td>
                <td>{result.get("lifecycle_role", "")}</td>
                <td><span class="{badge_class}">{status}</span></td>
                <td>{result.get("expected_status_code", "")}</td>
                <td>{result.get("actual_status_code", "")}</td>
                <td>{execution_time} ms</td>
                <td>
                    <details class="expandable">
                        <summary>View Request</summary>
                        <div class="json-view"><pre>{request_json}</pre></div>
                    </details>
                </td>
                <td>
                    <details class="expandable">
                        <summary>View Response</summary>
                        <div class="json-view"><pre>{response_body}</pre></div>
                    </details>
                </td>
                <td>{error_cell}</td>
            </tr>
            """

        with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            template = Template(f.read())

        html = template.substitute(
            rows=rows,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            success_rate=success_rate,
            total_execution_time=total_execution_time,
            generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        with open(html_path, "w", encoding="utf-8") as file:
            file.write(html)
