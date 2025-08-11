import json
import pathlib


def load_roles():
    path = pathlib.Path("roles.json")
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_roles(data):
    with open("roles.json", "w") as f:
        json.dump(data, f, indent=4)

def get_user_role_arn(guild_id, channel_id, user_id):
    roles = load_roles()
    user_data = roles.get(str(guild_id), {}).get(str(channel_id), {}).get(str(user_id))
    if user_data is None:
        return None
    if isinstance(user_data, list): 
        return user_data[0] if user_data else None
    return user_data.get("roles", [None])[0]

def get_user_region(guild_id, channel_id, user_id):
    roles = load_roles()
    user_data = roles.get(str(guild_id), {}).get(str(channel_id), {}).get(str(user_id))
    if isinstance(user_data, list):
        return "us-east-1"
    return user_data.get("region", "us-east-1")

def format_aws_error(e):
    if isinstance(e, TypeError) and 'RoleArn' in str(e):
        return " No IAM role set. Use `/setup-role` to register your AWS role before using this command."
    if hasattr(e, 'response'):
        err = e.response.get('Error', {})
        code = err.get('Code')
        if code in ['AccessDenied', 'UnauthorizedOperation']:
            return (
                " Cloud Commander does not have permission to perform this action.\n"
                "Please attach the required IAM policy to your IAM role and try again."
            )
        return f" AWS Error: {err.get('Message', 'An unknown AWS error occurred.')}"
    return f" Unexpected Error: {str(e)}"
