
from firebase_functions import https_fn, firestore_fn, options

enableCors = options.CorsOptions(
        cors_origins=[r"firebase\.com$", r"https://flutter\.com", r"https://flutter\.com", r"https://deliberationio-yizum0\.flutterflow\.app", r"https://deliberationiobeta2\.flutterflow\.app", r"https://deliberation\.io"],
        cors_methods=["get", "post"],
    )


@https_fn.on_request(cors=enableCors)
def getLink(request):
    from firebase_admin import initialize_app, credentials, firestore, auth
    from flask import jsonify
    import json
    import openai
    import pandas as pd
    import matplotlib.pyplot as plt
    from collections import defaultdict
    import io
    import requests
    from datetime import datetime, timedelta
    try:
        # authenticate the user
        token = request.headers.get("Authorization").split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token["user_id"]

        # Parse JSON directly from request body
        data = request.get_json()
        deliberationDocRef = data["deliberationDocRef"]
        
        
        firestore_client = firestore.client()
        deliberation_doc_dict = firestore_client.collection("deliberations").document(deliberationDocRef).get().to_dict()

        if 'survey_link' not in deliberation_doc_dict.keys():
            return https_fn.Response("No survey created yet.")
        return https_fn.Response(
            json.dumps({'link' : deliberation_doc_dict['survey_link']}), content_type="application/json"
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
