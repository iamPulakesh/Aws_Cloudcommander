# Cloud Commander 🤖

Cloud Commander is a powerful, secure and user-friendly discord bot that lets users manage their AWS resources directly from a discord channel. It is built with Python, Boto3 and Discord.py.

## Features

- Secure IAM Role-based Access via AWS STS
- Region-per-user support (`/set-region`, `/switch-region`)
- EC2 management: list, start, stop, and metrics
- EBS & RDS: volume/status checks, metrics, DB start/stop
- S3 & Lambda: list buckets/functions, usage stats
- CloudFormation support: list & describe stacks
- CloudWatch metrics
- Network insights: VPCs, Subnets, NACLs, Route Tables and much more

## Project Structure

```
├── bot.py             # Bot logic
├── roles.json         # Stores users-roles-regions
├── .env               # Contains bot token
└── requirements.txt   # Project dependencies
```

## Setup Instructions

### 1. Install Dependencies

- Make sure you have Python 3.10+
- It is recommended to make a virtual environment and work inside that.
```bash
python -m venv venv
source venv\Scripts\activate
pip install -r requirements.txt
```
- AWS CLI installed and configured in your machine.

### 2. Configure the Bot

Create a `.env` file inside the project directory and add:

```env
BOT_TOKEN=your_discord_bot_token
```

### 3. IAM Role + AWS STS Setup

- Create an IAM role
- Select entity type `AWS Account`
- Name it something like `Awscommander_bot_handle`
- Attach necessary permissions for the services you want to control (It can be done later also).
- Edit Trust Policy and use this
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<your_account_id>:user/<your_iam_user_name>"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
- Attach this role to an IAM user (new or exsisting)
- Create an inline policy
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::<your_account_id>:role/Awscommander_bot_handle"
    }
  ]
}
```
- Now the IAM user running the bot has permission to call `sts:AssumeRole` on the role we created.


### 4. Run the bot

```bash
python bot.py
```

## Usage guide

### First-Time setup the bot in the discord server

1. Go to the `#cloud-commander` channel
2. Run `/setup-role <your_iam_role_arn>`
3. Run `/set-region <your_aws_region>` (default: us-east-1)
4. Run `/commands` to explore all supported commands

## How the bot interacts with AWS accounts
- When a user runs a bot command the bot reads the stored IAM role arn from roles.json.
- It uses AWS STS assume_role() to get temporary credentials.
- These credentials are used by boto3 to perform AWS actions on behalf of the user.
- When a user runs a command, the bot looks up their IAM Role and AWS region.

--------------------------------------------------------------------------------------------------------------------------------

# Docker-Based Setup Guide (https://hub.docker.com/r/pulak0007/aws-commander)
## Prerequisite

-	Docker Desktop
- AWS CLI installed and configured
-	A Discord Bot Token 

## Setup instruction
### Step 1: Create a Discord Bot

1. Go to: https://discord.com/developers/applications
2. Click "New Application"
3. Go to the "Bot" section and click "Add Bot"
4. Click "Reset Token" → "Copy" your bot token

### Step 2: Create the .env File

``Set-Content .env "DISCORD_BOT_TOKEN=your-bot-token"``

### Step 3: 
Configure AWS CLI (If not configured previously)

`aws configure --profile desired_profile_name`
- Fill with your AWS credentials.

### Step 4: Run it
- PowerShell:
```
docker run -it `
  --name container_name `
  -v "$env:USERPROFILE\.aws:/root/.aws" `
  --env-file .env `
  -e AWS_PROFILE = your_aws_profile_name `
  pulak0007/aws-commander
```

- CMD:
```
docker run -it ^
  --name cloudcommander-bot ^
  -v %USERPROFILE%\.aws:/root/.aws ^
  --env-file .env ^
  -e AWS_PROFILE= your_aws_profile_name ^
  pulak0007/aws-commander
```

### Step 5:
- Invite the bot into the server
