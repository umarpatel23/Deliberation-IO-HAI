from firebase_functions import https_fn, firestore_fn, options

enableCors = options.CorsOptions(
        cors_origins=[r"firebase\.com$", r"https://flutter\.com", r"https://flutter\.com", r"https://deliberationio-yizum0\.flutterflow\.app", r"https://deliberationiobeta2\.flutterflow\.app", r"https://deliberation\.io"],
        cors_methods=["get", "post"],
    )

@https_fn.on_request(cors=enableCors)
def getDescription(req: https_fn.Request) -> https_fn.Response:
    from firebase_admin import initialize_app, credentials, firestore, auth
    from flask import jsonify
    import json
    try:
        # authenticate the user
        token = req.headers.get("Authorization").split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token["user_id"]

        # Initialize Firestore client
        firestore_client = firestore.client()

        # parse JSON directly from request body
        data = req.get_json()
        deliberationDocRef = data["deliberationDocRef"]

        # retrieve the topic information for the desired deliberation
        topic_doc = firestore_client.collection("deliberations").document(deliberationDocRef).get().to_dict()
        description = topic_doc["description"]

        # send back a JSON object with the doc references and also the topic names
        return https_fn.Response(description)
        
    except Exception as e:
        return https_fn.Response(str(e), status=400) 
    

@https_fn.on_request(cors=enableCors)
def getDelibInfo(req: https_fn.Request) -> https_fn.Response:
    from firebase_admin import initialize_app, credentials, firestore, auth
    from flask import jsonify
    import json
    try:
        # authenticate the user
        token = req.headers.get("Authorization").split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token["user_id"]

        # Initialize Firestore client
        firestore_client = firestore.client()

        # retrieve the user doc
        user_doc = (
            firestore_client.collection("users").document(user_id).get().to_dict()
        )

        data = req.get_json()
        required_keys = set(["deliberationDocRef"])
        # Ensure the JSON object contains a 'deliberationDocRef' field
        if set(list(data.keys())) != required_keys:
            return https_fn.Response("Required keys missing in JSON object", status=400)

        # if the user has not created any deliberations yet or is not part of the requested deliberation, give response
        if (
            "createdDeliberations" not in user_doc.keys()
            or len(user_doc["createdDeliberations"]) == 0
            or data["deliberationDocRef"] not in user_doc["createdDeliberations"]
        ):
            return https_fn.Response(
                "Seems like you don't have access to this deliberation. Sorry!",
                status=401,
            )

        # retrieve the topic information for the desired deliberation
        topic_doc = (
            firestore_client.collection("deliberations")
            .document(data["deliberationDocRef"])
            .get()
            .to_dict()
        )

        seedYesTaglines = topic_doc["seedViewpoints"]["yes"]["taglines"]
        seedNoTaglines = topic_doc["seedViewpoints"]["no"]["taglines"]
        seedYesDescriptions = topic_doc["seedViewpoints"]["yes"]["descriptions"]
        seedNoDescriptions = topic_doc["seedViewpoints"]["no"]["descriptions"]

        # construct the delibSettings object
        delibSettings = dict()
        delibSettings["Round 1"] = {"option": topic_doc["stageSelections"][1], "time": topic_doc["stageLengths"][1]}
        delibSettings["Intervention"] = {"option": topic_doc["stageSelections"][2], "time": topic_doc["stageLengths"][2]}
        delibSettings["Round 2"] = {"option": topic_doc["stageSelections"][3], "time": topic_doc["stageLengths"][3]}
        delibSettings["Round 3"] = {"option": topic_doc["stageSelections"][4], "time": topic_doc["stageLengths"][4]}



        yesSeedList = list()
        noSeedList = list()
        for tagline, description in zip(seedYesTaglines, seedYesDescriptions):
            yesSeedList.append({"tagline": tagline, "description": description})

        for tagline, description in zip(seedNoTaglines, seedNoDescriptions):
            noSeedList.append({"tagline": tagline, "description": description})

        massaged_doc = {
            "topicName": topic_doc["topic"],
            "yesSeeds": yesSeedList,
            "noSeeds": noSeedList,
            "delibSettings": delibSettings
        }

        # send back a JSON object with the doc references and also the topic names
        return https_fn.Response(
            json.dumps(massaged_doc), content_type="application/json"
        )

    # catch any errors that occur during the process
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

