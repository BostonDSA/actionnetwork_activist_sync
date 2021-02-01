import os

from actionnetwork_activist_sync.sync import sync

if __name__ == '__main__':
    stats = sync(os.environ['ACTIONNETWORK_API_KEY'])
    print('Sync complete')
    print(stats)
