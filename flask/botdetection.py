# Imports
import os
import tweepy
from datetime import datetime
import re
import time
import numpy as np
import pandas as pd
import pickle
import flask
from ExperimentalTransformer import ExperimentalTransformer

app = flask.Flask(__name__)

xgb_model = pickle.load(open('./flask/03 XGBoost (final).sav','rb'))

def bot_likelihood(prob):
    if prob < 20:
        return '<span class="has-text-info">Not a bot</span>'
    elif prob < 35:
        return '<span class="has-text-info">Likely not a bot</span>'
    elif prob < 50:
        return '<span class="has-text-info">Probably not a bot</span>'
    elif prob < 60:
        return '<span class="has-text-warning">Maybe a bot</span>'
    elif prob < 80:
        return '<span class="has-text-warning">Likely a bot</span>'
    else:
        return '<span class="has-text-danger">Bot</span>'

   
def bot_proba(twitter_handle):
    '''
    Takes in a twitter handle and provides probabily of whether or not the user is a bot
    Required: trained classification model (XGBoost) and user account-level info from get_user_features
    '''
    user_features = get_user_features(twitter_handle)
    user = np.matrix(user_features)
    print(user)
    df = pd.DataFrame(user, columns=["verified", "location", "followers_count", "following_count", "tweet_count", "un_no_of_char",
                    "un_special_char", "un_uppercase", "name_no_of_char", "name_special_char", "name_uppercase",
                    "des_no_of_usertags", "des_no_of_hashtags", "des_external_links", "has_description", "account_age_in_days"])
    print(df)
    if user_features == 'User not found':
        return 'User not found'
    else:
        user = np.matrix(user_features)
        proba = np.round(xgb_model.predict_proba(df)[:, 1][0]*100, 2)
        return proba

@app.route('/')
def homepage():
    return flask.render_template('index.html')


@app.route('/predict', methods=['GET', 'POST'])
def make_prediction():
    handle = flask.request.form['handle']
    print(handle)

    # make predictions with model from twitter_funcs
    user_lookup_message = f'Prediction for @{handle}'
    
    if get_user_features(handle) == 'User not found':
        prediction = [f'User @{handle} not found', '']

    else:
        prediction = [bot_likelihood(bot_proba(handle)),
                      f'Probability of being a bot: {bot_proba(handle)}%']

    return flask.render_template('index.html', prediction=prediction[0], probability=prediction[1], user_lookup_message=user_lookup_message)

@app.route('/api',methods=['POST'])
def predict():
    # Get the data from the POST request.
    data = request.get_json(force=True)
    # Make prediction using model loaded from disk as per the data.
    prediction = model.predict([[np.array(get_user_features(handle))]])
    # Take the first value of prediction
    output = prediction[0]
    return jsonify(output)

bearer_token = 'AAAAAAAAAAAAAAAAAAAAADuChwEAAAAAyd5NyoPPZfk%2FiBwmc2mC9me33RA%3DTFH93ScdBzcU6OHVLLsTDHKLW599NhhPoEBTPi0KFWdAEbmFth'
client = tweepy.Client(bearer_token=bearer_token)

def get_user_features(screen_name):
    '''
    Input: a Twitter handle (screen_name)
    Returns: a list of account-level information used to make a prediction 
            whether the user is a bot or not
    '''
    
    try:
        # Get user information from screen name
        user = client.get_user(username=screen_name,
                                user_fields=["created_at",
                                             "description",
                                             "entities",
                                             "id",
                                             "location",
                                             "name",
                                             "profile_image_url",
                                             "public_metrics",
                                             "url",
                                             "username",
                                             "verified"])
        data = user.data
        # account features to return for predicton
        verified = int(data["verified"] == True)
        location = int(data["location"] == True)
        followers_count = data["public_metrics"]['followers_count']
        following_count = data["public_metrics"]['following_count']
        tweet_count = data["public_metrics"]['tweet_count']
        name = data["name"]
        username = data["username"]
        description = data["description"]
        has_description = int(data["description"]!="")
        
        # manufactured features
        user_tags = r'\B@\w*[a-zA-Z]*\w*'
        hashtags = r'\B#\w*[a-zA-Z]+\w*'
        links = r'(https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}[-a-zA-Z0-9()@:%_+.~#?&/=]*)'
        special_char = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        un_no_of_char = len(username)
        un_special_char = special_char.search(username)!= None
        un_uppercase = bool(re.match(r'\w*[A-Z]\w*', username))
        name_no_of_char = len(name)
        name_special_char = special_char.search(name)!= None
        name_uppercase = bool(re.match(r'\w*[A-Z]\w*', name))
        des_no_of_usertags = len(re.findall(user_tags, description))
        des_no_of_hashtags = len(re.findall(hashtags, description))
        des_external_links = re.findall(links, description) != []
        account_age_in_days = (datetime.now() - data['created_at'].replace(tzinfo=None)).days

        # organizing list to be returned
        account_features = [verified, location, followers_count, following_count, tweet_count, un_no_of_char,
                            un_special_char, un_uppercase, name_no_of_char, name_special_char, name_uppercase,
                            des_no_of_usertags, des_no_of_hashtags, des_external_links, has_description, account_age_in_days]

    except: #Exception as e:
        return'User not found'

    return account_features if len(account_features) == 16 else f'User not found'

# for local dev
if __name__ == '__main__':
    app.run(port=5001)
