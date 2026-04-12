# Compatibility shim: python-lambda-local imports pkg_resources only to read
# its own version string, which was removed from setuptools 80+. This shim
# satisfies that import so tests can load lambda_local.context.

class _Dist:
    version = '0.1.13'

def require(name):
    return [_Dist()]
