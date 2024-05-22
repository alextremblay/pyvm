#!/usr/bin/env -S pyvm pipx 3.12 run --path

# /// script
# dependencies = [
#   "requests",
#   "rich",
# ]
# ///
                              
import requests
from rich import print

print(requests.get("https://httpbin.org").text)