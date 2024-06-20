import json
from os import getenv

import ovh

# create a client using configuration
client = ovh.Client(
    endpoint=getenv("OCN_ENDPOINT"),
    application_key=getenv("OCN_APPLICATION_KEY"),
    application_secret=getenv("OCN_APPLICATION_SECRET"),
)

# Request RO, /me API access
ck = client.new_consumer_key_request()

ck.add_recursive_rules(ovh.API_READ_WRITE, "/")

# Request token
validation = ck.request(
    allowedIPs=getenv("OCN_ALLOWED_IPS").replace(" ", "").split(",")
)

print("Please visit %s to authenticate" % validation["validationUrl"])
input("and press Enter to continue...")

# Print nice welcome message
print("Welcome", client.get("/me")["firstname"])
print("Btw, your 'consumerKey' is '%s'" % validation["consumerKey"])
