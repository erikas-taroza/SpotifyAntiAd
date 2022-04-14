import tekore, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from client_keys import ClientKeys

# Some code is taken from Spotipy:
# https://github.com/plamere/spotipy/blob/9a627e88f422927822ce39ae9919cc7ab9813dde/spotipy/oauth2.py

class AuthHelper:
    # Create a token from the redirect url.
    def get_token(self) -> tekore.RefreshingToken:
        cred = tekore.RefreshingCredentials(ClientKeys.client_id, ClientKeys.client_secret, "http://127.0.0.1:7777/")
        auth = tekore.UserAuth(cred, scope = tekore.scope.user_read_playback_state)
        response = self._get_response_from_server(auth)

        (code, state) = response
        if response is not None:
            return auth.request_token(code, state)

    def _get_response_from_server(self, auth):
        server = self._start_server()
        webbrowser.open(auth.url)
        server.handle_request()

        if server.code is not None and server.state is not None:
            return (server.code, server.state)
        else:
            return None

    def _start_server(self):
        server = HTTPServer(("127.0.0.1", 7777), _RequestHandler)
        server.code = None
        server.state = None
        return server

class _RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.code = tekore.parse_code_from_url(self.path)
        self.server.state = tekore.parse_state_from_url(self.path)

        # Update page
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        if self.server.code is not None:
            html = """<html>
<body>
<h1>Authentication successful!</h1>
This window can be closed.
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
        else:
            html = """<html>
<body>
<h1>Authentication failed!</h1>
This window can be closed.
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))