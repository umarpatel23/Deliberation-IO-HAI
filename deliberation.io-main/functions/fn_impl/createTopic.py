from firebase_functions import https_fn, firestore_fn, options


enableCors = options.CorsOptions(
        cors_origins=[r"firebase\.com$", r"https://flutter\.com", r"https://flutter\.com", r"https://deliberationio-yizum0\.flutterflow\.app", r"https://deliberationiobeta2\.flutterflow\.app", r"https://deliberation\.io"],
        cors_methods=["get", "post"],
    )


OPTIONS = {
    "Initial Comments" : ["Include seed comments", "No seed comments"],
    "Socratic Dialogue" : ["Socratic dialogue", "Placebo dialogue", "None"],
    "Comment Voting" : ["Raw comments", "Steelman arguments"],
}

GATE_ORDER_1 = ["initial", "socratic", "commentVoting", "final"]
GATE_ORDER_2 = ["initial", "commentVoting", "final"]

GATE_MAP_1 = {"initial": "socratic", "socratic": "commentVoting", "commentVoting": "final", "final": "None"}
GATE_MAP_2 = {"initial": "commentVoting", "commentVoting": "final", "final": "None"}

PAGE_MAP_1 = {"Initial Comments": "Socratic Dialogue", "Socratic Dialogue": "Comment Voting", "Comment Voting": "Final Waiting Room"}
PAGE_MAP_2 = {"Initial Comments": "Comment Voting", "Comment Voting": "Final Waiting Room"}

PAGE_COUNTS_1 = {"Initial Waiting Room": 0, "Initial Comments": 0, "Socratic Waiting Room": 0, "Socratic Dialogue": 0, "Voting Waiting Room": 0, "Comment Voting": 0, "Final Waiting Room": 0}
PAGE_COUNTS_2 = {"Initial Waiting Room": 0, "Initial Comments": 0, "Socratic Waiting Room": 0, "Voting Waiting Room": 0, "Comment Voting": 0, "Final Waiting Room": 0}

PUSHY_MAP = {"Low": "1", "Medium": "2", "High": "3"}
# this function above is disgusting. I need to change the logic anyway because we've changed the way we need to store the deliberation.
# There's a bunch of auxillary data structures that we need to create and store in the database, eg. a page map that maps from a page to the next page
# I'm gonna rewrite the function from scratch and clean it up a bit.
#
# Here is a sample input format:
# {"topicName": "Gun Control",
#  "description": "In America, there is a debate over whether guns should be regulated. What do you think?",
#  "seedViewpoints": {"yes": {"taglines": ["Guns are bad", ...], "descriptions": ["Guns are bad because they kill people.", ...]}, 
#                      "no": {"taglines": ["Guns are good", ...], "descriptions": ["Guns are good because they protect people."]}
#                    },
# "deliberationSettings": {"Initial Comments": {"option": "Include seed comments", "time": 60},
#                          "Socratic Dialogue": {"option": "Socratic dialogue", "time": 60},
#                          "Comment Voting": {"option": "Raw comments", "time": 60},
#                         },
# "placeboPrompt": "Do you think ice cream tates good or bad?"}
#
# But we don't store the deliberationSettings directly. Instead we programatically create auxiliary data structures that we store in the database.
# I will outline everything below and then write the function.
#
# The function should create a new document in the deliberations collection with the following fields:
# - topicName: string
# - description: string
# - seedViewpoints: map<string, map<string, list<string>>>
# - adminID: string
# - jobRun: boolean (default False)
# - initialGateOpen: boolean (default False)
# - socraticGateOpen: boolean (default False)
# - commentVotingGateOpen: boolean (default False)
# - finalGateOpen: boolean (default False)
# - isSteelman: boolean (we get this from the commentVoting field in deliberationSettings. If they choose the steelan option, then set isSteelman true). 
# - isPlacebo: boolean (we get this from the socraticDialogue field in deliberationSettings. If they choose the placebo option, then set isPlacebo true).
# - placeboPrompt: string
# - timeMap: map<string, int> (maps from the stage name to the time in milliseconds)
# - pageCounts: map<string, int> (maps from the stage name to an integer. Initialized to 0 for all stages)
# - pageMap: map<string, string> (maps from the stage name to the next stage name. The order of the pages is set as follows: Initial Comments -> Socratic Dialogue -> Comment Voting -> Final Waiting Room). But some of the pages can be skipped, depending on the deliberation settings. For example, if the user chooses "None" as the Socratic Dialogue option in DeliberationSettings, then the pageMap will skip the Socratic Dialogue page.
# - gateMap: map<string, string> (maps from the gate name to the next gate name. The order of the gates is set as follows (keep in mind that this is now camelCase): initial -> socratic -> commentVoting -> final). But some of the gates can be skipped, depending on the deliberation settings. For example, if the user chooses "None" as the Socratic Dialogue option in DeliberationSettings, then the gateMap will skip socraticGate.
# 
# Ok, now lets implement the function.

