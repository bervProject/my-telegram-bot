import os


class Config(object):
    # In a production app, store this instead in KeyVault or an environment variable
    # TODO: Enter your client secret from Azure AD below
    CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "{YOUR-CLIENT-SECRET}")

    AUTHORITY = os.environ.get(
        "AUTHORITY", "https://login.microsoftonline.com/common")  # For multi-tenant app
    # AUTHORITY = "https://login.microsoftonline.com/Enter_the_Tenant_Name_Here"

    # TODO: Enter your application client ID here
    CLIENT_ID = os.environ.get("CLIENT_ID", "{YOUR-APP-CLIENT-ID}")

    # TODO: Enter the redirect path you want to use for OAuth requests
    #   Note that this will be the end of the URI entered back in Azure AD
    # Used to form an absolute URL,
    REDIRECT_PATH = os.environ.get("REDIRECT_URL", "/{YOUR-REDIRECT-PATH}")
    # which must match your app's redirect_uri set in AAD

    # You can find the proper permission names from this document
    # https://docs.microsoft.com/en-us/graph/permissions-reference
    SCOPE = ["User.Read"]

    SESSION_TYPE = "filesystem"  # So token cache will be stored in server-side session

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key')
