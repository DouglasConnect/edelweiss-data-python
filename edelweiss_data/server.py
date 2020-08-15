import abc
import os
import time
import urllib.parse
import hashlib
import json

import requests
# There are a few different libraries called jwt, so python can get confused which one to import.
# But api_jwt only exists in one library, so this style import makes it unambiguous.
from jwt import api_jwt


class JwtAuthBase(requests.auth.AuthBase, metaclass=abc.ABCMeta):
    """Abstract base class for authentication by a jwt. This implements the __call__ method, making it compatible with requests library"""

    def __init__(self):
        super().__init__()
        self._jwt = None

    @abc.abstractmethod
    def generate_jwt(self):
        """child classes should implement this method"""
        raise NotImplementedError

    @property
    def jwt(self):
        if not self.is_valid():
            # jwt either does not exist or it has expired, so get a new one
            self._jwt = self.generate_jwt()
        return self._jwt

    def is_valid(self):
        if self._jwt is None:
            return False
        claims = api_jwt.decode(self._jwt, verify=False)
        exp = int(claims['exp'])
        return exp > time.time()

    def __call__(self, r):
        """This method implements the AuthBase super class. The requests library calls this method for every request"""
        r.headers['Authorization'] = "Bearer {}".format(self.jwt)
        return r

class SimpleJwt(JwtAuthBase):
    """Authentication class to use when the jwt is provided by some other external method."""
    def __init__(self, jwt):
        super().__init__()
        self._jwt = jwt

    def generate_jwt(self):
        raise Exception("SimpleJwt cannnot generate a new jwt")


