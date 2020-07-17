from flask import Flask, request, abort
from waitress import serve


Key = 'x%4htdsyp)8&pCew:L*A54[tzHu&Dn4_'

app = Flask(__name__)
app.debug = True


def runDonate():
    serve(app, host="127.0.0.1", port=25565)


app = Flask(__name__)


@app.route('/', methods=['POST'])
def donate():
    if request.method == 'POST' and request.headers.get("Authorization") == Key:
        print(request.get_json())
        return '', 200
    else:
        abort(400)
