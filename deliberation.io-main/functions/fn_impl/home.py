from firebase_functions import https_fn, firestore_fn, options


enableCors = options.CorsOptions(
        cors_origins=[r"firebase\.com$", r"https://flutter\.com", r"https://flutter\.com", r"https://deliberationio-yizum0\.flutterflow\.app", r"https://deliberationiobeta2\.flutterflow\.app", r"https://deliberation\.io"],
        cors_methods=["get", "post"],
    )

@https_fn.on_request(cors=enableCors)
def joinTopic(req: https_fn.Request) -> https_fn.Response:
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
        deliberationDocRef = data["deliberationDocRef"].strip()

        # Initialize Firestore client
        firestore_client = firestore.client()

        # retrieve the topic doc reference
        topic_lookup_ref = (
            firestore_client.collection("deliberations").document(deliberationDocRef).get()
        )

        # if the topic does not exist, return an error
        if not topic_lookup_ref.exists:
            return https_fn.Response("Requested topic does not exist.", status=400)

        # retrieve the user doc and update the participatedDeliberations fields
        user_doc = (
            firestore_client.collection("users").document(user_id).get().to_dict()
        )

        # if the user has not participated in any deliberations yet, create the field
        if "participatedDeliberations" not in user_doc.keys():
            user_doc["participatedDeliberations"] = []
            firestore_client.collection("users").document(user_id).set(user_doc)

        # update the participatedDeliberations field
        firestore_client.collection("users").document(user_id).update(
            {
                "participatedDeliberations": user_doc["participatedDeliberations"]
                + [deliberationDocRef]
            }
        )

        # Send back a message that we've successfully written the document
        return https_fn.Response(f"You have been added to the requested deliberation.")

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

@https_fn.on_request(cors=enableCors)
def getCreatedTopics(req: https_fn.Request) -> https_fn.Response:
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

        # if the user has not created any deliberations yet, create the field
        if "createdDeliberations" not in user_doc.keys():
            user_doc["createdDeliberations"] = []
            firestore_client.collection("users").document(user_id).set(user_doc)

        createdDeliberations = user_doc["createdDeliberations"]

        # retrieve the topic names of the created deliberations
        topic_list = []
        for topic_id in createdDeliberations:
            topic_doc = (
                firestore_client.collection("deliberations")
                .document(topic_id)
                .get()
                .to_dict()
            )
            topic_list.append(
                {"deliberationID": topic_id, "topicName": topic_doc["topicName"]}
            )

        # send back a JSON object with the doc references and also the topic names
        return https_fn.Response(
            json.dumps(topic_list), content_type="application/json"
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

@https_fn.on_request(cors=enableCors)
def getParticipatedTopics(req: https_fn.Request) -> https_fn.Response:
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

        # if the user has not created any deliberations yet, create the field
        if "participatedDeliberations" not in user_doc.keys():
            user_doc["participatedDeliberations"] = []
            firestore_client.collection("users").document(user_id).set(user_doc)

        participatedDeliberations = user_doc["participatedDeliberations"]

        # retrieve the topic names of the created deliberations
        topic_list = []
        for topic_id in participatedDeliberations:
            topic_doc = (
                firestore_client.collection("deliberations")
                .document(topic_id)
                .get()
                .to_dict()
            )
            topic_list.append(
                {"deliberationID": topic_id, "topicName": topic_doc["topicName"]}
            )

        # send back a JSON object with the doc references and also the topic names
        return https_fn.Response(
            json.dumps(topic_list), content_type="application/json"
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
