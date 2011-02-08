from flask import Flask
import argparse

def cmd_couchpotato():
    app = Flask(__name__)

    @app.route("/")
    def hello():
        return "Hello World!"

    if __name__ == "__main__":
        app.run(debug = True)