class OidcJwt(JwtAuthBase):
    """Authenticates requests by adding a jwt to each request.
       The user must sign in to the identity provider by copying a url into their web browser.

       This is an implementation of the oidc device authorization flow
       https://auth0.com/docs/flows/guides/device-auth/call-api-device-auth"""

    def __init__(self, client_id,
                 domain,
                 audience,
                 cache_jwt=True,
                 token_dir=None,
                 lazy=False,
                 refresh_token=None,
                 scopes=[]):

        self.token_dir = token_dir if token_dir is not None else os.path.expanduser(os.path.join("~", ".edelweiss"))
        self.client_id = client_id
        self.domain = domain
        self.audience = audience
        self.cache_jwt = cache_jwt
        self._refresh_token = refresh_token
        self.scopes = scopes
        super().__init__()

        if self._refresh_token is None:
            try:
                with open(self.refresh_token_path, "r") as fh:
                    self._refresh_token = fh.read()
            except FileNotFoundError:
                pass

        if not lazy:
            self._jwt = self.generate_jwt()

    @property
    def refresh_token_path(self):
        md5 = hashlib.md5(json.dumps(self._device_code_payload()).encode('utf-8')).hexdigest()
        return os.path.join(self.token_dir, "refresh_token_{}_v3".format(md5))

    def _device_code_payload(self):
        return {"client_id": self.client_id,
                "scope": ' '.join(["offline_access", *sorted(self.scopes)]),
                "audience": self.audience }

    def _fetch_device_code(self):
        url = "https://{}/oauth/device/code".format(self.domain)
        response = requests.post(url, data=self._device_code_payload())
        response.raise_for_status()
        return response.json()

    def _prompt_user(self, device_code_response):
        print("Visit this url in your web browser to sign into edelweiss:")
        print(device_code_response["verification_uri_complete"])
        print("Your authorization token is {}".format(device_code_response["user_code"]))
        print()
        print("Waiting for authentication.....")

    def _poll_token(self, device_code_response):
        url = "https://{}/oauth/token".format(self.domain)
        payload = {
            "client_id": self.client_id,
            "device_code": device_code_response["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }

        # Loop and wait for the user to authenticate.
        # Keep looping until the device code response expires.
        expires_at = time.time() + device_code_response['expires_in']
        while time.time() < expires_at:
            response = requests.post(url, data=payload)
            if response.ok:
                print("Authentication successful")
                return response.json()
            if response.json()["error"] == "authorization_pending":
                # We expect a 4xx error code if the user has not authenticated yet.
                time.sleep(device_code_response['interval'])
            else:
                response.raise_for_status()
        raise Exception("Timed out waiting for authentication")

    def authenticate_with_refresh_token(self, refresh_token):
        url = "https://{}/oauth/token".format(self.domain)
        payload = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        response = requests.post(url, data=payload)
        response.raise_for_status()
        return response.json()

    def authenticate_without_refresh_token(self):
        device_code_response = self._fetch_device_code()
        self._prompt_user(device_code_response)
        token_response = self._poll_token(device_code_response)
        self._refresh_token = token_response["refresh_token"]
        if self.cache_jwt:
            self._save_token(self._refresh_token)
        return token_response["access_token"]

    def _save_token(self, token):
        os.makedirs(self.token_dir, exist_ok=True, mode=0o700)
        fdesc = os.open(self.refresh_token_path, os.O_WRONLY | os.O_CREAT, 0o600)
        with os.fdopen(fdesc, 'w') as fh:
            fh.write(token)

    def generate_jwt(self):
        if self._refresh_token is None:
            return self.authenticate_without_refresh_token()
        else:
            token_response = self.authenticate_with_refresh_token(self._refresh_token)
            return token_response["access_token"]

    @property
    def refresh_token(self):
        if self._refresh_token is None:
            self.authenticate_without_refresh_token()
        return self._refresh_token


class DevJwt(JwtAuthBase):
    """Authentication to be used in development only.
       Creates a self-signed jwt without going to a remote identity provider. This is helpful when the dev server is configured to accept self-signed jwt"""

    def __init__(self, email="user@example.com",
                 email_claim="https://claims.edelweiss.douglasconnect.com/email"):
        self._email = email
        self._email_claim = email_claim
        super().__init__()

    def generate_jwt(self):
        claims = {
            'exp': int(time.time()) + 3600,
            self._email_claim: self._email,
        }
        jwt = api_jwt.encode(claims, 'secret', algorithm='HS256')
        return str(jwt, 'utf-8')

class EdelweissHttpError(requests.exceptions.HTTPError):
    """An HTTP error occurred"""

    def __init__(self, error_type, *args, **kwargs):
        self.error_type = error_type
        return super().__init__(*args, **kwargs)

class Server:
    def __init__(self, base_url):
        self.base_url = base_url
        self.auth = None

    def _absolute_url(self, route):
        return urllib.parse.urljoin(self.base_url, route)

    def authenticate(self, *args, development:bool=False, jwt=None, **kwargs):
        if development:
            self.auth = DevJwt(*args, **kwargs)
        elif jwt is not None:
            self.auth = SimpleJwt(jwt)
        else:
            config = self.oidc_config()
            self.auth = OidcJwt(*args, client_id=config["nativeClientId"], domain=config["domain"],
                    audience=config["audience"], **kwargs, )

    def _handle_response(self, response):
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                edelweiss_error = response.json()
                message = u'Edelweiss Error: "%s" for url %s' % (edelweiss_error.get('message'), response.url)
                error = EdelweissHttpError(edelweiss_error.get('errorType'), message, request=error.request, response=response)
            except:
                pass
            raise error

        return None if response.status_code == 204 else response.json()

    def get(self, route:str, json=None):
        '''Sends a GET request to a server.

        :returns: dict with the JSON response.
        :param route: route to which the request will be sent
        :param json: dict with the JSON body to send
        '''
        response = requests.get(self._absolute_url(route), json=json, auth=self.auth)
        return self._handle_response(response)

    def post(self, route:str, json=None):
        '''Sends a POST request to a server.

        :returns: dict with the JSON response.
        :param route: route to which the request will be sent
        :param json: dict with the JSON body to send
        '''
        response = requests.post(self._absolute_url(route), json=json, auth=self.auth)
        return self._handle_response(response)

    def post_raw(self, route:str, data):
        '''Sends a POST request with a given body to a server.

        :returns: dict with the JSON response.
        :param route: route to which the request will be sent
        :param body: raw body to send (a bytes object or a string that will be encoded as UTF-8)
        '''
        if isinstance(data, str):
            data = data.encode('utf-8')
        response = requests.post(self._absolute_url(route), data=data, auth=self.auth)
        return self._handle_response(response)

    def upload(self, route:str, files):
        '''Uploads a POST request that uploads files to a server.

        :returns: dict with the JSON response.
        :param route: route to which the request will be sent
        :param files: a dictionary of files in which the keys are filenames
          and corresponding values are file objects
        '''
        response = requests.post(self._absolute_url(route), files=files, auth=self.auth)
        return self._handle_response(response)

    def delete(self, route:str):
        '''Sends a DELETE request to a server.

        :returns: dict with the JSON response.
        :param route: route to which the request will be sent
        '''
        response = requests.delete(self._absolute_url(route), auth=self.auth)
        return self._handle_response(response)

    @abc.abstractmethod
    def oidc_config(self):
        """child classes should retrieve oidc config from the api"""
        raise NotImplementedError
