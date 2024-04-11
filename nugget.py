import hashlib
import json
import time
from datetime import datetime
from random import randint

import ovh
import requests
from os import getenv, environ
CONFIG = {
    "endpoint": getenv("OCN_ENDPOINT"),
    "ovhSubsidiary": getenv("OCN_OVH_SUBSIDIARY"),
    "application_key": getenv("OCN_APPLICATION_KEY"),
    "application_secret": getenv("OCN_APPLICATION_SECRET"),
    "dedicated_datacenter": getenv("OCN_DEDICATED_DATACENTER"),
    "region": getenv("OCN_REGION"),
    "consumer_key": getenv("OCN_CONSUMER_KEY"),
]
# Instantiate. Visit https://api.ovh.com/createToken/?GET=/me
# to get your credentials
client = ovh.Client(
    endpoint=CONFIG["endpoint"],
    application_key=CONFIG["application_key"],
    application_secret=CONFIG["application_secret"],
    consumer_key=CONFIG["consumer_key"],
)

# Print nice welcome message
print("Welcome", client.get("/me")["firstname"])

headers = {
    "Accept": "application/json",
    "X-Ovh-Application": CONFIG["application_key"],
    "X-Ovh-Consumer": CONFIG["consumer_key"],
    "Content-Type": "application/json;charset=utf-8",
    "Host": CONFIG["endpointAPI"],
}
print("Preparing Package")
# getting current time
response = requests.get(
    f"https://{CONFIG['endpointAPI']}/1.0/auth/time", headers=headers
)
if response.status_code == 200:
    print("Getting Time")
else:
    print(response.status_code)
    print(json.dumps(response.json(), indent=4))
    exit()
timeDelta = int(response.text) - int(time.time())
# run for 8 days
for day in range(4):
    print(f"Day {day}")
    # creating a new cart
    cart = client.post(
        "/order/cart", ovhSubsidiary=CONFIG["ovhSubsidiary"], _need_auth=False
    )
    # assign new cart to current user
    client.post("/order/cart/{0}/assign".format(cart.get("cartId")))
    # put ks1 into cart
    # result = client.post(f'/order/cart/{cart.get("cartId")}/eco',{"duration":"P1M","planCode":"22sk010","pricingMode":"default","quantity":1})
    # apparently this shit sends malformed json whatever baguette
    payload = {
        "duration": "P1M",
        "planCode": "22sk010",
        "pricingMode": "default",
        "quantity": 1,
    }
    response = requests.post(
        f"https://{CONFIG['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/eco",
        headers=headers,
        data=json.dumps(payload),
    )
    if response.status_code != 200:
        print(response.status_code)
        print(json.dumps(response.json(), indent=4))
        exit()
    # getting current cart
    response = requests.get(
        f"https://{CONFIG['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}"
    )
    if response.status_code != 200:
        print(response.status_code)
        print(json.dumps(response.json(), indent=4))
        exit()
    # modify item for checkout
    itemID = response.json()["items"][0]
    print(f'Getting current cart {cart.get("cartId")}')
    # set configurations
    configurations = [
        {"label": "region", "value": CONFIG["region"]},
        {"label": "dedicated_datacenter", "value": CONFIG["dedicated_datacenter"]},
        {"label": "dedicated_os", "value": "none_64.en"},
    ]
    for entry in configurations:
        response = requests.post(
            f"https://{CONFIG['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/item/{itemID}/configuration",
            headers=headers,
            data=json.dumps(entry),
        )
        if response.status_code == 200:
            print(f"Setting {entry}")
        else:
            print(response.status_code)
            print(json.dumps(response.json(), indent=4))
            exit()
    # set options
    options = [
        {
            "itemId": itemID,
            "duration": "P1M",
            "planCode": "bandwidth-100-included-ks",
            "pricingMode": "default",
            "quantity": 1,
        },
        {
            "itemId": itemID,
            "duration": "P1M",
            "planCode": "noraid-1x1000sa-sk010",
            "pricingMode": "default",
            "quantity": 1,
        },
        {
            "itemId": itemID,
            "duration": "P1M",
            "planCode": "ram-4g-sk010",
            "pricingMode": "default",
            "quantity": 1,
        },
    ]
    for option in options:
        response = requests.post(
            f"https://{CONFIG['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/eco/options",
            headers=headers,
            data=json.dumps(option),
        )
        if response.status_code == 200:
            print(f"Setting {option}")
        else:
            print(response.status_code)
            print(json.dumps(response.json(), indent=4))
            exit()
    print("Package ready, waiting for stock")
    # the order expires in about 3 days, we create a new one after 2 days
    for check in range(17280):
        now = datetime.now()
        print(f'Run {check+1} {now.strftime("%H:%M:%S")}')
        # wait for stock
        response = requests.get(
            "https://us.ovh.com/engine/apiv6/dedicated/server/datacenter/availabilities?excludeDatacenters=false&planCode=22sk010&server=22sk010"
        )
        if response.status_code == 200:
            stock = response.json()
            score = 0
            for datacenter in stock[0]["datacenters"]:
                # if datacenter['availability'] != "unavailable": score = score +1
                if datacenter["datacenter"] == "rbx":
                    print(f'RBX {datacenter["availability"]}')
                    if datacenter["availability"] != "unavailable":
                        score = score + 1
                if datacenter["datacenter"] == "gra":
                    print(f'GRA {datacenter["availability"]}')
                    if datacenter["availability"] == "unavailable":
                        score = score + 1
        else:
            time.sleep(randint(5, 10))
            continue
        # lets checkout boooyaaa
        # if score >= 1:
        if score == 2:
            # autopay should be set to true if you want automatic delivery, otherwise it will just generate a invoice
            payload = {
                "autoPayWithPreferredPaymentMethod": False,
                "waiveRetractationPeriod": False,
            }
            # prepare sig
            target = f"https://{CONFIG['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/checkout"
            now = str(int(time.time()) + timeDelta)
            signature = hashlib.sha1()
            signature.update(
                "+".join(
                    [
                        CONFIG["application_secret"],
                        CONFIG["consumer_key"],
                        "POST",
                        target,
                        json.dumps(payload),
                        now,
                    ]
                ).encode("utf-8")
            )
            headers["X-Ovh-Signature"] = "$1$" + signature.hexdigest()
            headers["X-Ovh-Timestamp"] = now
            response = requests.post(target, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                print(response.status_code)
                print(json.dumps(response.json(), indent=4))
                exit("Done")
            else:
                print("Got non 200 response code on checkout, retrying")
                continue
        time.sleep(10)