@https_fn.on_request(cors=enableCors)
def createTopic(req: https_fn.Request) -> https_fn.Response:
    from firebase_admin import initialize_app, credentials, firestore, auth
    from flask import jsonify
    import json
    try:
        # authenticate the user
        token = req.headers.get("Authorization").split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token["user_id"]

        # Parse JSON directly from request body
        data = req.get_json()
        topicName = data["topicName"]
        description = data["description"]
        seedViewpoints = data["seedViewpoints"]
        placeboPrompt = data["placeboPrompt"]
        delibSettings = data["deliberationSettings"]
        pushyLevel = data["pushyLevel"]
        
        # Initialize Firestore client
        firestore_client = firestore.client()
        
        # Create the auxiliary data structures
        timeMap, pageCounts, pageMap, gateMap = dict(), dict(), dict(), dict()
        isSteelman, isPlacebo = False, False

        # set the boolean values
        if delibSettings["Comment Voting"]["option"] == "Steelman arguments":
            isSteelman = True
        if delibSettings["Socratic Dialogue"]["option"] == "Placebo dialogue":
            isPlacebo = True

        # Populate the maps
        for i, key in enumerate(list(OPTIONS.keys())):
            if delibSettings[key]["option"] != "None":
                timeMap[key] = delibSettings[key]["time"] * 1000

        # create the pageMap: either pageMap1 or pageMap2 depending the length of timeMap
        if len(timeMap) == 3:
            pageMap = PAGE_MAP_1
        else:
            pageMap = PAGE_MAP_2
        
        # create the gateMap: either gateOrder1 or gateOrder2 depending on length of pageMap
        if len(pageMap) == 3:
            gateMap = GATE_MAP_1
        else:
            gateMap = GATE_MAP_2

        # create the pageCounts: either pageCounts1 or pageCounts2 depending on length of pageMap
        if len(pageMap) == 3:
            pageCounts = PAGE_COUNTS_1
        else:
            pageCounts = PAGE_COUNTS_2

        # convert pushyLevel to a string number
        if pushyLevel != "null":
            pushyLevel = PUSHY_MAP[pushyLevel]

        # add auxiliary data structures to the data
        data["adminID"] = user_id
        data["jobRun"] = False
        data["initialGateOpen"] = False
        data["socraticGateOpen"] = False
        data["commentVotingGateOpen"] = False
        data["finalGateOpen"] = False
        data["isSteelman"] = isSteelman
        data["isPlacebo"] = isPlacebo
        data["placeboPrompt"] = placeboPrompt
        data["timeMap"] = timeMap
        data["pageCounts"] = pageCounts
        data["pageMap"] = pageMap
        data["gateMap"] = gateMap
        data["pushyLevel"] = pushyLevel

        # add the new deliberation to the collection
        update_time, doc_ref = firestore_client.collection("deliberations").add(data)

        # retrieve the user doc and update the createdDeliberations fields
        user_doc = (
            firestore_client.collection("users").document(user_id).get().to_dict()
        )

        # if the user has not created any deliberations yet, create the field
        if "createdDeliberations" not in user_doc.keys():
            user_doc["createdDeliberations"] = []
            firestore_client.collection("users").document(user_id).set(user_doc)

        # update the createdDeliberations field
        firestore_client.collection("users").document(user_id).update(
            {"createdDeliberations": user_doc["createdDeliberations"] + [doc_ref.id]}
        )

        # return the deliberationDocRef to the user in a JSON object with field "deliberationDocRef". The 
        return https_fn.Response(doc_ref.id)
    
    # catch any errors that occur during the process
    except Exception as e:
        return https_fn.Response(str(e), status=400)


@https_fn.on_request(cors=enableCors)
def editTopic(req: https_fn.Request) -> https_fn.Response:
    """Take the JSON object passed to this HTTP endpoint and insert it into
    a new document in the messages collection. Expects a POST request."""
    from firebase_admin import initialize_app, credentials, firestore, auth
    from flask import jsonify
    import json
    try:
        # authenticate the user
        token = req.headers.get("Authorization").split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token["user_id"]

        # Parse JSON directly from request body
        data = req.get_json()
        required_keys = set(
            [
                "topic",
                "placebo",
                "isSteelman",
                "seedViewpoints",
                "deliberationSettings"
            ]
        )
        

        # Ensure the JSON object contains a 'topic' field
        if set(list(data.keys())) != required_keys:
            return https_fn.Response("Required keys missing in JSON object", status=400)
        if type(data["deliberationSettings"]) is not dict:
            return https_fn.Response("Deliberation settings incorrectly formatted.", status=400)
        
        finalStageChoices, finalSelections, finalLengths = list(), list(), list()
        for i, key in enumerate(list(OPTIONS.keys())):
            if data["deliberationSettings"][key]["option"] is not None:
                finalStageChoices.append(key)
                finalSelections.append(data["deliberationSettings"][key]["option"])
                finalLengths.append(data["deliberationSettings"][key]["time"] * 1000)  # convert from seconds to milliseconds for Flutterflow widgets
        
        # add the adminID field to the data
        data["adminID"] = user_id
        
        del data["deliberationSettings"]
        del data["deliberationDocRef"]
        data["stageChoices"] = ['Waiting'] + finalStageChoices
        data["stageSelections"] = ['Waiting'] + finalSelections
        data["stageLengths"] = ['Waiting'] + finalLengths
        data["stageTimes"] = [-1000 for _ in range(len(finalStageChoices) + 1)]
        data["currStage"] = 0


        # Initialize Firestore client
        firestore_client = firestore.client()

        # add the new deliberation to the collection
        firestore_client.collection("deliberations").document(data["deliberationDocRef"]).update(
            data
        )


        # Send back a message that we've successfully written the document
        return https_fn.Response(f"Topic successfully edited.")

    # Catch any errors that occur during the process
    except auth.InvalidIdTokenError:
        return https_fn.Response("Invalid JWT token", status=401)

    except auth.ExpiredIdTokenError:
        return https_fn.Response("Expired JWT token", status=401)

    except auth.RevokedIdTokenError:
        return https_fn.Response("Revoked JWT token", status=401)

    except auth.CertificateFetchError:
        return https_fn.Response(
            "Error fetching the public key certificates", status=401
        )

    except auth.UserDisabledError:
        return https_fn.Response("User is disabled", status=401)

    except ValueError:
        return https_fn.Response("No JWT token provided", status=401)