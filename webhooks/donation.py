from flask import Flask, request, abort
from waitress import serve
from webhooks.utils.donated import Donated


Key = 'x%4htdsyp)8&pCew:L*A54[tzHu&Dn4_'

app = Flask(__name__)
app.debug = True


def runDonate():
    serve(app, host="127.0.0.1", port=25565)


app = Flask(__name__)


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
        abort(400)
