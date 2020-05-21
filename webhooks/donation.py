from flask import Flask, request, abort
from waitress import serve


Key = 'mySuperSecreteAuthKey'

app = Flask(__name__)
app.debug = True


def runDonate():
    serve(app, host="127.0.0.1", port=25565)


app = Flask(__name__)


@app.route('/', methods=['POST'])
def donate():
    print("Donation Webhook")
    if request.method == 'POST':
        print(request.get_json())
        return '', 200
    else:
        abort(400)
