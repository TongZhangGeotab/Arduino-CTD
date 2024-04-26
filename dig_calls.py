import requests
import json

with open("config.json", "r") as file:
    data = json.load(file)
    userName = data["userName"]
    pw = data["pw"]

displayVerboseApiCallDetails = True

EndPoint = "dig.geotab.com (Default)"
if EndPoint == "dig.geotab.com (Default)":
    urlHdr = "https://dig."


def ApiCall(requestUrl, json):
    with requests.post(url=requestUrl, json=json) as r:
        if r.status_code == 200:
            return r
        else:
            return r


def authenticate_MyAdmin():
    """
    MyAdmin Authentication
    """
    # Set variables
    requestUrl = "https://myadmin.geotab.com/v2/myadminapi.ashx"
    try:
        userName and pw
    except userName.DoesNotExist or pw.DoesNotExist:
        print("Please enter MyAdmin credentials")
    obj = {"method": "Authenticate", "params": {"username": userName, "password": pw}}
    # Make Call
    authenticate = ApiCall(requestUrl, obj)
    x = authenticate.text
    # Setting MyAdmin Variables if call is successful
    if x[2:8] == "result":
        res = True
        userId = authenticate.json()["result"]["userId"]
        sessionId = authenticate.json()["result"]["sessionId"]
        print("MyAdmin Authentication was successful. " "Variables defined as: userId, sessionId")
    # Error handling
    else:
        print("An error occurred:")
        print(
            "Please ensure you have entered the proper MyAdmin credentials, the credentials entered were unable to authenticate"
        )
        userId = None
        sessionId = None
        res = False

    # Show endpoint and JSON payload if enabled in options
    if displayVerboseApiCallDetails:
        print("\nAPI endpoint: ", requestUrl)
        print("JSON payload:")
        obj["params"]["password"] = "[PASSWORD HIDDEN]"  # Never display user's password
        print(json.dumps(obj, indent=4))

    return res, userId, sessionId


def authenticate_DIG():
    """
    DIG Authentication and DIG Endpoint Selection
    """
    # Set variables
    authUrl = urlHdr + "geotab.com:443/authentication/authenticate"
    obj = {"username": userName, "password": pw}

    # Make Call
    call = ApiCall(authUrl, obj)
    print(call)
    txt = call.text
    x = json.loads(txt)

    # Error Handling
    if len(x["Error"]) > 0:
        print("DIG Authentication unsuccesssful:")
        print(
            "Please ensure you have entered the proper MyAdmin credentials, the credentials entered were unable to authenticate"
        )
        token = None
        tokenExpiration = None
        refreshToken = None
        refreshTokenExpiration = None
        res = False
    # Set variables if call is successful
    elif x["Data"]["Authenticated"] is True:
        token = x["Data"]["BearerToken"]["TokenString"]
        tokenExpiration = x["Data"]["BearerToken"]["Expires"]
        refreshToken = x["Data"]["RefreshToken"]["TokenString"]
        refreshTokenExpiration = x["Data"]["RefreshToken"]["Expires"]
        print(
            "DIG Authentication was successful. Variables defined as:"
            "token, tokenExpiration, refreshToken, refreshTokenExpiration"
        )
        print("Token Experation: ", tokenExpiration)
        res = True

    # Show endpoint and JSON payload if enabled in options
    if displayVerboseApiCallDetails:
        print("\nAPI endpoint: ", authUrl)
        print("JSON payload:")
        obj["password"] = "[PASSWORD HIDDEN]"  # Never display user's password
        print(json.dumps(obj, indent=4))

    return res, token, tokenExpiration, refreshToken, refreshTokenExpiration


def send_GenericStatusRecord(token, serialNo, code, value, timestamp):
    """
    Send a status record through DIG
    """
    dateTime = timestamp.isoformat() + "Z"

    recordsUrl = urlHdr + "geotab.com:443/records"

    try:
        token
    except token.DoesNotExist:
        print("Please authenticate to DIG")

    authcode = "Bearer " + token
    serialNo = serialNo.replace(
        "\u200B", ""
    )  # Replace invisible character that is occasionally copied from MyGeotab

    # Set header and data objects
    hdr = {"Authorization": authcode}
    data = [
        {
            "DateTime": dateTime,
            "SerialNo": serialNo,
            "Type": "GenericStatusRecord",
            "Code": code,
            "Value": value,
        }
    ]

    # Make Call
    datacall = requests.post(url=recordsUrl, headers=hdr, json=data)
    txt = datacall.text
    x = json.loads(txt)

    # Error handling
    if len(x["Error"]) < 1:
        print("Success:", x["Data"])
        res = True
    else:
        print("An Error occurred:", x["Error"])
        res = False

    # Show endpoint and JSON payload if enabled in options
    if displayVerboseApiCallDetails:
        print("\nAPI endpoint: ", recordsUrl)
        print("HTTP headers: ", hdr)
        print("JSON payload:")
        print(json.dumps(data, indent=4))

    return res
