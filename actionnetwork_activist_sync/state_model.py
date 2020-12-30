import os
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, JSONAttribute
)
from pynamodb.settings import get_settings_value

class State(Model):
    """
    This is a DynamoDB model for keeping state in the cloud.
    """

    class Meta:
        """
        Inner class that let's us set some customizations
        """
        # set via Terraform
        table_name = 'actionnetwork_activist_sync'
        host = 'http://localhost:4569' if os.environ.get('ENVIRONMENT') == 'local' \
            else get_settings_value('host')

    email = UnicodeAttribute(hash_key=True)
    batch = UnicodeAttribute(range_key=True)
    raw = JSONAttribute()
    status = NumberAttribute(default=0)

    UNPROCESSED = 0
    PROCESSING = 1
    PROCESSED = 2
    FAILED = 3
