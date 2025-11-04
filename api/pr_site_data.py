import time

import requests
from fastapi import FastAPI
from selenium import webdriver
from pages.quickcap_page import QuickcapPage

app = FastAPI()
class RequestAPi:


    def get(self):
        pass

    def split_address(address):
        url = "http://0.0.0.0:10022/api/parse_address"

        # Define the payload (query parameters) you want to send
        payload = {
            "raw_address": address,
        }

        # Send the GET request with parameters
        response = requests.post(url, json=payload)
        return response.json()

    def get_provider_id(plan_data):
        url = "http://0.0.0.0:10022/api/check_missing_ids"

        payload = {
            "ids": plan_data
        }
        response = requests.post(url, json=payload)
        return response.json()
