from firebase_functions import https_fn, firestore_fn, options

enableCors = options.CorsOptions(
        cors_origins=[r"firebase\.com$", r"https://flutter\.com", r"https://flutter\.com", r"https://deliberationio-yizum0\.flutterflow\.app", r"https://deliberationiobeta2\.flutterflow\.app", r"https://deliberation\.io"],
        cors_methods=["get", "post"],
    )


@https_fn.on_request(cors=enableCors)
def getComments(req: https_fn.Request) -> https_fn.Response:
    """Take the JSON object passed to this HTTP endpoint and insert it into
    a new document in the messages collection. Expects a POST request."""
    from firebase_admin import initialize_app, credentials, firestore, auth
    from flask import jsonify
    import json
    from google.api_core.exceptions import NotFound
    import openai
    try:
        # authenticate the user
        token = req.headers.get("Authorization").split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token["user_id"]

        # Parse JSON directly from request body
        data = req.get_json()
        required_keys = set(
            ["deliberationDocRef"]
        )
        
        # Ensure the JSON object contains the required fields
        if set(list(data.keys())) != required_keys:
            return https_fn.Response(f"Current keys are {data.keys()}. Required keys missing in JSON object", status=400)

        # Initialize Firestore client
        firestore_client = firestore.client()
        topic_doc = (
            firestore_client.collection("deliberations")
            .document(data["deliberationDocRef"])
            .get()
            .to_dict()
        )
        isSteelman = topic_doc['isSteelman']
        
        # add the new deliberation to the collection
        user_comment_docs = firestore_client.collection("deliberations").document(data["deliberationDocRef"]).collection("commentCollection" if not isSteelman else "steelmanCommentCollection").stream()
        # Get the comments from the user_comment_docs
        comments_list = []
        for user_comment_doc in user_comment_docs:
            user_comment_dict = user_comment_doc.to_dict()
            commentText = user_comment_dict["comments"][-1]
            userID = user_comment_doc.id
            commentID = {"userID": userID, "commentIndex": len(user_comment_dict["comments"])-1}
            commentCard = {"commentID": commentID, "commentText": commentText}
            comments_list.append(commentCard)

        # randomly sample up to 10 comments
        import random
        random.shuffle(comments_list)
        if len(comments_list) > 10:
            comments_list = comments_list[:10]
        
        ### REMOVE NUMBERING FROM OUTPUT COMMENTS
        import re
        def strip_list_prefixes(text):
            # Define a regex pattern that matches common list item prefixes
            pattern = r'^\s*(\d+\.\s*|\d+\)\s*|-\s*)'
            # Use re.sub to replace the matching prefixes with an empty string
            stripped_text = re.sub(pattern, '', text)
            return stripped_text
        final_comments_list = []
        for commentCard in comments_list:
            final_comments_list.append(
                {
                    'commentID': commentCard['commentID'],
                    'commentText': strip_list_prefixes(commentCard['commentText']).strip()
                }
            )
        del comments_list    
        # Return the list of comments
        return https_fn.Response(
            json.dumps(final_comments_list), content_type="application/json"
        )
        
        
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
def sendCommentVote(req: https_fn.Request) -> https_fn.Response:
    from firebase_admin import initialize_app, credentials, firestore, auth
    from flask import jsonify
    import json
    from google.api_core.exceptions import NotFound
    import openai
    try:
        # authenticate the user
        token = req.headers.get("Authorization").split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token["user_id"]

        # Parse JSON directly from request body
        data = req.get_json()
        required_keys = set(
            ["deliberationDocRef", "commentID", "vote"]
        )
         
        # Ensure the JSON object contains a 'topic' field
        if set(list(data.keys())) != required_keys:
            return https_fn.Response(f"Current keys are {data.keys()}. Required keys missing in JSON object", status=400)

        # extract the data from the JSON object
        userID = data["commentID"]["userID"]
        commentIndex = data["commentID"]["commentIndex"]
        vote = data["vote"]
        
        # Initialize Firestore client
        firestore_client = firestore.client()
        topic_doc = (
            firestore_client.collection("deliberations")
            .document(data["deliberationDocRef"])
            .get()
            .to_dict()
        )
        isSteelman = topic_doc['isSteelman']
        

        # add the new deliberation to the collection
        user_comment_doc = firestore_client.collection("deliberations").document(data["deliberationDocRef"]).collection("votesCollection").document(user_id).get().to_dict()

        # if the user has not voted on any comments yet, create the field
        correct_key = "comments" if not isSteelman else "steelman"
        if user_comment_doc is None:
            user_comment_doc = dict()
        if correct_key not in user_comment_doc.keys():
            user_comment_doc[correct_key] = dict()
        if userID not in user_comment_doc[correct_key].keys():
            user_comment_doc[correct_key][userID] = dict()
        user_comment_doc[correct_key][userID][str(commentIndex)] = vote

        try: 
            # update the createdDeliberations field
            firestore_client.collection("deliberations").document(data["deliberationDocRef"]).collection("votesCollection").document(user_id).update(
                user_comment_doc
            )

        except (NotFound, ValueError):
            firestore_client.collection("deliberations").document(data["deliberationDocRef"]).collection("votesCollection").document(user_id).set(
                user_comment_doc
            )


        # Send back a message that we've successfully added the comment.
        return https_fn.Response(f"vote successfully added.")

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


