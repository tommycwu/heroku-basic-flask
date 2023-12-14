import os
import json
import requests
import random
from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, render_template, request, session, url_for
import mysql.connector

app = Flask(__name__)
app.secret_key = "fd82541455b5c7a51086a2a51739f23c6e82cc8ee65e9af0ae014bc103970be2"
oauth = OAuth(app)
OAUTH_SCOPE = os.environ.get("OAUTH_SCOPE", "openid profile email application:write application:read demonstration:write demonstration:read idp:write idp:read resource:read resource:write")
#initialize the oauth lib
oauth.register(
    "auth0",
    #client_id=os.environ.get("AUTH0_CLIENT_ID", "ZoqQpUeIjm0wEyclIzWzxBBhHcvXdIOp"), 
    #client_secret=os.environ.get("AUTH0_CLIENT_SECRET", "9Ild24YzYEnlNP8cp4gh--4vzGDgF5ppr422TTkgcyHRjaDNURhnmJLUvwdMsvmu"), 
    
    client_id=os.environ.get("AUTH0_CLIENT_ID", "S5W32yd0wf2BqNeY8R9K3bIFjaQo3E5D"), 
    client_secret=os.environ.get("AUTH0_CLIENT_SECRET", "Kxd5PycGPnlMBrUtUGxbRQOU09mx7o7XrDjBDzAB7rjV_JR0e74L7eOZTf8ohv_G"), 
    
    client_kwargs={"scope": OAUTH_SCOPE},
    server_metadata_url='https://' + os.getenv("AUTH0_DOMAIN", "auth.demo.okta.com") + '/.well-known/openid-configuration'
)

def doPost(targetUrl, postData, headerInfo):
    try: 
        jsonData = json.JSONEncoder().encode(postData)
        print(postData)

        requestPost = requests.post(url = targetUrl, headers = headerInfo, data = jsonData)

        if requestPost.ok:
            resultValue = requestPost.text
            print(resultValue)
            return resultValue
        else:
            print(str(requestPost.status_code) + " - " + requestPost.reason)
            return None
        
    except Exception as ex:
        print(str(ex) + " - " + str(ex.__doc__)) 
        return None

@app.route("/login")
def login():
    #redirect to auth0 for the oidc login
    return oauth.auth0.authorize_redirect(redirect_uri=url_for("callback", _external=True), \
                                        audience="https://api.demo.okta.com", \
                                        scope=OAUTH_SCOPE, \
                                        response_type="code")

@app.route("/callback", methods=["GET", "POST"])
def callback():
    #oauth token will be given back to us once demo.okta.com has authenticated the user
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")

@app.route("/")
def home():
    #get access token from user that's logged in

    userSession = session.get('user')
    accessToken = userSession["access_token"]
    
    #generate random as a base for all idp/demo/app to be created
    tenantNbr = str(random.randint(10000,99999))

    #use access token to create idp
    postData = {"name":"twu-test-idp" + tenantNbr ,"type":"customer-identity"}
    headerInfo = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + accessToken}
    targetUrl = "https://api.demo.okta.com/idp"
    idpResult = doPost(targetUrl, postData, headerInfo)
    idpJson = json.loads(idpResult)
    idp_id = idpJson['idp_id']

    #while loop to check on status of idp create
    idpState = ''
    while idpState != 'active':
        getResult = requests.get("https://api.demo.okta.com/idp/" + idp_id, headers=headerInfo)  
        getText = getResult.text    
        getJson = json.loads(getText)  
        if "invite_link" in getJson:
            inviteLink = getJson["invite_link"]
        idpState = getJson["state"]

    #once the idp (aka tenant) has been created, use the idp_id and access token to create a demo
    demoName = "twu-test-demo-" + tenantNbr 
    postData = {"name": demoName, "type": "enablement", "idp_id": idp_id}
    headerInfo = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + accessToken, 'x-creation-source': 'builder'}
    targetUrl = "https://api.demo.okta.com/demonstration"
    demoResult = doPost(targetUrl, postData, headerInfo)

    #create an app (which will hold the webhooks... the post to the webhooks will contain the client creds for the management api)
    appName = "twu-test-app-" + tenantNbr
    postData = {"name": appName,
        "baseAddress": "https://example-client-application.example.com",
        "multiTenancy": "none",
        "hooks": {
            "request": "https://webhook.site/ee9e5ab7-f086-4dc0-b873-3604540cdbf2",
            "create": "https://webhook.site/ee9e5ab7-f086-4dc0-b873-3604540cdbf2",
            "update": "",
            "destroy": "",
            }
    }
    headerInfo = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + accessToken}
    targetUrl = "https://api.demo.okta.com/applications"
    appResult = doPost(targetUrl, postData, headerInfo)
    appJson = json.loads(appResult)
    application_id = appJson['application_id']

    #associate the app to the demo
    postData = {"application_id": application_id ,
        "label": "",
        "settings": ""
    }
    headerInfo = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + accessToken}
    targetUrl = "https://api.demo.okta.com/demonstration/" + demoName + "/apps"
    appResult = doPost(targetUrl, postData, headerInfo)

    #show results
    return render_template("home.html", userSession=json.dumps(userSession, indent=4), idpResult=json.dumps(getJson, indent=4), \
                           demoResult=json.dumps("demoResult", indent=4), appResult=json.dumps("appResult", indent=4), inviteLink = inviteLink)

@app.route("/webhook", methods=['POST'])
def webhook():
    incomingJson = request.json
    clientId = incomingJson['idp']['management_credentials']['clientId']
    clientSecret = incomingJson['idp']['management_credentials']['clientSecret']
    baseUrl = incomingJson['application']['oidc_configuration']['issuer']       
    return "", 200