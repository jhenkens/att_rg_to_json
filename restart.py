#!/usr/bin/env python3
from bs4 import BeautifulSoup
import sys, json, requests, re, os, hashlib
import hashlib

RESTART = 'http://192.168.1.254/cgi-bin/restart.ha'
LOGIN = 'http://192.168.1.254/cgi-bin/login.ha'

if __name__ == "__main__":
    response = requests.get(RESTART)
    cookies = [h.split("=") for h in response.headers['Set-Cookie'].split(";")]
    session_id = [c for c in cookies if c[0] == "SessionID"][0][1]
    
    cookies = {"SessionID": session_id}
    
    response = requests.get(RESTART, cookies=cookies)
    soup = BeautifulSoup(response.content, 'html.parser')
    nonce = soup.find('input',{"name":"nonce"}).attrs["value"]
    
    test_password='%#?@19<488'
    password = test_password
    hex_md5 = hashlib.md5(f'{password}{nonce}'.encode('utf-8')).hexdigest()
    form = {
        "nonce": nonce,
        "passowrd": '*' * len(password),
        "hashpassword": hex_md5
        }
    print(form)
    response = requests.post(LOGIN, cookies=cookies, data=form)
    
    response = requests.get(RESTART, cookies=cookies)
    soup = BeautifulSoup(response.content, 'html.parser')
    nonce = soup.find('input',{"name":"nonce"}).attrs["value"]
    form = {
        "nonce": nonce,
        "Restart": "Restart"
    }
    if os.environ.get("SUBMIT", None) == "TRUE":
        response = requests.post(RESTART, cookies=cookies, data=form)

    