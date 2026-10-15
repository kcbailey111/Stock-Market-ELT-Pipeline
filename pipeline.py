## Author: Kyler Bailey
## Date: 10/15/2026
## Description: This script is a pipeline for extracting, validating, and loading data from an API into a local DuckDB database.

# 1. Import the necessary libraries
import os
import datetime as dt
import requests
import duckdb
import pandas as pd
import pytest

# 2. Define the URL of the API
url = "https://api.example.com/data"

