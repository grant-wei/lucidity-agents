from flask import Flask, render_template

app = Flask(__name__)

NOTES = ["buy oat milk", "email the landlord", "renew passport"]


@app.route("/")
def index():
    return render_template("index.html", notes=NOTES)


if __name__ == "__main__":
    app.run(debug=True)
