import csv
import os
from os.path import exists
import sys

from keycloak import KeycloakAdmin

keycloak_admin = KeycloakAdmin(
    server_url="https://auth.bostondsa.org/auth/",
    client_id=os.environ.get('KEYCLOAK_CLIENT_ID'),
    client_secret_key=os.environ.get('KEYCLOAK_CLIENT_SECRET_KEY'),
    realm_name=os.environ.get('KEYCLOAK_REALM'),
    verify=True
)

if not exists(sys.argv[1]):
    raise FileNotFoundError

with open(sys.argv[1]) as csvfile:
    userreader = csv.reader(csvfile)
    for row in userreader:
        email = row[0]
        user_id = keycloak_admin.get_user_id(email)
        if user_id:
            print(f'User exists ({email}). Skipping.')
        else:
            print(f'User does not exist ({email}). Creating.')
            keycloak_admin.create_user({
                "email": email,
                "username": email,
                "enabled": True,
                "requiredActions": [
                    "UPDATE_PASSWORD"
                ]
            })
