from keycloak import KeycloakAdmin
from tenacity import Retrying, stop_after_attempt, wait_fixed

from actionnetwork_activist_sync.field_mapper import FieldMapper

class KeycloakService:
    """
    A service class that interacts with the lower level keycloak API
    and provides the actions necessary for the sync.
    """

    def __init__(self, keycloak: KeycloakAdmin):
        self.keycloak = keycloak

    def get_user_by_username(self, username: str) -> dict:
        """Searches the API for a user with an username.

        Args:
            username: The username to search for

        Returns:
            A dict representing a user if found, None otherwise
        """
        for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(5)):
            with attempt:
                users = self.keycloak.get_users({'username': username})
                keycloak_user = next(iter(users), None)

        return keycloak_user

    def get_user_by_email(self, email: str) -> dict:
        """Searches the API for a user with an email.

        Args:
            email: The email to search for

        Returns:
            A dict representing a user if found, None otherwise
        """
        for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(5)):
            with attempt:
                users = self.keycloak.get_users({'email': email})
                keycloak_user = next(iter(users), None)

        return keycloak_user

    def check_username(self, username: str):
        """Checks if a username is in use.

        Raises:
            ValueError if username is already taken
        """
        keycloak_user = self.get_user_by_username(username)
        if keycloak_user:
            raise ValueError('Username exists')

    def update_user(self, field_mapper: FieldMapper, keycloak_user: dict):
        """Updates an existing user.

        Args:
            field_mapper: the raw user data from a CSV
            keycloak_user: the already found user in keycloak
        """
        keycloak_user_id = keycloak_user['id']
        username = keycloak_user['username']

        # This is the legacy style username. Migrate user to non-email username.
        if keycloak_user['username'].lower() == keycloak_user['email'].lower():
            username = field_mapper.generate_username()
            self.check_username(username)

        self.keycloak.update_user(
            user_id=keycloak_user_id,
            payload={
                "username": username,
                "email": field_mapper.get_email(),
                "firstName": field_mapper.get_first_name(),
                "lastName": field_mapper.get_last_name(),
                "enabled": True
            }
        )

    def create_user(self, field_mapper: FieldMapper):
        """Creates a new user.

        Args:
            field_mapper: the raw user data from a CSV
        """
        username = field_mapper.generate_username()

        self.check_username(username)

        self.keycloak.create_user(payload={
            "username": username,
            "email": field_mapper.get_email(),
            "firstName": field_mapper.get_first_name(),
            "lastName": field_mapper.get_last_name(),
            "enabled": True,
            "requiredActions": [
                "UPDATE_PASSWORD"
            ]
        })
