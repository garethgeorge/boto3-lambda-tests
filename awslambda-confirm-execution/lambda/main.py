import requests 

def test(req, ctx):
    print("request: ", req)
    print("context: ", ctx)
    print("fetching url: %s" % (req["url"],))
    r = requests.get(req["url"])
    return {
        "result": str(r.text)
    }