# a function that allows admins to download the entirety of the deliberation data from the deliberation document in Firestore.
# It should return a url to the user that they can use to download the data.
@https_fn.on_request(cors=enableCors)
def downloadData(req: https_fn.Request) -> https_fn.Response:
    from firebase_admin import auth, storage, firestore
    import json
    try:
        # authenticate the user
        token = req.headers.get("Authorization").split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token["user_id"]

        # parse JSON directly from request body
        data = req.get_json()
        deliberationDocRef = data["deliberationDocRef"]

        # Initialize Firestore client
        firestore_client = firestore.client()

        # check if the user is the admin of the given deliberation
        doc = firestore_client.collection("deliberations").document(deliberationDocRef).get()
        adminId = doc.get("adminID")
        if adminId != user_id:
            return https_fn.Response("User is not the admin", status=401)

        # if they exist, then get the following subcollections: commentCollection, socraticCollection, steelmanCollection, voteCollection
        commentCollection = firestore_client.collection("deliberations").document(deliberationDocRef).collection("commentCollection").stream()
        socraticCollection = firestore_client.collection("deliberations").document(deliberationDocRef).collection("socraticCollection").stream()
        steelmanCollection = firestore_client.collection("deliberations").document(deliberationDocRef).collection("steelmanCollection").stream()
        voteCollection = firestore_client.collection("deliberations").document(deliberationDocRef).collection("voteCollection").stream()

        # create a dictionary to store all the data
        doc = {
            "commentCollection": [comment.to_dict() for comment in commentCollection],
            "socraticCollection": [socratic.to_dict() for socratic in socraticCollection],
            "steelmanCollection": [steelman.to_dict() for steelman in steelmanCollection],
            "voteCollection": [vote.to_dict() for vote in voteCollection]
        }

        # test the storage client
        bucket = storage.bucket('delib_data')
        blob = bucket.blob(f'{deliberationDocRef}.json')
        blob.upload_from_string(json.dumps(doc))

        # generate the download url
        blob.make_public()

        # send back the download url
        return https_fn.Response(blob.public_url)

    # catch any errors that occur during the process
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

@https_fn.on_request(cors=enableCors)
def downloadVotesMatrix(req: https_fn.Request) -> https_fn.Response:
    from firebase_admin import auth, storage, firestore
    import pandas as pd
    import json
    try:
        # authenticate the user
        token = req.headers.get("Authorization").split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token["user_id"]

        # parse JSON directly from request body
        data = req.get_json()
        deliberationDocRef = data["deliberationDocRef"]

        # Initialize Firestore client
        firestore_client = firestore.client()

        # check if the user is the admin of the given deliberation
        doc = firestore_client.collection("deliberations").document(deliberationDocRef).get()
        adminId = doc.get("adminID")
        if adminId != user_id:
            return https_fn.Response("User is not the admin", status=401)

        # get the voteCollection
        voteCollection = firestore_client.collection("deliberations").document(deliberationDocRef).collection("votesCollection").stream()

        # initialize the dictionary to store the votes data
        votes_dict = dict()

        # check if this deliberation was steelman or raw comments
        commentType = "steelman" if doc.get("isSteelman") else "comments"

        for doc in voteCollection:
            voter_id = doc.id
            votes_data = doc.to_dict()

            if voter_id not in votes_dict:
                votes_dict[voter_id] = dict()

            votes = votes_data.get(commentType, {})
            for comment_id, nested_vote in votes.items():
                # get the most recent vote
                vote = list(nested_vote.values())[-1]
                votes_dict[voter_id][comment_id] = vote

        # convert the dictionary to a csv
        votes_df = pd.DataFrame.from_dict(votes_dict, orient='index').fillna(0)
        votes_csv = votes_df.to_csv(index=True)

        # save the csv to the storage bucket
        bucket = storage.bucket('votes_matrices')
        blob = bucket.blob(f'{deliberationDocRef}.txt')
        blob.upload_from_string(votes_csv)

        # generate the download url
        blob.make_public()

        # send back the download url
        return https_fn.Response(blob.public_url)

    # catch any errors that occur during the process
    except auth.InvalidIdTokenError:
        return https_fn.Response("Invalid JWT token", status=401)

    except auth.ExpiredIdTokenError:
        return https_fn.Response("Expired JWT token", status=401)

    except auth.RevokedIdTokenError:
        return https_fn.Response("Revoked JWT token", status=401)

    except auth.CertificateFetchError:
        return https_fn.Response(
            "Error fetching the public key certificates", status=401)

    except auth.UserDisabledError:
        return https_fn.Response("User is disabled", status=401)

    except ValueError:
        return https_fn.Response("No JWT token provided", status=401)