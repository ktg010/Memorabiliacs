import json
from google.cloud import secretmanager
import requests
import streamlit as st
import toml
from BackendMethods.translations import _

## -------------------------------------------------------------------------------------------------
## Secrets Access --------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
@st.cache_data(ttl=3600)  # Cache for 1 hour
def access_secret_version():
    """
    Access the payload for a secret version.
    """
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = "projects/memorabiliacs-ec1bd/secrets/Streamlit_secrets/versions/latest"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Decode the payload.
    # Note: The secret value is returned as a bytes object.
    payload = response.payload.data.decode("UTF-8")
    payload_dict = toml.loads(payload)
    return payload_dict

st.secrets = access_secret_version()


## -------------------------------------------------------------------------------------------------
## Firebase Auth API -------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

def sign_in_with_email_and_password(email, password):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def get_account_info(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_email_verification(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_password_reset_email(email):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def create_user_with_email_and_password(email, password):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8" }
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def delete_user_account(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/deleteAccount?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def raise_detailed_error(request_object):
    try:
        request_object.raise_for_status()
    except requests.exceptions.HTTPError as error:
        raise requests.exceptions.HTTPError(error, request_object.text)

## -------------------------------------------------------------------------------------------------
## Authentication functions ------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

def sign_in(email: str, password: str, db) -> None:
    try:
        # Attempt to sign in with email and password
        id_token = sign_in_with_email_and_password(email,password)['idToken']

        # Get account information
        user_info = get_account_info(id_token)["users"][0]

        # If email is not verified, send verification email and do not sign in
        if not user_info["emailVerified"]:
            send_email_verification(id_token)
            st.session_state.auth_warning = 'Check your email to verify your account'

        # Save user info to session state
        else:
            st.session_state.user_info = user_info
            
            # Add user to database if they don't already exist
            try:
                result_list = email.split('@')
                
                user_ref = db.collection('Users').document(user_info['localId'])
                if not user_ref.get().exists:
                    data = {
                        'email': email,
                        'username': result_list[0],
                        'base' : 'dark',
                        'backgroundColor' : "#1a1a1a",
                        'textColor' : "#dddddd",
                        'font' : 'sans-serif',
                        'theme' : 'Original',
                        'language' : 'en'
                    }
                    user_ref.set(data)
                    user_ref.collection('Collections').document('DefaultCollection').set({'name': 'Default'})
            except Exception as e:
                print(f"Failed to add user to Firestore: {e}")
            
            st.rerun()

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"INVALID_EMAIL","EMAIL_NOT_FOUND","INVALID_PASSWORD","MISSING_PASSWORD"}:
            st.session_state.auth_warning = 'Error: Use a valid email and password'
        else:
            st.session_state.auth_warning = 'Error: Please try again later'

    except Exception as error:
        print(error)
        st.session_state.auth_warning = 'Error: Please try again later'


def create_account(email:str, password:str) -> None:
    try:
        # Create account (and save id_token)
        id_token = create_user_with_email_and_password(email,password)['idToken']

        # Create account and send email verification
        send_email_verification(id_token)
        st.session_state.auth_success = 'Check your inbox to verify your email'
    
    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message == "EMAIL_EXISTS":
            st.session_state.auth_warning = 'Error: Email belongs to existing account'
        elif error_message in {"INVALID_EMAIL","INVALID_PASSWORD","MISSING_PASSWORD","MISSING_EMAIL","WEAK_PASSWORD"}:
            st.session_state.auth_warning = 'Error: Use a valid email and password'
        else:
            st.session_state.auth_warning = 'Error: Please try again later'
    
    except Exception as error:
        print(error)
        st.session_state.auth_warning = 'Error: Please try again later'

def reset_password(email:str) -> None:
    try:
        send_password_reset_email(email)
        st.session_state.auth_success = 'Password reset link sent to your email'
    
    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"MISSING_EMAIL","INVALID_EMAIL","EMAIL_NOT_FOUND"}:
            st.session_state.auth_warning = 'Error: Use a valid email'
        else:
            st.session_state.auth_warning = 'Error: Please try again later'    
    
    except Exception:
        st.session_state.auth_warning = 'Error: Please try again later'


def sign_out() -> None:
    st.session_state.clear()
    st.session_state.auth_success = 'You have successfully signed out'


def delete_account(password:str, db) -> None:
    try:
        # Confirm email and password by signing in (and save id_token)
        id_token = sign_in_with_email_and_password(st.session_state.user_info['email'],password)['idToken']
        try:
            db.collection('Users').document(st.session_state.user_info['localId']).delete()
        except Exception as e:  
            print(f"Failed to delete user from Firestore: {e}")
        # Attempt to delete account
        delete_user_account(id_token)
        st.session_state.clear()
        st.session_state.auth_success = 'You have successfully deleted your account'

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        print(error_message)

    except Exception as error:
        print(error)

#setup templates for login stuff
def generate_login_template(db):
    col1, col2, col3 = st.columns([1, 2, 1])

    # Authentication form layout
    do_you_have_an_account = col2.selectbox(
        label=_('Do you have an account?'),
        options=(_('Yes'), _('No'), _('I forgot my password'))
    )
    auth_notification = col2.empty()

    #toggle between login, create account, and reset password forms based on selectbox answer
    if (do_you_have_an_account == _('Yes')):
        fields = {'Form name':'Login', 'Username':'Username', 'Password':'Password',
                        'Login':'Login'}

        login_form = st.form(key="Login", clear_on_submit=True)
        login_form.subheader(_('Login') if 'Form name' not in fields else fields['Form name'])
        email = login_form.text_input(_('Username') if 'Username' not in fields
                                                    else fields['Username'], autocomplete='off')
        password = login_form.text_input(_('Password') if 'Password' not in fields
                                                        else fields['Password'], type='password',
                                                        autocomplete='off')
        if login_form.form_submit_button(_('Login') if 'Login' not in fields
                                                    else fields['Login']):
            with auth_notification, st.spinner('Signing in'):
                sign_in(email, password, db)

    elif (do_you_have_an_account == _('No')):
        fields = {'Form name':'Create Account', 'Username':'Username', 'Password':'Password',
                        'Create Account':'Create Account'}
        create_account_form = st.form(key="Create Account", clear_on_submit=True)
        create_account_form.subheader(_('Create Account') if 'Form name' not in fields else fields['Form name'])
        email = create_account_form.text_input(_('Username') if 'Username' not in fields
                                                    else fields['Username'], autocomplete='off')
        password = create_account_form.text_input(_('Password') if 'Password' not in fields
                                                        else fields['Password'], type='password',
                                                        autocomplete='off')
        if create_account_form.form_submit_button(_('Create Account') if 'Create Account' not in fields
                                                    else fields['Create Account']):
            with auth_notification, st.spinner('Creating account'):
                create_account(email, password)
    elif (do_you_have_an_account == _('I forgot my password')):
        fields = {'Form name':'Reset Password', 'Username':'Username',
                        'Send Password Reset Email':'Send Password Reset Email'}
        reset_password_form = st.form(key="Reset Password", clear_on_submit=True)
        reset_password_form.subheader(_('Reset Password') if 'Form name' not in fields else fields['Form name'])
        email = reset_password_form.text_input(_('Username') if 'Username' not in fields
                                                    else fields['Username'], autocomplete='off')
        if reset_password_form.form_submit_button(_('Send Password Reset Email') if
                        'Send Password Reset Email' not in fields
                                                    else fields['Send Password Reset Email']):
            with auth_notification, st.spinner('Sending password reset link'):
                reset_password(email)
    if 'auth_success' in st.session_state:
        auth_notification.success(st.session_state.auth_success)
        del st.session_state.auth_success