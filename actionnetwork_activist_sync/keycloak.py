from keycloak import KeycloakAdmin
from tenacity import Retrying, stop_after_attempt, wait_fixed

class KeycloakService:
    def __init__(self, keycloak):
        self.keycloak = keycloak

    def get_user_by_email(self, email):
        for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(5)):
            with attempt:
                keycloak_user_id = self.keycloak.get_user_id(email)

        return keycloak_user_id

    def update_user(self, keycloak_user_id, stuff):
        for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(5)):
            with attempt:

                # TODO first / last / username support
                self.keycloak.update_user(
                    user_id=keycloak_user_id,
                    payload={
                        "enabled": True
                    }
                )

    def create_user(self, email, stuff):
        for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(5)):
            with attempt:

                # TODO first / last / username support
                self.keycloak.create_user({
                    "email": email,
                    "username": email,
                    "enabled": True,
                    "requiredActions": [
                        "UPDATE_PASSWORD"
                    ]
                })
