import os
import threading
from waitress import serve

from flask import Flask, session, redirect, request, url_for, render_template
from requests_oauthlib import OAuth2Session

from bot.main import LegacyMusic


class UserData:
    def __init__(self, user_data, guild_data):
        self.id = user_data.get("id")

        self.username = user_data.get("username")
        self.discriminator = user_data.get("discriminator")
        self.full = f"{self.username}#{self.discriminator}"

        self.avatar = user_data.get("avatar")

        self.public_flags = user_data.get("public_flags")
        self.flags = user_data.get("flags")

        self.email = user_data.get("email")
        self.verified = user_data.get("verified")

        self.locale = user_data.get("locale")

        self.mfa_enabled = user_data.get("mfa_enabled")

        self.guilds = guild_data

    def update_data(self, user_data, guild_data):
        self.id = user_data.get("id")

        self.username = user_data.get("username")
        self.discriminator = user_data.get("discriminator")
        self.full = f"{self.username}#{self.discriminator}"

        self.avatar = user_data.get("avatar")

        self.public_flags = user_data.get("public_flags")
        self.flags = user_data.get("flags")

        self.email = user_data.get("email")
        self.verified = user_data.get("verified")

        self.locale = user_data.get("locale")

        self.mfa_enabled = user_data.get("mfa_enabled")

        self.guilds = guild_data


userData = UserData({}, {})
legacy = LegacyMusic()

OAUTH2_CLIENT_ID = '698211698624167997'
OAUTH2_CLIENT_SECRET = 'VYJygI1LK07CHcQUraa5gak2JO0qR5VN'
OAUTH2_REDIRECT_URI = 'http://127.0.0.1:5000/login'
Key = 'x%4htdsyp)8&pCew:L*A54[tzHu&Dn4_'

API_BASE_URL = os.environ.get('API_BASE_URL', 'https://discordapp.com/api')
AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
TOKEN_URL = API_BASE_URL + '/oauth2/token'

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = OAUTH2_CLIENT_SECRET


def runApp():
    serve(app, host="127.0.0.1", port=5000)


if 'http://' in OAUTH2_REDIRECT_URI:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'


def token_updater(token):
    session['oauth2_token'] = token


def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': OAUTH2_CLIENT_ID,
            'client_secret': OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater)


@app.route('/')
def home():
    if 'oauth2_token' in session:
        discord = make_session(token=session.get('oauth2_token'))
        user = discord.get(API_BASE_URL + '/users/@me').json()
        guilds = discord.get(API_BASE_URL + '/users/@me/guilds').json()
        connections = discord.get(API_BASE_URL + '/users/@me/connections').json()

        userData.update_data(user, guilds)
    return render_template('index.html',
                           logged_in=True if 'oauth2_token' in session and userData.full != "None#None" else False,
                           userData=userData)


@app.route('/donate/', methods=['POST'])
def donate():
    """
    This webhook catches all incoming POST requests, this will be reserved for donations. If the key is compromised then donations can be faked
    An example response would be:
    {'txn_id': '32972532BD432764B', 'buyer_email': 'buyer@email.com', 'price': '4.99', 'currency': 'USD',
    'buyer_id':'349714792719843329', 'role_id': '479793572267425842', 'guild_id': '404394509917487105',
    'recurring': False, 'status': 'completed'}

    txn_id is the transaction ID, this will be stored if the user is buying something such as premium for a specific server
    """
    if request.method == 'POST' and request.headers.get("Authorization") == Key:
        return '', 200
    else:
        return render_template('donate.html', logged_in=True if 'oauth2_token' in session and userData.full != "None#None" else False, userData=userData)


@app.route('/dashboard')
def dashboard():
    if 'oauth2_token' not in session or userData.full == "None#None":
        return redirect(url_for(".oauth2_login"))

    in_guilds = []
    not_in_guilds = []
    for guild in userData.guilds:
        for botGuild in legacy.guilds:
            if guild['name'] == botGuild.name:
                in_guilds.append(guild)
            else:
                not_in_guilds.append(guild)

    return render_template('dashboard.html',
                           logged_in=True if 'oauth2_token' in session and userData.full != "None#None" else False,
                           userData=userData, legacy=legacy, in_guilds=in_guilds, not_in_guilds=not_in_guilds, baseUrl=url_for(".dashboard"))


@app.route('/dashboard/<guild_id>')
def dashboard_view(guild_id: str = None):
    return redirect(url_for(".dashboard")+'/'+guild_id+"/music")


@app.route('/dashboard/<guild_id>/music')
def dashboard_music_view(guild_id: str = None):
    gid = None
    for data in userData.guilds:
        if data["id"] == guild_id:
            gid = int(data["id"])
    if gid:
        return render_template('dashboardMusic.html',
                               logged_in=True if 'oauth2_token' in session and userData.full != "None#None" else False,
                               userData=userData, legacy=legacy, guild=legacy.get_guild(gid))
    else:
        return redirect(url_for(".dashboard"))


@app.route('/our-team')
def team():
    return render_template('our-team.html',
                           logged_in=True if 'oauth2_token' in session and userData.full != "None#None" else False,
                           userData=userData)


@app.route('/oauth2_login')
def oauth2_login():
    scope = request.args.get(
        'scope',
        'identify email connections guilds guilds.join')
    discord = make_session(scope=scope.split(' '))
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    session['oauth2_state'] = state
    return redirect(authorization_url)


@app.route('/login')
def login():
    try:
        if request.values.get('error'):
            return redirect(url_for(".oauth2_login"))

        discord = make_session(state=session.get('oauth2_state'))
        token = discord.fetch_token(
            TOKEN_URL,
            client_secret=OAUTH2_CLIENT_SECRET,
            authorization_response=request.url)
        session['oauth2_token'] = token

        return redirect(url_for('.home'))
    except Exception:
        return redirect(url_for(".oauth2_login"))


if __name__ == "__main__":
    website = threading.Thread(target=runApp)
    bot = threading.Thread(target=legacy.run)

    website.start()
    bot.start()
