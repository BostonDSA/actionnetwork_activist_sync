import types

from actionnetwork_activist_sync.sync import sync

def lambda_handler(event, context):
    sync()
    return {
        'statusCode': 200,
        'body': 'Sync Complete'
    }

if __name__ == '__main__':
    lambda_handler({}, types.SimpleNamespace())
