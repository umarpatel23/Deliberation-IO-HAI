"""
This file contains the main functions that are deployed to the Firebase Cloud Functions.
Authors: Chinmaya, Guinness
"""

# import the functions from the implementation files
from fn_impl.home import *
from fn_impl.createTopic import *
from fn_impl.round1 import *
from fn_impl.round2 import *
from fn_impl.admin import *
from fn_impl.socratic import *
from fn_impl.steelman import *
from fn_impl.pageNavigation import *
from fn_impl.analytics import *
import openai
from firebase_admin import initialize_app

# initialize the app
initialize_app()


exp1234567 = {
    "Homepage" : "Round 1",
    "Round 1" : "Socratic Dialogue",
    "Socratic Dialogue" : "Round 2"
}

exp89 = {
    "Homepage" : "Round 1",
    "Round 1" : "Round 2"
}


#Gated waiting room
#Nongated waiting room (takes previous page as a param, and to find next page we map previous page to the next one in the dictionary
# )