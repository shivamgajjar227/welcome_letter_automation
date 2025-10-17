from billiard.exceptions import SoftTimeLimitExceeded
from celery import Celery
import time
from datetime import datetime
import subprocess
import sys
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# @app.task
# def cpu_heavy_task(n):
#     print(f"{datetime.now()} starting time of cpu heavy task")
#     result = 1
#     for i in range(1, n+1):
#         result *= i
#     print(f"{datetime.now()} ending time of cpu heavy task")
#     return result
#
# @app.task
# def io_heavy_task(seconds):
#     print(f"{datetime.now()} starting time of io heavy task")
#     print(f"Sleeping for {seconds} seconds...")
#     time.sleep(seconds)
#     print(f"{datetime.now()} ending time of io heavy task")
#     return f"Slept for {seconds} seconds"
#
# @app.task
# def add(x, y):
#     return x + y
#
#
# @app.task(
#     bind=True,                  # bind=True allows self.retry
#     max_retries=3,              # max number of retries
#     default_retry_delay=5,      # retry after 5 seconds
#     soft_time_limit=4,          # soft time limit in seconds
#     time_limit=6                # hard time limit in seconds
# )
# def io_heavy_task(self, seconds):
#     try:
#         print(f"[{datetime.now()}] Starting I/O-heavy task sleep({seconds}s)")
#         time.sleep(seconds)
#         print(f"[{datetime.now()}] Finished I/O-heavy task sleep({seconds}s)")
#         return f"Slept for {seconds} seconds"
#     except SoftTimeLimitExceeded:
#         print(f"[{datetime.now()}] Task exceeded soft time limit, retrying...")
#         raise self.retry(exc=SoftTimeLimitExceeded())
#     except Exception as e:
#         print(f"[{datetime.now()}] Task failed with {e}, retrying...")
#         raise self.retry(exc=e)

sys.path.append(os.path.dirname(__file__))

def run_pytest(test_name):
    """Run a specific pytest test."""
    try:
        result = subprocess.run(
            [
                "pytest",
                f"tests/quickcap_suite.py::{test_name}",
                "-v",  # verbose logs
                "--alluredir=allure-results"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        print(result.stdout)  # <-- print full pytest output
        print(result.stderr)
        return {"status": "success", "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.CalledProcessError as e:
        print(e.stdout)  # <-- print error output
        print(e.stderr)
        return {"status": "failed", "stdout": e.stdout, "stderr": e.stderr}


def run_test_monday():
    print("Running test_monday...")
    result = run_pytest("test_monday")
    print(f"Result: {result['status']}")
    return result

def run_pr_site_test():
    print("Running test_pr_site...")
    result = run_pytest("test_pr_site")
    print(f"Result: {result['status']}")
    return result


def run_qc_test():
    print("Running test_qc...")
    result = run_pytest("test_qc")
    print(f"Result: {result['status']}")
    return result


def run_test_monday_status():
    print("Running test_monday_status...")
    result = run_pytest("test_monday_status")
    print(f"Result: {result['status']}")
    return result


if __name__ == "__main__":
    print("Running all test functions...")

    results = {
        "monday": run_test_monday(),
        "pr_site": run_pr_site_test(),
        "qc": run_qc_test(),
        "monday_status": run_test_monday_status()
    }

    print("\n=== SUMMARY ===")
    for test_name, result in results.items():
        print(f"{test_name}: {result['status']}")