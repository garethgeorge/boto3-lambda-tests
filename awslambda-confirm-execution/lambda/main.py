import requests 

def test(req, ctx):
    print("HELLO WHATS UP?")
    print("\t\t\tRUNNING THE HTTP REQUEST LAMBDA: GET URL %s" % (req["url"],))
    r = requests.get(req["url"])

    print("RESPONSE: %s" % r.text)
    return {
        "status": "OK" if r.status_code == requests.codes.ok else "ERROR",
        "status_code": r.status_code,
        "text": r.text
    }
